# Tasks: Visual Anomaly Detection (PyTorch)

> Note: exceeds the default 530-word artifact budget. This change touches domain,
> application, a new adapter, scripts, Docker/CI, samples, docs, and web copy —
> compressing that into 530 words would drop required RED/GREEN traceability.

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | ~1150-1350 (authored; excludes generated `reference_embeddings_v1.json` bytes and `uv.lock`) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes (but delivery strategy is fixed to single-pr this session) |
| Suggested split | Single PR, `size:exception` required — even the session's elevated 800-line budget is likely exceeded |
| Delivery strategy | single-pr (session-confirmed, 800-line budget) |
| Chain strategy | size-exception |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: size-exception
400-line budget risk: High

Rationale: new adapter package (~250-300 lines), `fetch_vision_model.py` +
`build_reference_embeddings.py` (~180), 3 new `samples/generate.py` templates +
manifest updates (~180), unit + integration tests (~330), domain/scoring/app
wiring (~125), infra (pyproject/Dockerfile/ci.yml, ~45), docs/i18n/web copy
(~100). Sum comfortably exceeds even the session's 800-line elevated budget.
Flagging honestly rather than under-forecasting; orchestrator must confirm
`size:exception` before `sdd-apply`, or ask the user to reconsider chaining.

### Suggested Work Units (if chaining is later approved)

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|---|---|---|---|---|---|
| 1 | Domain + application wiring (Phases 1-2) | PR 1 | `uv run pytest -k "signals or ruleset or scoring or analyze_receipt"` | N/A — pure domain/application, no real model | Revert `domain/{signals,rulesets/v2026_09_01,scoring}.py`, `application/{ports,analyze_receipt}.py` |
| 2 | Vision adapter + reference data + infra (Phases 3-6) | PR 2 (base: PR 1) | `uv run pytest -k vision` | Real MobileNetV3 against committed fixtures, CI-required | Delete `adapters/vision/`, `scripts/{fetch_vision_model,build_reference_embeddings}.py`, revert `Dockerfile`/`ci.yml`/`pyproject.toml` vision hunks |
| 3 | Golden/contract updates + docs/UI (Phases 7-9) | PR 3 (base: PR 2) | `uv run pytest -k "contract or golden"`; `pnpm --filter web test` | `TestClient` full-fixture run; web component tests | Regenerate goldens against pre-vision weights; revert docs/i18n files |

## Phase 1: Domain foundation

- [x] 1.1 RED: `tests/unit/test_domain_signals.py::test_visual_category_and_visual_anomaly_code_exist`
- [x] 1.2 GREEN: `domain/signals.py` — add `SignalCategory.VISUAL`, `SignalCode.VISUAL_ANOMALY_DETECTED`
- [x] 1.3 RED: `domain/rulesets/v2026_09_01.py::test_evidence_weights_sum_to_one_across_four_roles` (spec: Evidence weights sum to one)
- [x] 1.4 RED: `test_visual_anomaly_detected_weight_20_no_critical_floor_entry`
- [x] 1.5 GREEN: rebalance `_ANALYZER_EVIDENCE_WEIGHTS` (ocr 0.43/metadata 0.17/provenance 0.25/vision 0.15), add `_WEIGHTS[VISUAL_ANOMALY_DETECTED]=20`, severity multiplier entries, no `_CRITICAL_FLOOR` entry
- [x] 1.6 RED: `domain/scoring.py::test_adapter_role_maps_mobilenetv3_embedding_to_vision`
- [x] 1.7 GREEN: `domain/scoring.py` — `_ADAPTER_ROLE["mobilenetv3-embedding"] = "vision"`

## Phase 2: Application wiring

