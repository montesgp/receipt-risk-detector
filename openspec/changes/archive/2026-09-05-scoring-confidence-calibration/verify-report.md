# Verify Report: scoring-confidence-calibration

**Mode**: full artifacts (proposal/spec/design/tasks all present) | **Verdict**: **PASS**

## Test Execution Evidence

| Command | Exit | Result |
|---|---|---|
| uv run pytest -q (apps/api/) | 0 | 216 tests, 0 failures, 0 errors, 14 skipped (missing local binaries: exiftool/c2pa/PaddleOCR real fixtures -- expected in this sandbox) |
| npm test (apps/web/, vitest run) | 0 | 25 files / 173 tests, all passed |
| Standalone end-to-end repro script (AnalyzeReceiptUseCase.execute() with injected fakes, zero-text OCR + no-manifest provenance) | n/a | classification: INCONCLUSIVE, confirmed twice (coverage 0.32 and, separately, coverage 0.57 with a manifest present to isolate the NEW floor from the pre-existing coverage gate) |

No pnpm was used anywhere.

## Task Completeness

All 34 tasks across 4 phases in tasks.md are marked [x]. Spot-checked against actual code/tests -- all claims verified true (see below), no stale checkmarks found.

## Spec Compliance Matrix (receipt-analysis)

| Scenario | Status | Evidence |
|---|---|---|
| evidence_coverage distinguishes completed vs informative for provenance | PASS | scoring.py::_completeness -- result.evidence_observed is False returns Decimal("0"); test_completeness_provenance_evidence_observed_false_returns_zero |
| vision/metadata completeness unchanged at 1.0 | PASS | test_completeness_vision_and_metadata_unchanged_at_one_when_completed |
| OCR-zero + no strong signal forces INCONCLUSIVE | PASS | test_ocr_zero_core_fields_forces_inconclusive_even_above_coverage_threshold, test_ocr_zero_floor_fires_even_when_coverage_is_above_threshold (isolates the new floor from the pre-existing coverage gate at coverage=0.57) |
| Legitimate low-quality receipt (partial OCR, no C2PA) NOT forced INCONCLUSIVE | PASS | test_legitimate_low_quality_receipt_partial_ocr_no_c2pa_not_forced_inconclusive -- 1/4 core fields (realistic partial extraction, not contrived), coverage 0.43, classification unaffected |
| Combination floor: both codes co-occur then floors at 55 | PASS | test_combination_floor_fires_only_when_both_signals_co_occur |
| Neither signal alone triggers the combination floor | PASS | same test, extraction_only/date_only assertions below 55 |
| Prior ruleset versions (v2026_09_01/04) byte-identical, combination_floors empty is a no-op | PASS | same test's both_old_ruleset assertion; test_v2026_09_01_and_v2026_09_04_reproducible_under_shared_engine_fix; test_ruleset_declares_combination_floors_field_empty_on_historical_versions |
| Verdict-grade CRITICAL signal overrides OCR-zero floor | PASS | test_ocr_zero_with_valid_ai_generated_claim_stays_high_risk_not_downgraded |
| Failed/timed-out OCR never triggers the new floor | PASS | _ocr_core_fields_empty explicitly returns False when status not in completed/partial; regression test test_confidence_independent_of_risk_ocr_fails_others_succeed_not_inconclusive still green |
| No new Classification/SignalCode/schema change | PASS | confirmed via ruleset.py, signals.py diff -- no additions |

## Spec Compliance Matrix (receipt-analysis-web-client)

| Scenario | Status | Evidence |
|---|---|---|
| INCONCLUSIVE plus no_text_detected reason selects hedged copy | PASS | ScoreSummary.svelte inconclusiveKey derivation; ScoreSummary.test.ts 3 dedicated cases (hedged/generic/neither) |
| Hedged wording, no absolute verdict | PASS | en/es strings read directly: "we could not identify..." / "no pudimos identificar..." -- no "is not a transfer" language |
| noTextDetected derived correctly in ResultView | PASS | ResultView.svelte derivation matches design exactly (code equals CORE_FIELD_EXTRACTION_FAILED and evidence.reason equals no_text_detected); ResultView.test.ts |
| es/en key parity | PASS | key-parity.test.ts (4 tests) green; both files carry result.inconclusiveNoTextNote at the same location |
| No forbidden authenticity language in new/changed copy | PASS | literal-audit.test.ts (24 tests) green; manual grep of new strings clean |

