"""Engine-output -> `ExtractedField` parsing for the OCR adapter.

Adapter-only per `docs/ARCHITECTURE.md` §5: this module knows the shape of
a RapidOCR-style detection row (`[box_points, text, score]`), but never
imports the OCR engine itself -- that stays in `adapters/ocr/paddle_onnx.py`.

Rewritten (generic-receipt-field-extraction change) from a label-map +
nearest-value-below pairing to a `scan -> validate -> select -> emit`
pipeline: every core field gets an independent scanner that walks the
reading-ordered `RawTextBox` list looking for *value shapes* -- never
labels. Labels only re-enter, for `destination_cbu` / `cuit`, as a
keyword-proximity ranking signal over already-found candidates (see
`_keyword_score`).

Traces to spec.md "Field extracted with confidence" / "Same field
extracted despite different label wording" (FR-005): a field is returned
with its raw text, a normalized value (or `None` when it cannot be
normalized), and the engine's confidence for the value box, independent of
label wording, layout, or absence of a label entirely.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from dateutil import parser as _dateutil_parser  # noqa: TID251 -- adapters/** is exempt

from receipt_risk.domain.analysis import ExtractedField
from receipt_risk.domain.financial.cbu import validate_cbu
from receipt_risk.domain.financial.cuit import validate_cuit
from receipt_risk.domain.financial.dates import is_within_date_bounds
from receipt_risk.domain.financial.money import normalize_amount

# The four core fields the coverage formula in design.md is computed over:
# "coverage = core fields with conf >= 0.60, / 4".
CORE_FIELD_NAMES: tuple[str, ...] = ("amount", "destination_cbu", "cuit", "date_time")

_CUIT_DIGIT_LENGTH = 11
_CBU_DIGIT_LENGTH = 22

# Context window for keyword-proximity disambiguation: a candidate's own
# box plus the boxes immediately around it in reading order, restricted to
# the same visual "row" (approximately one label+value pair at
# samples/generate.py's ROW_HEIGHT = 130). Reasoned defaults, not tuning
# knobs -- same convention as the ruleset/C2PA marker constants.
_CONTEXT_BEFORE = 2
_CONTEXT_AFTER = 1
_CONTEXT_MAX_DY_PX = 140.0

# Ranking-only backstop (never a rejection filter -- see `_select_date`):
# much wider than `domain.financial.dates.DEFAULT_MAX_PAST_DAYS`/
# `DEFAULT_MAX_FUTURE_DAYS`, which stay the *validation* bounds used by
# `application/financial_validation.py`'s `DATE_OUT_OF_BOUNDS` signal.
_DATE_RANKING_MAX_PAST_DAYS = 3650
_DATE_RANKING_MAX_FUTURE_DAYS = 3650

_SENTINEL_YEAR = 1900

# Real bank/wallet receipts print local wall-clock time, never a UTC offset
# (confirmed against the real Mercado Pago sample this parser was built
# against). dateutil then returns a naive datetime for the near-totality of
# real receipts. financial_validation.py's is_within_date_bounds always
# compares against an aware `datetime.now(UTC)`-based reference, so a naive
# result must never reach it -- attach this product's fixed Argentina
# offset (UTC-3, no DST) whenever the source text carried none of its own.
_ARGENTINA_TZ = timezone(timedelta(hours=-3))


@dataclass(frozen=True, slots=True)
class RawTextBox:
    """An engine-agnostic detected text box: text, confidence, and the
    top-left corner of its bounding box (used only for reading-order
    sorting and keyword-proximity context, never persisted)."""

    text: str
    confidence: Decimal
    top: float
    left: float


def boxes_from_engine_output(raw_result: Sequence[object] | None) -> list[RawTextBox]:
    """Convert a RapidOCR-shaped result (`[[points, text, score], ...]`)
    into `RawTextBox` records. Never raises: a malformed row is dropped,
    never propagated as an exception (the adapter's bounded-retry state
    machine must stay purely a function of coverage, not of parser
    exceptions)."""
    boxes: list[RawTextBox] = []
    for row in raw_result or []:
        try:
            points, text, score = row  # type: ignore[misc]
            xs = [float(point[0]) for point in points]
            ys = [float(point[1]) for point in points]
            boxes.append(
                RawTextBox(
                    text=str(text).strip(),
                    confidence=Decimal(str(score)).quantize(Decimal("0.01")),
                    top=min(ys),
                    left=min(xs),
                )
            )
        except (TypeError, ValueError, IndexError):
            continue
    return boxes


@dataclass(frozen=True, slots=True)
class _Candidate:
    value: str  # digits | Decimal str | ISO-8601
    raw_text: str  # originating box text/substring
    confidence: Decimal
    order: int  # index in reading order
    checksum_valid: bool  # always True for amount/date


def _reading_order(boxes: Sequence[RawTextBox]) -> list[RawTextBox]:
    return sorted(boxes, key=lambda box: (box.top, box.left))


def _fold(text: str) -> str:
    """NFKD-normalize, drop combining marks, lower-case -- so
    "acreditación" matches "acreditacion"."""
    decomposed = unicodedata.normalize("NFKD", text)
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return without_marks.lower()


# ---------------------------------------------------------------------------
# Digit-run scanning primitives (CBU/CUIT) -- boundary-anchored, exact-length.
# ---------------------------------------------------------------------------

# Tier 1: a run of digits (with interior hyphens/dots) not glued to another
# alnum character on either side. `,`, `/`, `:` are deliberately NOT
# accepted interior separators, so `125.000,00` yields only a short run and
# `01/09/2026` yields three short runs -- neither can reach 11 or 22.
_DIGIT_RUN_RE = re.compile(r"(?<![0-9A-Za-z])(\d[\d\-.]*\d)(?![0-9A-Za-z])")


def _digit_runs(text: str) -> list[str]:
    return [match.group(1) for match in _DIGIT_RUN_RE.finditer(text)]


def _grouped_runs(text: str, target: int) -> list[str]:
    """Tier 2: split `text` into whitespace-separated all-digit tokens and,
    for each start index, concatenate left-to-right. Accept on exact
    `== target`, abandon (stop extending from that start) on `> target`."""
    tokens = [token for token in text.split() if token.isdigit()]
    results: list[str] = []
    for start in range(len(tokens)):
        accumulated = ""
        for token in tokens[start:]:
            accumulated += token
            if len(accumulated) == target:
                results.append(accumulated)
                break
            if len(accumulated) > target:
                break
    return results


def _digit_candidates(ordered: Sequence[RawTextBox], target: int) -> list[_Candidate]:
    """Shared digit-run primitive for both CBU and CUIT scanning. Tier 2
    (`_grouped_runs`) only runs for a box when Tier 1 found nothing there."""
    candidates: list[_Candidate] = []
    for order, box in enumerate(ordered):
        tier1_found = False
        for raw in _digit_runs(box.text):
            digits = "".join(ch for ch in raw if ch.isdigit())
            if len(digits) == target:
                candidates.append(
                    _Candidate(
                        value=digits,
                        raw_text=raw,
                        confidence=box.confidence,
                        order=order,
                        checksum_valid=False,
                    )
                )
                tier1_found = True
        if tier1_found:
            continue
        for digits in _grouped_runs(box.text, target):
            candidates.append(
                _Candidate(
                    value=digits,
                    raw_text=digits,
                    confidence=box.confidence,
                    order=order,
                    checksum_valid=False,
                )
            )
    return candidates


def _dedupe_candidates(candidates: Sequence[_Candidate]) -> list[_Candidate]:
    """De-duplicate by normalized value, keeping the earliest-in-reading-
    order occurrence (a CBU printed twice is one candidate)."""
    seen: dict[str, _Candidate] = {}
    for candidate in sorted(candidates, key=lambda c: c.order):
        seen.setdefault(candidate.value, candidate)
    return list(seen.values())


def _scan_cuit_candidates(ordered: Sequence[RawTextBox]) -> list[_Candidate]:
    return [
        replace(candidate, checksum_valid=validate_cuit(candidate.value).is_valid)
        for candidate in _digit_candidates(ordered, _CUIT_DIGIT_LENGTH)
    ]


def _scan_cbu_candidates(ordered: Sequence[RawTextBox]) -> list[_Candidate]:
    return [
        replace(candidate, checksum_valid=validate_cbu(candidate.value).is_valid)
        for candidate in _digit_candidates(ordered, _CBU_DIGIT_LENGTH)
    ]


# ---------------------------------------------------------------------------
# Amount scanner -- the parser locates the substring, `normalize_amount`
# decides the AR/US locale convention.
# ---------------------------------------------------------------------------

_AMOUNT_TIER1_RE = re.compile(r"(?:AR\$|US\$|ARS|USD|\$)\s*(-?\d[\d.,]*)")
_AMOUNT_TIER2_RE = re.compile(r"-?\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?")


def _scan_amount_candidates(ordered: Sequence[RawTextBox]) -> list[_Candidate]:
    """Two match tiers: (1) symbol/code-prefixed, (2) grouped-without-
    symbol. Tier 1 is preferred globally over tier 2 -- tier 2 is only
    scanned when tier 1 found nothing anywhere."""
    tier1: list[_Candidate] = []
    for order, box in enumerate(ordered):
        for match in _AMOUNT_TIER1_RE.finditer(box.text):
            amount = normalize_amount(match.group(1))
            if amount is None:
                continue
            tier1.append(
                _Candidate(
                    value=str(amount),
                    raw_text=match.group(0),
                    confidence=box.confidence,
                    order=order,
                    checksum_valid=True,
                )
            )
    if tier1:
        return tier1

    tier2: list[_Candidate] = []
    for order, box in enumerate(ordered):
        for match in _AMOUNT_TIER2_RE.finditer(box.text):
            amount = normalize_amount(match.group(0))
            if amount is None:
                continue
            tier2.append(
                _Candidate(
                    value=str(amount),
                    raw_text=match.group(0),
                    confidence=box.confidence,
                    order=order,
                    checksum_valid=True,
                )
            )
    return tier2


def _select_amount(candidates: Sequence[_Candidate]) -> _Candidate | None:
    """Prefer the largest `Decimal` within the (already tier-preferred)
    candidate set -- the transferred amount is assumed to dominate
    fees/commissions on a transfer receipt (documented risk, no keyword
    disambiguation for amount)."""
    if not candidates:
        return None
    try:
        return max(candidates, key=lambda c: (Decimal(c.value), -c.order))
    except InvalidOperation:
        return candidates[0]


# ---------------------------------------------------------------------------
# Date scanner -- Spanish-aware, clock-independent.
# ---------------------------------------------------------------------------

# Digit -> letter OCR-typo repair map. Extends design.md's documented table
# (0,1,3,4,5,6,8,9) with 2 -> z: "marzo" degrades to "mar20" ('z' and 'o'
# visually confused with '2' and '0' respectively) is an explicit spec.md
# scenario ("Wide date/time format coverage including an OCR-typo month
# name"), so the map must cover it to satisfy that acceptance criterion.
_DIGIT_TO_LETTER: dict[str, str] = {
    "0": "o",
    "1": "l",
    "2": "z",
    "3": "e",
    "4": "a",
    "5": "s",
    "6": "g",
    "8": "b",
    "9": "g",
}

_MONTH_WORDS: frozenset[str] = frozenset(
    {
        "enero",
        "ene",
        "febrero",
        "feb",
        "marzo",
        "mar",
        "abril",
        "abr",
        "mayo",
        "may",
        "junio",
        "jun",
        "julio",
        "jul",
        "agosto",
        "ago",
        "septiembre",
        "setiembre",
        "sep",
        "sept",
        "set",
        "octubre",
        "oct",
        "noviembre",
        "nov",
        "diciembre",
        "dic",
        "january",
        "jan",
        "february",
        "march",
        "april",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    }
)

_ES_TO_EN_MONTH: dict[str, str] = {
    "enero": "January",
    "ene": "Jan",
    "febrero": "February",
    "feb": "Feb",
    "marzo": "March",
    "mar": "Mar",
    "abril": "April",
    "abr": "Apr",
    "mayo": "May",
    "junio": "June",
    "jun": "Jun",
    "julio": "July",
    "jul": "Jul",
    "agosto": "August",
    "ago": "Aug",
    "septiembre": "September",
    "setiembre": "September",
    "sep": "Sep",
    "sept": "Sep",
    "set": "Sep",
    "octubre": "October",
    "oct": "Oct",
    "noviembre": "November",
    "nov": "Nov",
    "diciembre": "December",
    "dic": "Dec",
}

_DATE_CONNECTOR_WORDS: frozenset[str] = frozenset({"de", "del", "a", "las", "hs", "hrs", "horas"})

_WORD_TOKEN_RE = re.compile(r"\w+", re.UNICODE)
_NUMERIC_DATE_SHAPE_RE = re.compile(r"\b\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}\b")
_ISO_DATE_SHAPE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
# Digit-adjacency boundaries only (not `\b`): `\b` treats digits and letters
# as the same "word" class, so a year glued directly to trailing alphabetic
# connector text -- a documented OCR artifact where the leading space of a
# connector like "a las"/"at" is dropped, e.g. "2026alas20:53" -- has no
# transition right after the year and never matched `\b\d{4}\b` (verify
# finding: real Mercado Pago OCR text glues "2026" to "alas"). Requiring
# "not preceded/followed by another digit" instead keeps the original
# false-positive guard (a 4-digit year is never sliced out of a longer
# all-digit run, e.g. a CBU/CUIT/phone number), while letters immediately
# before or after the year no longer reject an otherwise-valid date shape.
_FOUR_DIGIT_YEAR_RE = re.compile(r"(?<!\d)\d{4}(?!\d)")


def _repair_month_tokens(text: str) -> str:
    """Digit-for-letter repair, applied only to mixed alnum tokens (pure-
    digit tokens like `2026` are left untouched). A repaired token is kept
    only if it lands exactly on a known month word; otherwise the original
    token is left unrepaired."""

    def _repair(match: re.Match[str]) -> str:
        token = match.group(0)
        if token.isdigit() or token.isalpha():
            return token
        repaired = "".join(_DIGIT_TO_LETTER.get(ch, ch) for ch in token)
        return repaired if repaired.lower() in _MONTH_WORDS else token

    return _WORD_TOKEN_RE.sub(_repair, text)


def _to_english_date_text(text: str) -> str:
    """After digit-for-letter repair: substitute Spanish month names/
    abbreviations for English ones, and drop Spanish date connectors
    (`de`, `del`, `a`, `las`, `hs`, `hrs`, `horas`) -- `dateutil` does not
    understand Spanish month names."""
    repaired = _repair_month_tokens(text)

    def _translate(match: re.Match[str]) -> str:
        token = match.group(0)
        lower = token.lower()
        if lower in _DATE_CONNECTOR_WORDS:
            return " "
        return _ES_TO_EN_MONTH.get(lower, token)

    return _WORD_TOKEN_RE.sub(_translate, repaired)


def _has_date_shape(text: str, *, repaired: str) -> bool:
    if _NUMERIC_DATE_SHAPE_RE.search(text) or _ISO_DATE_SHAPE_RE.search(text):
        return True
    has_month_word = any(
        token.lower() in _MONTH_WORDS
        for token in _WORD_TOKEN_RE.findall(repaired)
        if not token.isdigit()
    )
    has_year = bool(_FOUR_DIGIT_YEAR_RE.search(text))
    return has_month_word and has_year


def _try_parse_date(text: str, english_text: str) -> datetime | None:
    default = datetime(_SENTINEL_YEAR, 1, 1)
    has_year = bool(_FOUR_DIGIT_YEAR_RE.search(text))
    has_month_word = any(
        token.lower() in _MONTH_WORDS for token in _WORD_TOKEN_RE.findall(english_text)
    )
    # ISO 8601 (YYYY-MM-DD...) is unambiguous year-first -- `dayfirst=True`
    # would otherwise still swap month/day on the trailing `MM-DD` pair
    # (a documented dateutil quirk: `dayfirst` is applied token-by-token,
    # not format-aware).
    dayfirst = not _ISO_DATE_SHAPE_RE.search(text)

    try:
        parsed = _dateutil_parser.parse(
            english_text, dayfirst=dayfirst, fuzzy=False, default=default
        )
    except (ValueError, OverflowError, TypeError):
        if not (has_year or has_month_word):
            return None
        try:
            parsed = _dateutil_parser.parse(
                english_text, dayfirst=dayfirst, fuzzy=True, default=default
            )
        except (ValueError, OverflowError, TypeError):
            return None

    if parsed.year == _SENTINEL_YEAR and "1900" not in text:
        # dateutil silently back-filled a missing year from `default` --
        # treat "no real year present" as an explicit rejection rather
        # than a guess (never fall back to the wall clock: `default` is
        # pinned precisely so this parser is deterministic).
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_ARGENTINA_TZ)
    return parsed


def _scan_date_candidates(
    ordered: Sequence[RawTextBox], *, excluded_orders: frozenset[int]
) -> list[_Candidate]:
    candidates: list[_Candidate] = []
    for order, box in enumerate(ordered):
        if order in excluded_orders:
            continue
        repaired = _repair_month_tokens(box.text)
        if not _has_date_shape(box.text, repaired=repaired):
            continue
        english_text = _to_english_date_text(box.text)
        parsed = _try_parse_date(box.text, english_text)
        if parsed is None:
            continue
        candidates.append(
            _Candidate(
                value=parsed.isoformat(),
                raw_text=box.text,
                confidence=box.confidence,
                order=order,
                checksum_valid=True,
            )
        )
    return candidates


def _safe_within_bounds(candidate: _Candidate, *, reference: datetime) -> bool:
    try:
        extracted = datetime.fromisoformat(candidate.value)
        return is_within_date_bounds(
            extracted,
            reference=reference,
            max_past_days=_DATE_RANKING_MAX_PAST_DAYS,
            max_future_days=_DATE_RANKING_MAX_FUTURE_DAYS,
        )
    except (ValueError, TypeError):
        return False


def _select_date(candidates: Sequence[_Candidate], *, reference: datetime) -> _Candidate | None:
    """`is_within_date_bounds` is consulted only when >=2 candidates exist,
    and only as a ranking tiebreak -- never a rejection filter (rejecting
    would silently disable `DATE_OUT_OF_BOUNDS` downstream)."""
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    return max(
        candidates,
        key=lambda c: (_safe_within_bounds(c, reference=reference), -c.order),
    )


# ---------------------------------------------------------------------------
# Disambiguation -- keyword-proximity with signed scoring, positional
# fallback.
# ---------------------------------------------------------------------------

_DESTINATION_KEYWORDS: tuple[str, ...] = (
    "destino",
    "destinatario",
    "beneficiario",
    "beneficiaria",
    "receptor",
    "recibe",
    "acredita",
    "acreditacion",
    "credito",
    "para",
    "cobra",
    "a nombre de",
    "a:",
)
_ORIGIN_KEYWORDS: tuple[str, ...] = (
    "origen",
    "ordenante",
    "emisor",
    "titular",
    "remitente",
    "debita",
    "debito",
    "desde",
    "pagador",
    "envia",
    "de:",
)


def _compile_keyword_pattern(keywords: Sequence[str]) -> re.Pattern[str]:
    # `(?<!\w)`/`(?!\w)` instead of `\b` so trailing-colon tokens (`a:`,
    # `de:`) still match when followed by whitespace (a literal `\b` right
    # after `:` requires a word/non-word transition, which whitespace after
    # `:` never provides).
    alternation = "|".join(re.escape(keyword) for keyword in keywords)
    return re.compile(rf"(?<!\w)(?:{alternation})(?!\w)")


_DESTINATION_KEYWORD_RE = _compile_keyword_pattern(_DESTINATION_KEYWORDS)
_ORIGIN_KEYWORD_RE = _compile_keyword_pattern(_ORIGIN_KEYWORDS)


def _keyword_score(window: str) -> int:
    has_destination = bool(_DESTINATION_KEYWORD_RE.search(window))
    has_origin = bool(_ORIGIN_KEYWORD_RE.search(window))
    if has_destination and has_origin:
        return 0
    if has_destination:
        return 1
    if has_origin:
        return -1
    return 0


def _context_window(ordered: Sequence[RawTextBox], candidate: _Candidate) -> str:
    index = candidate.order
    anchor = ordered[index]
    start = max(0, index - _CONTEXT_BEFORE)
    end = min(len(ordered), index + _CONTEXT_AFTER + 1)
    window_boxes = [
        ordered[i]
        for i in range(start, end)
        if abs(ordered[i].top - anchor.top) <= _CONTEXT_MAX_DY_PX
    ]
    return _fold(" ".join(box.text for box in window_boxes))


def _disambiguate_destination(
    candidates: Sequence[_Candidate], ordered: Sequence[RawTextBox]
) -> _Candidate | None:
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    scored = [
        (candidate, _keyword_score(_context_window(ordered, candidate))) for candidate in candidates
    ]
    max_score = max(score for _, score in scored)
    if max_score > 0:
        tied = [candidate for candidate, score in scored if score == max_score]
        return min(tied, key=lambda c: c.order)

    # No destination signal anywhere: positional fallback -- second
    # candidate in reading order is the destination, first is the origin.
    by_order = sorted(candidates, key=lambda c: c.order)
    return by_order[1] if len(by_order) >= 2 else by_order[0]


def _select_identifier(
    candidates: Sequence[_Candidate], ordered: Sequence[RawTextBox]
) -> _Candidate | None:
    """0 candidates -> omit field; 1 -> surface regardless of checksum
    (locked rule, preserves `invalid_cbu_check_digit`); >=2 -> disambiguate
    within the checksum-valid subset when one exists, else across all."""
    deduped = _dedupe_candidates(candidates)
    if not deduped:
        return None
    if len(deduped) == 1:
        return deduped[0]

    valid = [candidate for candidate in deduped if candidate.checksum_valid]
    pool = valid if valid else deduped
    if len(pool) == 1:
        return pool[0]
    return _disambiguate_destination(pool, ordered)


def extract_core_fields(
    boxes: Sequence[RawTextBox], *, reference: datetime | None = None
) -> tuple[ExtractedField, ...]:
    """Scan -> validate -> select -> emit. Emits at most one
    `ExtractedField` per name, in `CORE_FIELD_NAMES` order --
    `detect_contradictions` treats two same-name entries as a
    contradiction, so collapsing to one is a correctness requirement."""
    ordered = _reading_order(boxes)
    effective_reference = reference if reference is not None else datetime.now(UTC)

    cbu_candidates = _scan_cbu_candidates(ordered)
    cuit_candidates = _scan_cuit_candidates(ordered)
    excluded_orders = frozenset(
        candidate.order for candidate in (*cbu_candidates, *cuit_candidates)
    )

    amount_candidates = _scan_amount_candidates(ordered)
    date_candidates = _scan_date_candidates(ordered, excluded_orders=excluded_orders)

    selected: dict[str, _Candidate | None] = {
        "amount": _select_amount(amount_candidates),
        "destination_cbu": _select_identifier(cbu_candidates, ordered),
        "cuit": _select_identifier(cuit_candidates, ordered),
        "date_time": _select_date(date_candidates, reference=effective_reference),
    }

    fields: list[ExtractedField] = []
    for name in CORE_FIELD_NAMES:
        candidate = selected[name]
        if candidate is None:
            continue
        fields.append(
            ExtractedField(
                name=name,
                raw_text=candidate.raw_text,
                normalized=candidate.value,
                confidence=candidate.confidence,
            )
        )
    return tuple(fields)