- [x] 2.1 RED: `application/ports.py::test_vision_port_protocol_shape`
- [x] 2.2 GREEN: add `VisionPort` Protocol (`inspect(image) -> AnalyzerResult`, never raises)
- [x] 2.3 RED: `application/analyze_receipt.py::test_four_analyzers_run_in_one_task_group_vision_first_in_results` (spec: Vision listed first in signal ordering)
- [x] 2.4 RED: `test_missing_vision_weights_degrades_without_failing_analysis_200_weight_zero` (spec: Missing vision weights degrade)
- [x] 2.5 GREEN: extend `AnalyzeReceiptUseCase` — `vision` ctor arg, `TimeBudget.vision_s=3.0`, 4th `start_soon` in the same task group, vision-first result ordering

## Phase 3: Vision adapter

- [x] 3.1 Create `adapters/vision/__init__.py` package marker
- [x] 3.2 RED: `adapters/vision/preprocess.py::test_preprocessing_deterministic_same_bytes_identical_tensor_hash`
- [x] 3.3 GREEN: implement `preprocess.py` (PIL open → RGB → resize 256 → center-crop 224 → ImageNet normalise)
- [x] 3.4 RED (threat, model loading): `test_unset_model_dir_env_var_returns_analyzer_unavailable_zero_network`
- [x] 3.5 RED: `test_distance_to_severity_mapping_at_each_threshold_boundary` (d≥0.45 MEDIUM/0.70; 0.30≤d<0.45 LOW/0.50; else no signal), injected fake `embed` + synthetic reference matrix
- [x] 3.6 RED (threat, untrusted input): `test_adapter_only_accepts_validated_safeimageref_path_never_client_supplied`
- [x] 3.7 GREEN: implement `mobilenet_embedder.py::MobileNetV3VisionAdapter` mirroring `paddle_onnx.py` (env-var model dir, fail-closed before model construction, injectable `embed`/`reference_embeddings`, `anyio.to_thread.run_sync`, threshold constants + rationale docstring)
- [x] 3.8 RED: `test_visual_outlier_signal_shape_matches_design_evidence_fields` (cosine_distance/threshold/reference_set_version/reference_set_size)
- [x] 3.9 GREEN: implement pure `_derive_signal()` function (mirrors `c2pa_reader._derive_signals`)

## Phase 4: Reference embeddings & samples

- [x] 4.1 Extend `samples/generate.py` with 3 deterministic templates (second bank identity, compact layout, dark-header/boxed-rows), no RNG, byte-identical reruns
- [x] 4.2 Update `samples/manifest.json` — add `vision` to `expected_analyzer_statuses`
- [x] 4.3 Create `apps/api/scripts/build_reference_embeddings.py` (renders/reads `samples/images/**` → writes `reference_embeddings_v1.json`; `--check` drift mode)
- [x] 4.4 Generate and commit `adapters/vision/reference_embeddings_v1.json` (`schema_version, model, embedding_dim, source_fixtures, embeddings[]`)

## Phase 5: Model fetch & infra

