# Verification Report: visual-anomaly-detection

Change: visual-anomaly-detection
Mode: openspec (full artifact set: proposal/specs/design/tasks)
Verdict: PASS WITH WARNINGS

## Completeness
45/45 tasks in tasks.md marked [x]. Independently re-verified against actual source for every phase (domain, application, vision adapter, reference embeddings, model fetch/infra, bootstrap wiring, golden/contract updates, integration tests, docs/web copy). No task is checked-but-not-done.

## Independent Test Execution
apps/api (uv run pytest):
- Without RECEIPT_RISK_VISION_MODEL_DIR set: 151 passed, 12 skipped.
- With RECEIPT_RISK_VISION_MODEL_DIR=/tmp/vision-model (real model apply had already fetched into this sandbox): 159 passed, 4 skipped, 0 failed, exit 0. The 4 skips are unrelated: 2x exiftool not on PATH, 2x RECEIPT_RISK_OCR_MODEL_DIR unset -- pre-existing OCR/metadata sandbox gaps, not vision. Apply report claimed "159 passed, 2 skipped"; actual skip count in this sandbox is 4, not 2 (minor discrepancy, nature of skips correctly characterized, not CRITICAL).
- -k vision: 25/25 passed including all 8 real-model integration tests in test_vision_integration.py, run against the actually-fetched /tmp/vision-model/mobilenet_v3_small.pth checkpoint (torch 2.14.0+cpu / torchvision 0.29.0+cpu genuinely importable and used).
- ruff check .: All checks passed. ruff format --check .: 93 files already formatted.

apps/web (pnpm test / vitest run): 166/166 tests passed across 25 files, independently re-run. Matches apply report exactly.

## Verification of flagged apply-report claims
1. _ANALYZER_EVIDENCE_WEIGHTS sums to exactly Decimal("1.00") -- CONFIRMED. ocr=0.43, metadata=0.17, provenance=0.25, vision=0.15, sum=1.00 exactly.
2. Vision adapter fails closed before any torch/torchvision import -- CONFIRMED by direct source read of mobilenet_embedder.py. Env-var/weights-file check happens strictly before the import lines; VisionEngineUnavailable folds into AnalyzerResult(status="failed", error_code="ANALYZER_UNAVAILABLE"), never raising.
3. Zero-outbound-network guarantee -- CONFIRMED. No network-capable imports in adapters/vision/. Weights load only from local model_dir; reference embeddings load only from the committed local JSON artifact. Real-inference zero-network test passed.
4. sha256 in fetch_vision_model.py is a valid 64-hex-char digest -- CONFIRMED. 047dcff4addef86ea5bc2eff13c9614dc11f47ab1160d0a71a25e7db994f4e1f is exactly 64 hex chars; no typo/extra-character discrepancy found.
5. UI copy wording -- CONFIRMED exact required English/Spanish strings present. WARNING: no "Engine: PyTorch" string exists anywhere in apps/web/src -- the spec clause is conditional so this is not a violation, but it is unaddressed by the apply report. Vision findings correctly worded "outlier", never conflated with AI-generated phrasing.
6. _run_analyzers uses ONE anyio task group -- CONFIRMED. Single task group, 4 start_soon calls, vision-first is presentation-only result-list ordering.
7. No _CRITICAL_FLOOR entry for VISUAL_ANOMALY_DETECTED -- CONFIRMED.
8. Golden test regeneration (test_scoring.py, 0.50->0.42) is legitimate -- CONFIRMED. 0.17+0.25=0.42 exactly, consistent with the rebalance.
9. Determinism invariant preserved in samples/generate.py -- CONFIRMED. No random/time/datetime imports; --check reports "All fixtures match committed bytes."

## Spec Compliance Matrix

receipt-analysis:
- Visual outlier flagged: PASS
- Vision listed first in signal ordering: PASS
- No outbound network calls during visual inspection: PASS
- Missing vision weights degrade without failing analysis: PASS
- Deterministic score for identical input: PASS (pre-existing, unaffected)
- No absolute verdict: PASS
- Evidence weights sum to one across four roles: PASS
- Typical request meets p50 / slow request meets p95: UNVERIFIED -- no p50/p95 latency tests exist anywhere in the repo (pre-existing gap, not introduced by this change; task 8.3 correctly marked N/A)

public-api-contract:
- Ready endpoint reports four analyzers: PASS
- Version endpoint reports the vision analyzer: PASS
- Visual anomaly signal documented in the schema: PASS

receipt-analysis-web-client:
- Idle state renders the pipeline explainer including vision: PASS
- Pipeline explainer never overstates system capability: PASS
- Visual anomaly finding worded as outlier, never AI claim: PASS
- No forbidden authenticity language appears: PASS
- "Engine: PyTorch" label wording (conditional clause): WARNING -- no engine-label UI element exists yet anywhere; clause technically unviolated (conditional) but unaddressed by apply report

## Design Coherence
All design.md decisions match the implementation exactly. File Changes table matches the actual diff footprint.

## Issues

CRITICAL: None found.

WARNING:
1. Apply report skip-count precision (claimed 2, actual 4 in this sandbox; both unrelated to vision).
2. Conditional "Engine: PyTorch" UI-copy clause has no corresponding element anywhere; not a violation, but unaddressed.
3. No p50/p95 latency test exists in the repo (pre-existing gap); MODIFIED "Analysis latency budget" requirement lacks direct automated runtime proof.

SUGGESTION:
1. Add a lightweight p50/p95 latency smoke test in a follow-up change now that four concurrent analyzers exist.

## Overall Verdict
PASS WITH WARNINGS -- every CRITICAL-tier claim from the apply report was independently verified as true and accurate. All 45 tasks are genuinely complete. Both test suites pass under independent re-execution (159/159 non-skipped api tests, 166/166 web tests). Remaining gaps are pre-existing or minor/cosmetic -- none block archive.
