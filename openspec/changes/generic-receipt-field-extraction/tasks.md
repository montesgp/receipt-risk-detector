# Tasks: Generic (label-independent) receipt field extraction

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 650-900 (field_parsers.py rewrite ~350, tests ~300, generate.py/manifest ~150-250 incl. binary fixture bytes) |
| 400-line budget risk | High |
| Chained PRs recommended | No (delivery strategy is `single-pr`) |
| Suggested split | Single PR, sliced into ordered commits (dependency-add → scanners → disambiguation → fixtures → tests) |
| Delivery strategy | single-pr |
| Chain strategy | size-exception |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Add `python-dateutil` dep + relock | commit 1 (this PR) | `uv run --project apps/api python -c "import dateutil"` | N/A — dependency-only, no behavior | Revert `pyproject.toml` line + `uv.lock` |
| 2 | Scanners (CBU/CUIT/amount/date) + disambiguation, RED-GREEN | commit 2 (this PR) | `uv run --project apps/api pytest tests/unit/test_ocr_field_parsers.py -q` | N/A — pure unit, no engine | Revert `field_parsers.py` + its test file |
| 3 | New fixtures (isolated slice per proposal's risk mitigation) | commit 3 (this PR) | `python samples/generate.py --check` | `uv run --project apps/api pytest tests/fixtures/test_manifest_integrity.py -q` | Revert `samples/generate.py` + `samples/manifest.json` + new PNGs |
| 4 | Integration proof on real engine | commit 4 (this PR) | `uv run --project apps/api pytest tests/integration/test_ocr_integration.py -q` | Real RapidOCR-onnxruntime engine run against new fixtures | Revert integration test additions only |

Note: `size-exception` requires maintainer approval per the review guard (single-pr delivery strategy maps to "Yes" decision needed). The proposal already flagged the fixture regeneration as the highest-risk slice for binary diff size — Unit 3 above isolates it as its own commit so a reviewer can skip re-diffing PNG bytes byte-by-byte and instead trust `--check`.

## Phase 1: Dependency

- [x] 1.1 RED: `uv run --project apps/api python -c "import dateutil.parser"` fails (module absent).
- [x] 1.2 GREEN: add `"python-dateutil>=2.9",` to `apps/api/pyproject.toml` `[project].dependencies`; add `"dateutil".msg = "python-dateutil is an adapter-only dependency (adapters/ocr/**)."` to `[tool.ruff.lint.flake8-tidy-imports.banned-api]`.
- [x] 1.3 Run `uv lock`; commit `uv.lock` diff. **Deviation**: design.md claimed the workspace `uv.lock` lives at the repo root — verified false (`git rev-parse --show-toplevel` + filesystem check: no `pyproject.toml`/`uv.lock` exists at the repo root at all). The lock file actually lives at `apps/api/uv.lock`, so `uv lock` was run from `apps/api/`, which is the only location that resolves.
- [x] 1.4 GREEN check: `uv run --project apps/api python -c "import dateutil.parser"` succeeds.

## Phase 2: Digit-run scanning primitives (CBU/CUIT) — spec FR-005, scenarios "Same field extracted despite different label wording", "Inline label:value", "Stray digit run ignored"

- [x] 2.1 RED in `apps/api/tests/unit/test_ocr_field_parsers.py`: `_digit_runs`/`_grouped_runs`/`_digit_candidates` extract `20-34240499-6` (Tier 1, hyphenated) and `2850 5909 4009 0418 1352 01` (Tier 2, spaced groups) as exact-length 11/22 digit strings; a 33-digit merged box yields nothing at Tier 1 and Tier 2 abandons on overflow.
- [x] 2.2 GREEN in `apps/api/src/receipt_risk/adapters/ocr/field_parsers.py`: implement `_fold`, `_digit_runs` (boundary-anchored regex `(?<![0-9A-Za-z])(\d[\d\-.]*\d)(?![0-9A-Za-z])`), `_grouped_runs` (space-separated all-digit token concatenation, abandon-on-overflow), `_digit_candidates(ordered, target)`.
- [x] 2.3 RED: `_scan_cuit_candidates`/`_scan_cbu_candidates` — inline `"CUIT: 20-12345678-9"` single-line box yields one 11-digit candidate; `"CVU:0000003100094065748023"` yields one 22-digit candidate; a lone 11-digit order ID (`"N° de operación 483927183"` + `"11 2345-6789"`) yields no CUIT candidate confused with a real one when a valid CUIT is also present.
- [x] 2.4 GREEN: implement `_scan_cuit_candidates(ordered)`, `_scan_cbu_candidates(ordered)` returning `_Candidate` (value, raw_text, confidence, order, checksum_valid via `validate_cuit`/`validate_cbu`).
- [x] 2.5 RED: de-duplication — same CBU digit string printed twice in two boxes collapses to one candidate.
- [x] 2.6 GREEN: de-dup candidates by normalized digit string before selection.

## Phase 3: Amount and date scanners — spec FR-005, scenario "Wide date/time format coverage including an OCR-typo month name"

- [x] 3.1 RED: `_scan_amount_candidates` — symbol-prefixed AR `$ 8.000` → `8000`; US `$1,234.56` → `1234.56`; two amounts present (fee + transferred) → largest `Decimal` wins within the winning tier; symbol-prefixed tier beats grouped-no-symbol tier.
- [x] 3.2 GREEN: implement `_scan_amount_candidates(ordered)` (two match tiers) + `_select_amount(candidates)` (prefer tier 1, then largest `Decimal`), both delegating value parsing to `normalize_amount` verbatim.
- [x] 3.3 RED: `_repair_month_tokens` — `"1 de ag0sto de 2026, 14:43 hs"` repairs `ag0sto` → `agosto` (digit→letter map, mixed-alnum tokens only, pure-digit tokens like `2026` untouched); a token that doesn't land on a known month word is left unrepaired.
- [x] 3.4 GREEN: implement `_repair_month_tokens(text)` per the digit→letter map, **extended with `2→z`** (see Deviations below), and the Spanish→English month/connector substitution table.
- [x] 3.5 RED: `_scan_date_candidates` parses `"15/03/2026 14:30"`, `"2026-03-15T14:30:00"`, `"15 de marzo de 2026"`, `"15 de mar20 de 2026"` (digit-typo) to the same ISO instant; a box that already produced an accepted CUIT/CBU candidate is excluded via `excluded_orders`; unparseable text yields no candidate (never raises).
- [x] 3.6 GREEN: implement `_scan_date_candidates(ordered, *, excluded_orders)` — shape gate, `_repair_month_tokens`, `dateutil.parser.parse(..., default=datetime(1900,1,1))` with the documented single fuzzy retry, and the `year == 1900` rejection guard. **Deviation**: `dayfirst` is set dynamically (`False` only for ISO-shaped `YYYY-MM-DD...` text, `True` otherwise) — see Deviations below.
- [x] 3.7 RED: `_select_date` — with `reference` injected, a deliberately implausible-but-only candidate is still selected (bounds are ranking-only, never a rejection filter).
- [x] 3.8 GREEN: implement `_select_date(candidates, *, reference)` calling `is_within_date_bounds` only for ranking among ≥2 candidates, with the widened window; wrapped in `_safe_within_bounds` to tolerate naive/aware `datetime` comparison mismatches without raising.

## Phase 4: Disambiguation and selection — spec scenarios "Two CUIT/CBU pairs disambiguated by keyword proximity", "...by position", "Sole checksum-failing candidate is still surfaced"

- [x] 4.1 RED: `_context_window`/`_keyword_score` — a candidate box near `"destino"`/`"beneficiario"` scores `+1`; near `"origen"`/`"remitente"` scores `-1`; both present scores `0`; window includes 2 boxes before / 1 after within `140.0px` vertical delta, folded (NFKD, lower-cased) so `"acreditación"` matches `"acreditacion"`.
- [x] 4.2 GREEN: implement `_fold`, `_context_window(ordered, candidate)` (`_CONTEXT_BEFORE=2, _CONTEXT_AFTER=1, _CONTEXT_MAX_DY_PX=140.0`), `_keyword_score(window)` with the two keyword tuples from design.md.
- [x] 4.3 RED: `_disambiguate_destination` — exactly one candidate wins with no scoring; two valid candidates with clear destination keyword near one → that one wins; no destination signal anywhere → positional fallback (second candidate wins).
- [x] 4.4 GREEN: implement `_disambiguate_destination(candidates, ordered)` per the resolution order in design.md.
- [x] 4.5 RED: locked rule 3 — single CBU-shaped candidate with a deliberately wrong check digit (only candidate for the slot) is still surfaced with `normalized` populated; feed the result through the existing `application/financial_validation.py` pipeline and assert `INVALID_CBU_CHECK_DIGIT` still fires.
- [x] 4.6 GREEN: implement `_select_identifier(candidates, ordered)` — 0 candidates → omit field; 1 → surface regardless of checksum; ≥2 → disambiguate within the checksum-valid subset when one exists, else across all. **Deviation**: signature is `(candidates, ordered)`, not `(name, candidates)` — design.md's own "Interfaces/Contracts" table does not list `_select_identifier` at all, and `ordered` is required for keyword-proximity disambiguation.
- [x] 4.7 RED: `extract_core_fields` emits at most one `ExtractedField` per name in `CORE_FIELD_NAMES` order for every scenario above; `detect_contradictions(fields) == []` on the two-pair fixtures.
- [x] 4.8 GREEN: rewired `extract_core_fields(boxes, *, reference=None)` to call `_reading_order` → four scanners → four selectors → collapse to ≤1 field per name; kept `RawTextBox`, `boxes_from_engine_output`, `CORE_FIELD_NAMES` verbatim; removed `_LABEL_TO_FIELD`, `_nearest_value_below`, `_normalize_digits_of_length`, `_normalize_date`, `_MAX_LABEL_VALUE_GAP_PX`.
- [x] 4.9 Verified `apps/api/src/receipt_risk/adapters/ocr/paddle_onnx.py`'s call site (`extract_core_fields(boxes1)` / `extract_core_fields(boxes2)`) needs no change — the new `reference` parameter is optional keyword-only and defaults to `None` (adapter resolves it to `datetime.now(UTC)` internally). No edit made.

## Phase 5: Regression check (no rewrite)

- [x] 5.1 Ran `uv run --project apps/api pytest tests/unit/test_financial_validation_fixture.py -q` unchanged — `invalid_cbu_check_digit` fixture still yields `INVALID_CBU_CHECK_DIGIT` end-to-end. PASSED, no source edits in `application/financial_validation.py`.

## Phase 6: New fixtures (isolated commit slice per proposal risk mitigation)

- [x] 6.1 Added literals `ORIGIN_CBU`, `ORIGIN_CUIT`, `ORIGIN_BENEFICIARY`, `ALT_AMOUNT = "8.000"`, `ALT_DATE_TEXT`, `ALT_DATE_ISO = "2026-08-01T14:43:00"`, `DECOY_PHONE` in `samples/generate.py`.
- [x] 6.2 RED in new `apps/api/tests/fixtures/test_origin_identifiers_checksum_valid.py`: asserts `validate_cbu(ORIGIN_CBU).is_valid` and `validate_cuit(ORIGIN_CUIT).is_valid` are both `True`.
- [x] 6.3 GREEN: computed `ORIGIN_CBU = "0720001400004444444448"` / `ORIGIN_CUIT = "27098765439"` via `mod10_check_digit`/CUIT mod-11 arithmetic (not hand-typed); Phase 6.2 test passes.
- [x] 6.4 Added four new deterministic templates/render functions to `samples/generate.py`: `_render_labeled_rows`/`_render_values_only` used by `alt_vocabulary_inline`, `no_label_layout`, `two_party_labeled`, `two_party_no_labels`.
- [x] 6.5 Regenerated: `python samples/generate.py` wrote 4 new PNGs under `samples/images/` and updated `samples/manifest.json` (additive `declared_fields` keys `origin_cbu`/`origin_cuit` on the two-party fixtures; `schema_version` stays `1`; verified via `git diff --stat` that the diff is purely additive — 10 existing digests unchanged).
- [x] 6.6 Verified: `python samples/generate.py --check` passes; `uv run --project apps/api pytest tests/fixtures -q` passes (3 tests, including the new checksum-guard test).

## Phase 7: Fixture-based integration tests — spec scenarios end-to-end

- [x] 7.1 RED/GREEN in `apps/api/tests/unit/test_ocr_field_parsers.py`: hand-written `RawTextBox` list matching `alt_vocabulary_inline`'s layout extracts all 4 core fields with matching `normalized` values.
- [x] 7.2 hand-written `RawTextBox` list matching `no_label_layout` extracts all 4 core fields and ignores the decoy operation-id/phone digit runs.
- [x] 7.3 hand-written `RawTextBox` lists matching `two_party_labeled` and `two_party_no_labels` each yield exactly one `destination_cbu` and one `cuit`, matching the destination pair in both the keyword-driven and positional-fallback cases.
- [x] 7.4 Confirmed 7.1-7.3 pass against the Phase 2-4 implementation.
- [x] 7.5 Added `test_real_engine_extracts_all_core_fields_from_alt_vocabulary_fixture` and `test_real_engine_selects_destination_pair_on_two_party_labeled_fixture` to `apps/api/tests/integration/test_ocr_integration.py`, following the file's existing `RECEIPT_RISK_OCR_MODEL_DIR`-gated skip pattern. **Not executed in this sandbox** (no baked OCR model dir available locally, same as the pre-existing integration tests in this file — all 14 integration tests in this module report `skipped`, not `passed`). CI is expected to run these once `RECEIPT_RISK_OCR_MODEL_DIR` is set via `scripts/fetch_ocr_models.py`.

## Phase 8: Batch 2 — CRITICAL fix from sdd-verify (verify-report.md Critical Finding 1)

- [x] 8.1 RED: added `test_has_date_shape_accepts_year_glued_to_trailing_connector_text`, `test_scan_date_candidates_parses_year_glued_to_connector_text`, and `test_extract_core_fields_real_mercado_pago_ocr_text_extracts_all_four_fields` to `apps/api/tests/unit/test_ocr_field_parsers.py`, using the literal production OCR text from the verify report (`"$ 8.000"`, `"CUIT/CUIL:20-34240499-6"`, `"CVU:0000003100094065748023"`, `"30/ag0sto/2026alas20:53."`). Confirmed all 3 fail before the fix (`date_time` not extracted; only 3/4 core fields).
- [x] 8.2 GREEN: fixed `_FOUR_DIGIT_YEAR_RE` in `apps/api/src/receipt_risk/adapters/ocr/field_parsers.py` from `\b\d{4}\b` to `(?<!\d)\d{4}(?!\d)`. Root cause: `\b` treats digits and letters as the same "word" class, so a year glued directly to trailing alphabetic connector text (OCR dropping the space in "a las" → "alas") has no boundary transition after the year and never matched. The digit-adjacency lookaround preserves the original false-positive guard (a 4-digit year is never sliced out of a longer all-digit run, e.g. CBU/CUIT/phone number) while no longer rejecting a year immediately followed or preceded by letters. All 3 new tests pass after the fix; `_try_parse_date` (unchanged) correctly parses the resulting text, confirming the shape-gate was the sole defect.
- [x] 8.3 Re-ran full suite (`uv run --project apps/api pytest apps/api/tests -q`, exit code 0, no failures) and `uv run --project apps/api ruff check apps/api` (all checks passed) — no regressions in the other 3 date-format scenarios (numeric DD/MM/YYYY, ISO 8601, day-month-name) or `invalid_cbu_check_digit`.

## Key Learnings

1. The existing `field_parsers.py` uses a `_LABEL_TO_FIELD` map + nearest-value-below pairing that must be fully replaced, not extended, to satisfy vocabulary independence.
2. `validate_cbu`/`validate_cuit` already return structured `ChecksumResult` with `failure` reasons, so the new scanners can reuse them directly as the detection signal without re-deriving checksum math.
3. `apps/api/pyproject.toml`'s `testpaths = ["tests"]` and `uv.lock` living at the repo root (workspace) mean dependency changes must be relocked from the repo root, not `apps/api/`.
4. `samples/generate.py`'s fixture generation is fully deterministic (no RNG/timestamp/system fonts), so new fixtures must follow the same literal-constant pattern to keep `--check` byte-stable.
5. The `invalid_cbu_check_digit` fixture's regression coverage lives in `test_financial_validation_fixture.py`, separate from `test_ocr_field_parsers.py`, confirming the design's claim that checksum-failure signaling stays entirely in `application/financial_validation.py`.
