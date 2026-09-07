# Proposal: Visual Anomaly Detection (PyTorch)

## Intent

The pipeline reasons only about text (OCR), metadata and C2PA. A tampered or fully re-rendered receipt whose text and EXIF look clean produces no signal today. Add a fourth analyzer that inspects the **pixels**: a frozen ImageNet MobileNetV3 embedding compared by cosine distance against a bundled reference set of legitimate receipt renders, flagging visual outliers. This is one-class novelty detection, not a fraud classifier — no labeled fraud data exists.

## Scope

### In Scope

- `VisionPort` + `adapters/vision/` MobileNetV3 embedding adapter (torchvision, frozen, **PyTorch at runtime**), fail-closed on missing weights per `adapters/ocr/paddle_onnx.py`.
- New `SignalCategory.VISUAL` + `SignalCode.VISUAL_ANOMALY_DETECTED`, LOW/MEDIUM severity, **no `_CRITICAL_FLOOR` entry**.
- `vision` role at ~0.15 in `_ANALYZER_EVIDENCE_WEIGHTS`; ocr/metadata/provenance rebalanced proportionally so the total stays exactly **1.00** (`confidence_score` invariant).
- Build-time pinned + sha256-verified weight fetch (script + Dockerfile stage + CI cache), mirroring `fetch_ocr_models.py`. **Zero runtime network calls.**
- Versioned, regeneratable reference-embedding artifact; `samples/generate.py` expanded with additional synthetic receipt templates.
- `ANALYZER_UNAVAILABLE` degradation identical to existing analyzers (info, weight 0, 0 evidence coverage).
- Copy updates: web i18n (`en`/`es`), `docs/API.md`, `README.md` — wording is "visual outlier", never "AI-generated".

### Out of Scope

- Trained fraud classifier, labeled data, human feedback loop, database.
- **True short-circuit scheduling.** `_run_analyzers` runs all analyzers concurrently in one task group; "vision runs early" is delivered as **signal-list ordering only** (vision listed first). Real two-phase scheduling is deferred.
- ONNX export, engine selector, fine-tuning, threshold benchmarking.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `receipt-analysis`: new visual-inspection requirement; scoring/evidence-weight and latency-budget requirements updated for a 4th analyzer.
- `public-api-contract`: `/ready` and `/version` analyzer maps gain `vision`; new signal code/category on the wire.
- `receipt-analysis-web-client`: docs copy for the PyTorch vision analyzer.

## Approach

Cosine-distance one-class detector. Reference embeddings are precomputed offline into a committed, regeneratable artifact (no startup inference, no magic numbers in code). Adapter takes an injectable engine so unit tests never load weights; one skipif-guarded integration test exercises real inference against CI-cached weights. Thresholds are documented as reasoned defaults, not benchmarked.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `domain/signals.py` | Modified | `VISUAL` category, `VISUAL_ANOMALY_DETECTED` code |
| `domain/rulesets/v2026_09_01.py` | Modified | Signal weight; evidence-weight rebalance to 1.00 |
| `domain/scoring.py` | Modified | `_ADAPTER_ROLE` → `vision` |
| `application/ports.py` | Modified | `VisionPort` |
| `application/analyze_receipt.py` | Modified | 4th task, `TimeBudget.vision_s`, ordering |
| `adapters/vision/` | New | MobileNetV3 embedding adapter |
| `scripts/fetch_vision_model.py` | New | Pinned + sha256 weights |
| `Dockerfile`, `.github/workflows/ci.yml` | Modified | Build stage + CI cache |
| `bootstrap/app.py` | Modified | Wiring, `/ready`, `/version` |
| `pyproject.toml` | Modified | `torch`/`torchvision` deps + TID251 ban |
| `samples/` | Modified | Template diversity + reference embeddings |
| `tests/unit`, `tests/integration` | New | Fake-engine unit, guarded real test |
| web i18n, `docs/API.md`, `README.md` | Modified | Analyzer roster copy |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Thin reference set → false positives on legitimate unseen layouts | High | Expand `samples/` templates; LOW/MEDIUM weight caps blast radius; document limitation |
| Evidence-weight rebalance shifts `confidence_score` for all requests | High | De facto ruleset change; assert sum == 1.00; update golden expectations |
| `torch` inflates image size / cold start (Railway) | High | CPU-only wheels, multi-stage build; measure before merge |
| Unbenchmarked threshold | Med | Document as reasoned default, per existing ruleset docstring precedent |
| `_run_analyzers` hardcodes 3 tasks | Med | Structural edit covered in design |

## Rollback Plan

Single revert. The adapter is additive behind a port: dropping `RECEIPT_RISK_VISION_MODEL_DIR` degrades to `ANALYZER_UNAVAILABLE` without failing analysis, so a config-only kill is available before a code revert. Restoring the previous `_ANALYZER_EVIDENCE_WEIGHTS` triple restores prior `confidence_score` values exactly.

## Dependencies

- `torch` / `torchvision` (CPU wheels), pinned MobileNetV3 checkpoint URL + sha256.

## Success Criteria

- [ ] Visual outlier produces a LOW/MEDIUM `VISUAL_ANOMALY_DETECTED` signal; never a critical verdict.
- [ ] `_ANALYZER_EVIDENCE_WEIGHTS` sums to exactly 1.00 with 4 roles (asserted in tests).
- [ ] Missing weights → `ANALYZER_UNAVAILABLE`, analysis still returns 200.
- [ ] Zero outbound network connections during analysis (existing threat-matrix test passes).
- [ ] `/ready` and `/version` report a `vision` analyzer; UI/docs state "Engine: PyTorch".
