# Tasks: Scoring Confidence Calibration

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 650-850 (prod ~150; ~14 golden test files ~30-60 lines each) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 -> PR 2 -> PR 3 |
| Delivery strategy | single-pr |
| Chain strategy | size-exception |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: size-exception
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Evidence honesty: `_completeness` provenance fix, `evidence_observed` field, `ENGINE_VERSION` bump, c2pa adapter | PR 1 | `uv run pytest tests/unit/test_scoring.py tests/unit/test_c2pa_reader.py tests/unit/test_domain_analysis.py -q` | N/A — pure domain unit, no external service | revert commit; `evidence_observed` is additive/optional |
| 2 | OCR-zero floor + combination floor + v2026_09_05 ruleset + bootstrap wiring | PR 2 | `uv run pytest tests/unit/test_scoring.py tests/unit/test_ruleset.py -q` | N/A — deterministic scoring, no I/O | repoint `bootstrap/app.py` to `RULESET_2026_09_04` |
| 3 | Web copy + golden regeneration across ~14 files + docs | PR 3 | `pnpm -C apps/web test -- ScoreSummary ResultView key-parity literal-audit` then `uv run pytest -q` | Manual: upload a no-text receipt in dev UI, confirm hedged copy | revert commit; i18n key is additive |

Single PR is over budget; `single-pr` delivery strategy requires an explicit `size:exception` decision before `sdd-apply` proceeds, or the user must accept the 3-unit chain above.

## Phase 1: Evidence Honesty (shared, retroactive)

- [x] 1.1 RED: `tests/unit/test_scoring.py` — add case: `_completeness("provenance", AnalyzerResult(status="completed", evidence_observed=False))` returns `Decimal("0")`; assert `_completeness("vision"/"metadata", status="completed")` unchanged at `1`.
- [x] 1.2 GREEN: `domain/analysis.py` — add `evidence_observed: bool | None = None` as last field of `AnalyzerResult` (frozen dataclass, additive).
- [x] 1.3 GREEN: `domain/scoring.py::_completeness` — for `role != "ocr"`, return `Decimal("0")` when `result.status != "completed" or result.evidence_observed is False`, else `Decimal("1")`.
- [x] 1.4 RED: `tests/unit/test_c2pa_reader.py` — add cases: manifest found -> `evidence_observed=True`; no manifest / undecodable -> `evidence_observed=False`.
- [x] 1.5 GREEN: `adapters/provenance/c2pa_reader.py` — set `evidence_observed=manifest is not None` on the returned `AnalyzerResult`; add docstring note per design.
- [x] 1.6 Confirm no change needed to `adapters/vision/mobilenet_embedder.py` or `adapters/metadata/exiftool.py` (design: their `status="completed"` already implies real evaluation) — add a one-line comment or assertion in existing tests if not already covered. (verified via `test_completeness_vision_and_metadata_unchanged_at_one_when_completed`; also added `evidence_observed is False` assertion to the real-fixture `test_metadata_provenance_integration.py::test_c2pa_reader_inspects_real_fixture_without_manifest_neutrally`.)
- [x] 1.7 GREEN: `application/analyze_receipt.py` — bump `ENGINE_VERSION = "0.1.0"` -> `"0.2.0"`.
- [x] 1.8 GREEN: `docs/API.md` — update `"engine_version": "0.1.0"` examples (lines ~29, ~65) to `"0.2.0"`.

## Phase 2: OCR-Zero Floor and Combination Floor