## Ten Targeted Apply-Report Claims -- Independent Re-Verification

1. Original bug fixed (zero-text image via live pipeline yields INCONCLUSIVE, not LOW_RISK) -- CONFIRMED independently via a standalone script driving the real AnalyzeReceiptUseCase.execute() (not just score()) with injected fake ports simulating a completed-but-empty OCR result and a no-manifest C2PA result. Result: INCONCLUSIVE, risk_score 0. Repeated with evidence_observed True (coverage 0.57, above the 0.35 threshold) to isolate the NEW floor mechanism from the pre-existing coverage gate -- still INCONCLUSIVE. Confirms the fix operates end-to-end, not merely at the unit-test layer.
2. Legitimate low-quality receipt (0.32-adjacent, nonzero OCR) not forced INCONCLUSIVE -- CONFIRMED: the actual test (test_legitimate_low_quality_receipt_partial_ocr_no_c2pa_not_forced_inconclusive) uses 1/4 core fields genuinely extracted (amount), a realistic partial-extraction scenario, not a contrived one, coverage 0.43, classification unaffected.
3. Combination floor requires BOTH codes co-occurring -- CONFIRMED by reading _risk_score's subset check (codes subset-of fired, where fired is the frozenset of ALL fired codes -- only true when every code in the floor's key is present) and the dedicated test proving each code alone stays below 55.
4. _completeness fix is unconditional/retroactive -- CONFIRMED: no version branching anywhere in scoring.py; test_v2026_09_01_and_v2026_09_04_reproducible_under_shared_engine_fix runs the OLD ruleset objects through the same fixed _completeness code path.
5. _ocr_core_fields_empty scoped to completed/partial only -- CONFIRMED by direct source read (returns False when status is not completed and not partial) and test_confidence_independent_of_risk_ocr_fails_others_succeed_not_inconclusive passing (OCR status failed, other analyzers succeed, classification stays non-INCONCLUSIVE).
6. ENGINE_VERSION equals 0.2.0 -- CONFIRMED in application/analyze_receipt.py; docs/API.md examples updated to 0.2.0 / 2026-09-05 at both cited example blocks; test_router.py asserts engine_version equals 0.2.0 end-to-end via the real router.
7. bootstrap/app.py wired to v2026_09_05 -- CONFIRMED: imports RULESET_2026_09_05 from domain.rulesets.v2026_09_05, uses it at use-case construction and /version; no stale RULESET_2026_09_04 reference remains as active. test_version_endpoint_reports_active_ruleset_2026_09_05 passes.
8. Web copy key parity plus hedged wording plus correct branch condition -- CONFIRMED: keys present in both en.json and es.json, wording hedged, ResultView.svelte's noTextDetected derivation checks exactly the CORE_FIELD_EXTRACTION_FAILED code with the no_text_detected reason, matching design.
9. No absolute-verdict language in new/changed copy -- CONFIRMED via targeted grep of the two new i18n strings and signals.py; the one "authenticity" hit found (docsPage.product.principle) is pre-existing unrelated documentation copy, not part of this change's new strings.
10. No scope creep into visual-anomaly-detection (PR 29) or generic-receipt-field-extraction (PR 31) -- CONFIRMED via git status and git diff stat: 26 changed files (25 modified plus 1 new v2026_09_05.py), exactly matching design.md's File Changes table. mobilenet_embedder.py and field_parsers.py are untouched.

## Issues

None found. No CRITICAL, no WARNING, no SUGGESTION.

## Final Verdict: PASS

All tasks complete and verified against real code and passing tests. Both original-bug reconstruction and the regression-guard case for legitimate low-quality receipts were independently re-derived and pass. The change is ready for sdd-archive and PR opening (already flagged in tasks.md as exceeding the 400-line single-PR budget -- user accepted the size exception per the tasks.md forecast; actual diff came in at 484 insertions and 27 deletions across 26 files, consistent with that forecast).
