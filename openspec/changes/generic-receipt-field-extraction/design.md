# Design: Generic (label-independent) receipt field extraction

## Technical Approach

`adapters/ocr/field_parsers.py` is rewritten from **label-map + nearest-value-below pairing** to a
**four-stage pipeline**: `scan → validate → select → emit`. Every core field gets an independent
scanner that walks the reading-ordered `RawTextBox` list looking for *value shapes*, never labels.
Labels re-enter only in the `select` stage, and only for `destination_cbu` / `cuit`, as a
keyword-proximity ranking signal over already-found candidates.

Layering is unchanged: `field_parsers.py` stays adapter-only, imports the pure `domain.financial.*`
validators (`validate_cuit`, `validate_cbu`, `normalize_amount`, `is_within_date_bounds`) and
`domain.analysis.ExtractedField`. No domain/application file is modified. `paddle_onnx.py`'s call
site `extract_core_fields(boxes)` keeps working — the only signature change is a new **optional
keyword-only** `reference: datetime | None = None`.

**Hard invariant**: `extract_core_fields` emits **at most one** `ExtractedField` per name, in
`CORE_FIELD_NAMES` order. `detect_contradictions` treats two same-name entries as a contradiction,
so collapsing to one is a correctness requirement, not an optimisation.

## Architecture Decisions

### Decision: Two-tier boundary-anchored digit-run scan

**Choice**: Tier 1 regex `(?<![0-9A-Za-z])(\d[\d\-.]*\d)(?![0-9A-Za-z])`, digits stripped, accepted
only when the digit count is **exactly** 11 (CUIT) or 22 (CBU). Tier 2 runs only when Tier 1 found
nothing for that target inside a box: split the box into space-separated all-digit group tokens and,
for each start index, concatenate left-to-right — accept on exact `== target`, abandon on `> target`.

**Alternatives considered**: (a) plain `\d{11}` / `\d{22}` — misses `20-34240499-6` and grouped
`2850 5909 4009 0418 1352 01`; (b) sliding window over any long digit run — reintroduces the
false-positive class the anchoring exists to kill.

**Rationale**: the alnum lookaround pulls `20-34240499-6` out of `CUIT/CUIL:20-34240499-6` and
`0000003100094065748023` out of `CVU:0000003100094065748023` (both preceded by `:`), while rejecting
letter-glued order IDs. Exact-length equality means a merged `CBU CUIT` box (33 digits) is rejected
at Tier 1, and Tier 2's abandon-on-overflow keeps it from silently splicing across fields. `,` and
`/` and `:` are deliberately **not** separators, so `125.000,00` yields only a 6-digit run and
`01/09/2026` yields `01`,`09`,`2026` — neither can reach 11 or 22.

### Decision: The parser locates the amount; `normalize_amount` decides the convention

**Choice**: `_scan_amount_candidates` only extracts a substring, then passes it **verbatim** to
`normalize_amount`. Two match tiers: (1) symbol-prefixed `(?:AR\$|US\$|\$|ARS|USD)\s*(-?\d[\d.,]*)`,
(2) grouped-without-symbol `-?\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?`. Selection: prefer tier 1 over
tier 2; within a tier, the **largest** `Decimal`.

**Alternatives considered**: detecting AR vs US locale in the parser and pre-rewriting separators.

**Rationale**: `normalize_amount` already resolves both conventions (`$ 8.000` → `8000`,
`$1,234.56` → `1234.56`); duplicating that logic would create two divergent sources of truth. The
"largest" tiebreak assumes the transferred amount dominates fees/commissions on a transfer receipt —
a documented risk when a running balance is printed, accepted for this change (no keyword
disambiguation for amount).

### Decision: Spanish-aware, clock-independent date pipeline

`dateutil` does **not** understand Spanish month names, so pre-normalization does two jobs, in order:

| Step | Operation |
|---|---|
| 1 | Shape gate: box must match a date shape (`d[/-.]m[/-.]y`, ISO `YYYY-MM-DD`, or `<d> <monthword> <y>`) **and** must not have produced an accepted CUIT/CBU candidate. |
| 2 | Digit→letter repair, applied **only to mixed alnum tokens** (pure-digit tokens untouched, so `2026` survives): substitute `0→o 1→l 3→e 4→a 5→s 6→g 8→b 9→g`; keep the repaired token **only if** it lands exactly on a known month word. `ag0sto → agosto`. |
| 3 | Spanish→English month substitution (`enero→January` … `dic→Dec`, incl. `set`/`sep`) and connector stripping (`de`, `del`, `a`, `las`, `hs`, `hrs`, `horas`). |
| 4 | `dateutil.parser.parse(text, dayfirst=True, fuzzy=False, default=datetime(1900,1,1))`. On `ValueError`/`OverflowError`/`TypeError`, retry once with `fuzzy=True` **only if** the text still contains a 4-digit year or a month word; otherwise no candidate from this box. |
| 5 | Reject if `parsed.year == 1900` and `"1900"` is absent from the text (dateutil filled a missing year from `default`). |
| 6 | `normalized = parsed.isoformat()`. |

**Rationale for `default=`**: without it dateutil back-fills missing components from
`datetime.now()`, making the parser clock-dependent and non-deterministic. Pinning to 1900 plus the
step-5 guard makes "no year present" an explicit rejection instead of a silent guess.

**Output contract**: `parsed.isoformat()` is a strict superset of today's `_normalize_date`
(which echoed the input after an `fromisoformat` round-trip check). `2026-09-01T14:43:00-03:00`
round-trips byte-identically, so the existing test assertion and
`financial_validation._parse_datetime`'s `datetime.fromisoformat` both keep working unchanged.

### Decision: `is_within_date_bounds` is a *ranking* backstop, never a rejection filter

**Choice**: bounds are consulted only when **more than one** date candidate exists, and with a wide
`max_past_days=3650, max_future_days=3650` window — not the validator's default 365/1.

**Alternatives considered**: rejecting out-of-bounds dates in the parser.

**Rationale**: rejecting would drop the field, and `DATE_OUT_OF_BOUNDS` in
`application/financial_validation.py` would then never fire — a silent behaviour regression. The
wide window only discards absurd parses (e.g. year 0020). `reference` defaults to `datetime.now(UTC)`
inside the adapter; tests inject it explicitly.

### Decision: single candidate wins regardless of checksum (locked)

`_select_identifier(name, candidates)`:

| Candidate count | Behaviour |
|---|---|
| 0 | no `ExtractedField` emitted (coverage counts the miss, as today) |
| 1 | emit with `normalized` populated **even if the checksum fails** |
| ≥2 | if any candidate passes its checksum, disambiguate **within the valid subset only**; otherwise disambiguate across all |

Candidates are de-duplicated by normalized digit string first (a CBU printed twice is one candidate).
This is what preserves the `invalid_cbu_check_digit` fixture: the mutated CBU is still shape-matched
(the scan is checksum-independent), is the only candidate, is surfaced with `normalized`, and
`financial_validation.py` emits `INVALID_CBU_CHECK_DIGIT` + `REVIEW_RECOMMENDED` exactly as today.

### Decision: keyword-proximity disambiguation with signed scoring and positional fallback

Text is *folded* first: NFKD-normalized, combining marks dropped, lower-cased (so `acreditación`
matches `acreditacion`). No new dependency — `unicodedata` is stdlib.

```python
_DESTINATION_KEYWORDS = ("destino", "destinatario", "beneficiario", "beneficiaria",
                         "receptor", "recibe", "acredita", "acreditacion", "credito",
                         "para", "cobra", "a nombre de", "a:")
_ORIGIN_KEYWORDS = ("origen", "ordenante", "emisor", "titular", "remitente",
                    "debita", "debito", "desde", "pagador", "envia", "de:")
```

Matched as whole words (`\b…\b`) on the folded window; bare `a` is excluded as too noisy, `a:`/`de:`
only as exact inline-label tokens.