- [x] 5.1 Create `apps/api/scripts/fetch_vision_model.py` — pinned `mobilenet_v3_small-047dcff4.pth` URL, hand-verified sha256 (compute and verify at apply time, never fabricate), `--dest`/`--verify`
- [x] 5.2 Modify `apps/api/pyproject.toml` — add `torch`/`torchvision` CPU-only wheel deps, resolve CPU-wheel index strategy against `uv.lock`, ban `torch`/`torchvision` outside `adapters/vision/**` (`TID251`), add `"scripts/**" = ["TID251"]` per-file-ignore
- [x] 5.3 Modify `apps/api/Dockerfile` — new `vision-model` build stage, `COPY --from`, `ENV RECEIPT_RISK_VISION_MODEL_DIR=/opt/vision-model`
- [x] 5.4 Modify `.github/workflows/ci.yml` — independent cache step keyed on `fetch_vision_model.py` (separate from OCR's key), fetch step, `RECEIPT_RISK_VISION_MODEL_DIR` in test env

## Phase 6: Bootstrap wiring

- [x] 6.1 RED: `bootstrap/app.py::test_ready_endpoint_reports_four_analyzers_including_vision` (spec: Ready endpoint reports four analyzers)
- [x] 6.2 RED: `test_version_endpoint_includes_vision_analyzer_entry` (spec: Version endpoint reports the vision analyzer)
- [x] 6.3 GREEN: wire `MobileNetV3VisionAdapter` as `_vision`, add to `/ready` and `/version` analyzer maps

## Phase 7: Golden/contract updates

- [x] 7.1 RED: `test_analyze_response_signal_schema_includes_visual_anomaly_detected_and_visual_category` (spec: Visual anomaly signal on the wire)
- [x] 7.2 Regenerate/update every hardcoded `confidence_score` expectation across contract/golden tests to reflect the rebalanced weights (design risk: this is a de facto behavior change for every existing request)
- [x] 7.3 RED: `test_response_never_contains_ai_generated_wording_for_visual_anomaly_detected` (spec: outlier wording, never "AI-generated")

## Phase 8: Integration tests

- [x] 8.1 Create `apps/api/tests/integration/test_vision_integration.py` — real MobileNetV3 on committed fixtures, `skipif(not os.environ.get("RECEIPT_RISK_VISION_MODEL_DIR"))`, assert every reference fixture scores `d<0.30` and an off-domain/corrupted image scores higher
- [x] 8.2 Extend the existing "zero outbound network during analysis" e2e test to cover the vision adapter in the graph (spec: No outbound network calls during visual inspection)
- [x] 8.3 Confirm existing p50/p95 latency tests still pass with four concurrent analyzers (spec: Analysis latency budget)

## Phase 9: Docs & web copy

- [x] 9.1 Update `docs/API.md` — `/ready`/`/version` examples add `"vision": "mobilenetv3-embedding/1.0.0"`; signal/threat-matrix table adds `VISUAL_ANOMALY_DETECTED` (category `visual`, LOW/MEDIUM)
- [x] 9.2 Update `README.md` — stack table Vision row; Mermaid flow diagram fourth parallel analyzer node
- [x] 9.3 Update `apps/web/src/lib/i18n/messages/{en,es}.json` — `docsPage.stack.visionLabel/visionValue`, rewritten `docsPage.architecture.flow.analyzers`
- [x] 9.4 Update `apps/web/src/routes/docs/+page.svelte` — append `'vision'` to `STACK_ROWS`
- [x] 9.5 RED: web idle-state test asserting the pipeline explainer lists the PyTorch step (both locales) and never uses "real"/"fake"/"authentic"/"verified transfer" (spec: Idle state renders the pipeline explainer including vision)
- [x] 9.6 RED: web result-state test asserting `VISUAL_ANOMALY_DETECTED` renders as an outlier finding, never "AI-generated" wording (spec: Visual anomaly finding worded as outlier)
- [x] 9.7 GREEN: update `ResultView.svelte`/`ProcessingStages.svelte`/idle-state component per 9.5-9.6 if a vision-analyzer entry or explainer step is missing

## Key Learnings

1. Weight rebalancing changes `confidence_score` for every existing request, so Phase 7's golden-test regeneration must land in the same PR as the ruleset change, never split across chained PRs.
2. `_run_analyzers` stays a single `anyio` task group; "vision runs first" is delivered only through output-list ordering, not scheduling priority.
3. The vision adapter must fail closed before any `torch`/`torchvision` import when `RECEIPT_RISK_VISION_MODEL_DIR` is unset, mirroring `paddle_onnx.py`'s existing pattern exactly.
4. The pinned sha256 for the MobileNetV3 weights must be hand-computed at apply time; `fetch_vision_model.py` must never ship a fabricated hash.
5. This change's authored line estimate (~1150-1350) likely exceeds even the session's elevated 800-line single-PR budget, so `size:exception` approval is a hard precondition before `sdd-apply` starts Phase 3 onward.