- [x] 2.1 RED: `tests/unit/test_scoring.py` — fixture (a): zero-OCR core fields + no C2PA manifest -> `Classification.INCONCLUSIVE` (coverage `0.32`).
- [x] 2.2 RED: `tests/unit/test_scoring.py` — fixture (b): real receipt, 1/4 core fields, no C2PA -> coverage `0.43`, classification unchanged (regression guard, NOT forced inconclusive).
- [x] 2.3 RED: `tests/unit/test_scoring.py` — fixture: zero-OCR + `VALID_AI_GENERATED_CLAIM` fired -> stays `HIGH_RISK` (verdict-signal override, not downgraded). (also added a dedicated test proving the floor fires independently of the coverage gate when coverage is above threshold.)
- [x] 2.4 GREEN: `domain/scoring.py` — add `_verdict_signals(signals, ruleset)`: signals with `Severity.CRITICAL` and a `ruleset.critical_floor` entry.
- [x] 2.5 GREEN: `domain/scoring.py` — add `_ocr_core_fields_empty(statuses)`: True when an `ocr`-role result is present and yielded zero core fields. (Restricted to `status in ("completed","partial")` — a `failed`/`timed_out` OCR result must NOT trigger the floor, per the pre-existing "a failed analyzer never forces INCONCLUSIVE alone" decision; this surfaced as a real regression against `test_confidence_independent_of_risk_ocr_fails_others_succeed_not_inconclusive` and was fixed by scoping the check.)
- [x] 2.6 GREEN: `domain/scoring.py::score()` — force `Classification.INCONCLUSIVE` when `_ocr_core_fields_empty(...)` is True and `_verdict_signals(...)` is empty; leave the existing `evidence_coverage < threshold` gate byte-identical.
- [x] 2.7 RED: `tests/unit/test_ruleset.py` — assert `ScoringRuleset` requires `combination_floors: Mapping[frozenset[SignalCode], int]`; `v2026_09_01`/`v2026_09_04` have `combination_floors == {}`.
- [x] 2.8 GREEN: `domain/ruleset.py` — add `combination_floors: Mapping[frozenset[SignalCode], int]` field after `critical_floor` (no default, frozen dataclass).
- [x] 2.9 GREEN: `domain/rulesets/v2026_09_01.py`, `v2026_09_04.py` — add explicit `combination_floors={}`.
- [x] 2.10 RED: `tests/unit/test_scoring.py`/`test_ruleset.py` — fixture (c): both `CORE_FIELD_EXTRACTION_FAILED` + `DATE_OUT_OF_BOUNDS` fired -> risk_score floors at `55`; each alone -> unchanged score; empty `combination_floors` mapping is a no-op.
- [x] 2.11 GREEN: `domain/scoring.py::_risk_score` — after `critical_floor`, compute `fired = {s.code for s in signals}`; add `[f for codes, f in ruleset.combination_floors.items() if codes <= fired]` to the floor list; keep the existing `max()` pattern.
- [x] 2.12 GREEN: create `domain/rulesets/v2026_09_05.py` — copy-forward of `v2026_09_04` fields; `version = "2026-09-05"`; `combination_floors = {frozenset({SignalCode.CORE_FIELD_EXTRACTION_FAILED, SignalCode.DATE_OUT_OF_BOUNDS}): 55}`.
- [x] 2.13 RED: `tests/unit/test_ruleset.py` — `RULESETS` has 3 entries; `v2026_09_05.version == "2026-09-05"`.
- [x] 2.14 GREEN: `domain/rulesets/__init__.py` — import and register `RULESET_2026_09_05` in `RULESETS`.
- [x] 2.15 GREEN: `bootstrap/app.py` — import `RULESET_2026_09_05`, repoint the 3 sites (use-case construction, `/version` endpoint reference, any default) from `RULESET_2026_09_04` to `RULESET_2026_09_05`.
- [x] 2.16 RED: `tests/unit/test_bootstrap_app.py` — assert active ruleset is `RULESET_2026_09_05`.
- [x] 2.17 GREEN: `docs/API.md` — update `"ruleset_version": "2026-09-04"` examples (lines ~30, ~66) to `"2026-09-05"`. (done together with 1.8's engine_version edit.)

## Phase 3: Web Copy

- [x] 3.1 RED: `apps/web/tests/unit/ScoreSummary.test.ts` — `INCONCLUSIVE` + signal with `code === 'CORE_FIELD_EXTRACTION_FAILED'` and `evidence.reason === 'no_text_detected'` renders `result.inconclusiveNoTextNote`; `INCONCLUSIVE` without it renders `result.inconclusiveNote`; non-`INCONCLUSIVE` renders neither.
- [x] 3.2 RED: `apps/web/tests/unit/ResultView.test.ts` — `noTextDetected` derived correctly from signals and passed to `ScoreSummary`.
- [x] 3.3 RED: `apps/web/tests/unit/key-parity.test.ts` — new key present with matching shape in both `en.json`/`es.json`.
- [x] 3.4 RED: `apps/web/tests/unit/literal-audit.test.ts` — new strings contain no absolute-verdict language ("is not a transfer" / "no es un comprobante" forbidden).
- [x] 3.5 GREEN: `apps/web/src/lib/i18n/messages/es.json` — add `"result.inconclusiveNoTextNote"` after `result.inconclusiveNote` (hedged Spanish text per design).
- [x] 3.6 GREEN: `apps/web/src/lib/i18n/messages/en.json` — add mirrored English key.
- [x] 3.7 GREEN: `apps/web/src/lib/components/ResultView.svelte` — derive `noTextDetected` from `result.signals`, pass to `ScoreSummary`.
- [x] 3.8 GREEN: `apps/web/src/lib/components/ScoreSummary.svelte` — accept `noTextDetected` prop, select `inconclusiveKey` accordingly.

(Full `npm test` from `apps/web/` run after Phase 3: 25 files, 173 tests, all green.)

## Phase 4: Golden Regeneration and Integration

- [x] 4.1 GREEN: hand-recompute and update golden values (`risk_score`, `confidence_score`, `classification`, `ruleset_version` -> `2026-09-05`, `engine_version` -> `0.2.0`) in `tests/unit/test_assessment.py`. (Fixed `_results()` fixture to give OCR all 4 core fields so the pre-existing "clean successful analysis -> LOW_RISK" test isn't accidentally caught by the new OCR-zero floor — a fixture fix, not a golden-value change.)
- [x] 4.2 GREEN: same regeneration in `tests/unit/test_analyze_receipt.py`. (No literal-value changes needed — confirmed via full suite run; its stub ports don't set `evidence_observed` and don't assert `classification`, so unaffected.)
- [x] 4.3 GREEN: same regeneration in `tests/unit/test_api_schemas.py`. (No changes needed — confirmed green in full suite; its `engine_version="0.1.0"` literals are inputs to schema construction, not assertions against the real `ENGINE_VERSION` constant.)
- [x] 4.4 GREEN: same regeneration in `tests/unit/test_api_error_contract.py`. (No changes needed — confirmed green.)
- [x] 4.5 GREEN: same regeneration in `tests/unit/test_router.py`. (Updated `engine_version` assertion to `"0.2.0"`.)
- [x] 4.6 GREEN: same regeneration in `tests/unit/test_log_privacy.py`. (No changes needed — confirmed green.)
- [x] 4.7 GREEN: sweep remaining affected unit files touching `engine_version`/`ruleset_version`/completeness/score literals (`test_domain_signals.py`, `test_ports.py`, others surfaced by the full run) and regenerate. (Full `uv run pytest -q` run surfaced no further failures beyond `test_router.py` and `test_assessment.py`, both already fixed above.)
- [x] 4.8 RED->GREEN: `tests/integration/test_analyze_endpoint_e2e.py` — assert response carries `engine_version="0.2.0"`, `ruleset_version="2026-09-05"`, and floored scores end-to-end. (Repointed fixture app construction from `RULESET_2026_09_04` to `RULESET_2026_09_05`; added `engine_version` assertion.)
- [x] 4.9 Add fixture (e): re-run `v2026_09_01`/`v2026_09_04` against their own historical inputs in `test_ruleset.py`/`test_scoring.py`, assert byte-identical scores (unaffected by the new ruleset field). (Added to `test_scoring.py` as `test_v2026_09_01_and_v2026_09_04_reproducible_under_shared_engine_fix`.)
- [x] 4.10 Full suite: `uv run pytest -q` (API) and `npm test` (web, vitest run — CORRECTED from tasks.md's original `pnpm` reference, this repo uses npm only) both green. (API: all passed, 15 skipped for missing local binaries as expected. Web: 25 files / 173 tests passed.)

## Key Learnings

1. The design pins the shared-code `_completeness` fix as unconditional and retroactive, requiring an `ENGINE_VERSION` bump rather than a ruleset-scoped change.
2. Only the provenance role's C2PA adapter needed the new `evidence_observed` flag; vision and metadata adapters stay unchanged because their `status="completed"` already implies real evaluation occurred.
3. The new `combination_floors` field must be added to v2026_09_01 and v2026_09_04 as explicit empty mappings since `ScoringRuleset` is a frozen dataclass with no defaults.
4. Golden-value regeneration spans roughly 7-9 API unit test files plus integration tests and 4+ web unit test files, driving the estimated review size past the 400-line budget.
5. The active ruleset in `bootstrap/app.py` moves from `RULESET_2026_09_04` to the newly created `RULESET_2026_09_05`, keeping rollback to a one-line repoint.