**Context window** for a candidate = its own box text + the **2** boxes immediately before it and
the **1** box immediately after it in reading order, keeping only boxes whose `|top - candidate.top|
≤ 140.0 px`. Constants: `_CONTEXT_BEFORE = 2`, `_CONTEXT_AFTER = 1`, `_CONTEXT_MAX_DY_PX = 140.0`
(≈ one label+value row at `generate.py`'s `ROW_HEIGHT = 130`). Reasoned defaults, not tuning knobs —
same convention as the ruleset/C2PA marker constants.

**Score** = `+1` if any destination keyword is in the window, `-1` if any origin keyword is. Both →
`0`. Resolution order:

1. exactly one candidate → it wins (no scoring);
2. unique max score `> 0` → winner;
3. tied max score `> 0` → earliest in reading order among the tied set;
4. max score `≤ 0` (no destination signal anywhere) → **positional fallback**: second candidate in
   reading order when ≥2 exist, otherwise the only one.

## Data Flow

    boxes_from_engine_output(raw)  ──→  _reading_order()  (sort by (top, left))
                                              │
              ┌───────────────┬───────────────┼───────────────┬────────────────┐
              ▼               ▼               ▼               ▼                │
      _scan_cbu_cands   _scan_cuit_cands  _scan_amount    _scan_date_cands ◀───┘
        (22 digits)      (11 digits)       (currency)      (excl. id boxes)
              │               │               │               │
              ▼               ▼               ▼               ▼
      _disambiguate_    _disambiguate_    _select_amount   _select_date
       destination       destination       (tier, max)     (bounds rank)
              └───────────────┴───────────────┴───────────────┘
                                    ▼
                     exactly ≤1 ExtractedField per name
                                    ▼
             paddle_onnx._coverage → financial_validation → detect_contradictions

## File Changes

| File | Action | Description |
|---|---|---|
| `apps/api/src/receipt_risk/adapters/ocr/field_parsers.py` | Modify | Full rewrite of extraction; `RawTextBox`, `boxes_from_engine_output`, `CORE_FIELD_NAMES` kept verbatim |
| `apps/api/tests/unit/test_ocr_field_parsers.py` | Modify | Scenario matrix below |
| `apps/api/pyproject.toml` | Modify | `"python-dateutil>=2.9",` in `[project].dependencies`; `"dateutil".msg = "python-dateutil is an adapter-only dependency (adapters/ocr/**)."` in `[tool.ruff.lint.flake8-tidy-imports.banned-api]` |
| `uv.lock` (repo root) | Modify | Regenerate: `uv lock` from the repo root (workspace lock, not `apps/api/`) |
| `samples/generate.py` | Modify | 4 new templates + literals, new digest keys, new manifest entries |
| `samples/manifest.json` | Modify | Regenerate via `python samples/generate.py`; 4 new entries, 10 existing digests unchanged |

## Interfaces / Contracts

```python
@dataclass(frozen=True, slots=True)
class _Candidate:
    value: str            # digits | Decimal str | ISO-8601
    raw_text: str         # originating box text
    confidence: Decimal
    order: int            # index in reading order
    checksum_valid: bool  # always True for amount/date

def _fold(text: str) -> str
def _digit_runs(text: str) -> list[str]
def _grouped_runs(text: str, target: int) -> list[str]
def _digit_candidates(ordered: Sequence[RawTextBox], target: int) -> list[_Candidate]
def _scan_cuit_candidates(ordered) -> list[_Candidate]
def _scan_cbu_candidates(ordered) -> list[_Candidate]
def _scan_amount_candidates(ordered) -> list[_Candidate]
def _repair_month_tokens(text: str) -> str
def _scan_date_candidates(ordered, *, excluded_orders: frozenset[int]) -> list[_Candidate]
def _context_window(ordered, candidate: _Candidate) -> str
def _keyword_score(window: str) -> int
def _disambiguate_destination(candidates, ordered) -> _Candidate | None
def _select_amount(candidates) -> _Candidate | None
def _select_date(candidates, *, reference: datetime) -> _Candidate | None

def extract_core_fields(
    boxes: Sequence[RawTextBox], *, reference: datetime | None = None
) -> tuple[ExtractedField, ...]
```

## Fixture Plan

All four are OCR fixtures and land in `samples/images/` (root), **not** `images/reference/`, so the
vision reference-embedding builder does not pick them up.

| Fixture id | Proves |
|---|---|
| `alt_vocabulary_inline` | Disjoint labels (`Importe transferido`, `Realizada el`, `Para`, `CVU`, `CUIT/CUIL`); inline `CVU: …` / `CUIT/CUIL:…`; AR amount `$ 8.000`; date `1 de ag0sto de 2026, 14:43 hs` (typo'd month + Spanish connectors) |
| `no_label_layout` | Values only, zero labels, plus decoys (`Comprobante`, 9-digit operation id, a phone number) |
| `two_party_labeled` | Origin block (`Cuenta origen` / `Titular`) then destination block (`Destino` / `Beneficiario`); **both** CBUs and **both** CUITs checksum-valid, so the test proves keyword selection rather than checksum selection |
| `two_party_no_labels` | Same two pairs with no keyword text anywhere → positional fallback (second = destination) |

New `generate.py` literals: `ORIGIN_CBU`, `ORIGIN_CUIT`, `ALT_AMOUNT = "8.000"`,
`ALT_DATE_TEXT`, `ALT_DATE_ISO = "2026-08-01T14:43:00"`; destination reuses `VALID_CBU` / `CUIT`.
`ORIGIN_CBU`/`ORIGIN_CUIT` must be *computed* to be checksum-valid and asserted with
`validate_cbu`/`validate_cuit` in a test — never hand-typed. Manifest entries reuse the existing
schema; `declared_fields` gains `origin_cbu` / `origin_cuit` keys on the two-party fixtures.
`schema_version` stays `1` (additive keys only). `samples/generate.py --check` and
`tests/fixtures/test_manifest_integrity.py` both keep passing after regeneration.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | Scan/select functions | Hand-written `RawTextBox` lists (no engine): existing clean layout regression; alt-vocabulary; inline `label:value`; no-label; spaced groups `2850 5909 4009 0418 1352 01`; AR `$ 8.000`→`8000`, US `$1,234.56`→`1234.56`, fee-vs-amount tiering; dates `01/09/2026 14:43`, ISO w/ offset, `1 de agosto de 2026`, `1 de ag0sto de 2026`, `Sep 1, 2026`, unparseable→omitted; `reference` injected for determinism |
| Unit | Disambiguation | Two valid pairs + destination keywords → destination wins; origin-only keyword near A → B wins; zero keywords → second-in-order wins; **assert exactly one field per name** and `detect_contradictions(fields) == []` |
| Unit | Locked rule 3 | Single checksum-failing CBU → `normalized` populated; feed the result into `validate_financials` → `INVALID_CBU_CHECK_DIGIT` still emitted |
| Unit | False positives | Box with only `N° de operación 483927183` + `11 2345-6789` → no `cuit`/`destination_cbu`; malformed engine rows still dropped, never raised |
| Fixture | New samples | `tests/fixtures/test_manifest_integrity.py` (sha256 drift) + `samples/generate.py --check` in CI |
| Integration | Real engine | `tests/integration/test_ocr_integration.py` — all 4 core fields extracted from `alt_vocabulary_inline`; destination pair selected on `two_party_labeled` |

Strict TDD: every row above is written RED before `field_parsers.py` is touched.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or
process-integration boundary. `python-dateutil` is pure-Python with no C extension and is invoked
only on already-extracted OCR text; `parse` is called with `fuzzy` and `default` pinned and every
exception path is caught, so it cannot propagate an exception into the adapter's retry state machine.

## Migration / Rollout

No migration. `ExtractedField` shape, `AnalyzerResult`, and the API contract are byte-identical
before and after. Rollback = single-commit revert of the six files above.

## Open Questions

None — all defaults (keyword vocabulary, `_CONTEXT_BEFORE/_AFTER`, `_CONTEXT_MAX_DY_PX`, amount
tiering, the ±10-year ranking window, the digit→letter repair map) are decided above as reasoned
constants.
