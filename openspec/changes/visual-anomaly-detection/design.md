# Design: Visual Anomaly Detection (PyTorch)

## Technical Approach

A fourth analyzer role, `vision`, behind a new `VisionPort`. `MobileNetV3VisionAdapter` embeds the receipt with a frozen ImageNet MobileNetV3-Small, compares it by nearest-neighbour cosine distance against a committed reference-embedding artifact, and emits at most one `VISUAL_ANOMALY_DETECTED` signal (LOW or MEDIUM). It copies `adapters/ocr/paddle_onnx.py` exactly: env-var model dir, fail-closed *before* any model construction, constructor-injectable engine as the test seam, `status="failed"` / `error_code="ANALYZER_UNAVAILABLE"`, blocking work in `anyio.to_thread.run_sync`, zero runtime network. Signal derivation is a pure function like `c2pa_reader._derive_signals`.

Confirmed non-goal: `_run_analyzers` stays one concurrent `anyio` task group. "Vision runs early" is delivered only by listing `vision` first in the returned results list (and therefore first in the chained signal list).

## Architecture Decisions

| Decision | Choice | Rejected | Rationale |
|---|---|---|---|
| Backbone | `torchvision.models.mobilenet_v3_small`, `weights=None` + local `state_dict` | `mobilenet_v3_large` | ~2.5M params / ~10 MB vs ~21M / ~87 MB. Cold-start and image size are High risks on Railway; for one-class cosine distance over near-duplicate document renders the extra capacity buys nothing measurable, and nothing here is benchmarked anyway. |
| Embedding | `model.features` → `AdaptiveAvgPool2d(1)` → flatten → L2-normalise = **576-d** | Penultimate 1024-d classifier layer; raw logits | The classifier head is ImageNet-class-specific and irrelevant to "receipt-ness". Pooled conv features are the standard generic descriptor. Skipping the head also lets us drop the classifier weights. |
| Distance | `d = 1 - max_j cos(e, r_j)` over the reference set (nearest neighbour) | Mean/centroid distance; Mahalanobis | Reference set is intentionally multi-modal (several templates); a centroid would sit between modes and flag every legitimate template. Max-similarity is the correct one-class rule for a small heterogeneous set. |
| Thresholds | `d ≥ 0.45` → MEDIUM (confidence `0.70`); `0.30 ≤ d < 0.45` → LOW (confidence `0.50`); `d < 0.30` → no signal | Percentile calibration on held-out data | No labelled data exists. Documented as reasoned defaults in the module docstring, mirroring `_ALGORITHMIC_SOURCE_MARKERS` and the ruleset docstring ("reasonable defaults, not fake precision"). |
| Reference embeddings | Precomputed offline into a committed, versioned JSON artifact | Compute at adapter startup from `samples/` | Startup inference costs cold-start seconds, requires `samples/` in the runtime image, and makes results depend on load order. A committed artifact is reviewable, deterministic, regeneratable by script, and contains no magic numbers in code. |
| Weight distribution | New sibling script `scripts/fetch_vision_model.py`, pinned URL + sha256, new `vision-model` Dockerfile stage, new CI cache step | Extending `fetch_ocr_models.py`; `torchvision`'s own downloader | Separate cache key so an OCR pin bump does not invalidate the vision cache (and vice versa). `torchvision`'s downloader would be a runtime network call. |
| Critical floor | **No** `_CRITICAL_FLOOR` entry | Floor like `VALID_AI_GENERATED_CLAIM` | A pixel-space outlier is weak, unbenchmarked evidence. It must be able to raise a score, never to force a verdict — same posture as `PROVENANCE_VALIDATION_FAILED`. |

### Evidence-weight rebalance (exact numbers)

Scale the existing triple by `0.85` and round to 2 dp so the sum is exactly `1.00`:

| Role | Before | Scaled ×0.85 | **After** |
|---|---|---|---|
| ocr | 0.50 | 0.425 | **0.43** |
| metadata | 0.20 | 0.170 | **0.17** |
| provenance | 0.30 | 0.255 | **0.25** |
| vision | — | — | **0.15** |
| **sum** | 1.00 | 0.85 | **1.00** |

Rounding tie-break: `ocr` rounds up and `provenance` rounds down because `ocr` is the only role with fractional `_completeness`, so it is the role whose coverage most often lands below its full weight. This is a de facto ruleset change: every `confidence_score` shifts. A test must assert `sum(...) == Decimal("1.00")`.

## Data Flow

    SafeImageRef ─┬─→ ocr        ┐
                  ├─→ metadata   ├─ one anyio task group (unchanged)
                  ├─→ provenance │
                  └─→ vision ────┘
                        │
        PIL open → RGB → resize 256 → center-crop 224 → ImageNet normalise
                        │
        mobilenet_v3_small.features → avgpool → flatten → L2-norm (576-d)
                        │
        max cosine sim vs reference_embeddings_v1.json → d = 1 - sim
                        │
        threshold → 0..1 VISUAL_ANOMALY_DETECTED signal
                        │
    results = [vision, ocr, metadata, provenance] → assemble() → scoring

## File Changes

| File | Action | Description |
|---|---|---|
| `apps/api/src/receipt_risk/adapters/vision/__init__.py` | Create | Package marker |
| `.../adapters/vision/mobilenet_embedder.py` | Create | `MobileNetV3VisionAdapter`, `VisionEngineUnavailable`, `_model_dir_from_env`, `_load_embedder`, threshold constants + rationale docstring |
| `.../adapters/vision/preprocess.py` | Create | Deterministic PIL→tensor pipeline (resize/crop/normalise), no cv2 |
| `.../adapters/vision/reference_embeddings_v1.json` | Create | Versioned artifact: `{schema_version, model, embedding_dim, source_fixtures, embeddings[[...576 floats]]}` |
| `.../application/ports.py` | Modify | `VisionPort` protocol |
| `.../application/analyze_receipt.py` | Modify | `vision` ctor arg, `TimeBudget.vision_s = 3.0`, 4th `start_soon`, vision-first result order, `_guarded` `inspect` path (no change needed — vision uses `inspect`) |
| `.../domain/signals.py` | Modify | `SignalCategory.VISUAL = "visual"`, `SignalCode.VISUAL_ANOMALY_DETECTED` |
| `.../domain/rulesets/v2026_09_01.py` | Modify | `_WEIGHTS[VISUAL_ANOMALY_DETECTED] = 20`; rebalanced `_ANALYZER_EVIDENCE_WEIGHTS`; **no** `_CRITICAL_FLOOR` entry |
| `.../domain/scoring.py` | Modify | `_ADAPTER_ROLE["mobilenetv3-embedding"] = "vision"` |
| `.../bootstrap/app.py` | Modify | Wire `_vision`, add to `/ready` + `/version` analyzer maps |
| `apps/api/scripts/fetch_vision_model.py` | Create | Pinned URL + sha256 → `mobilenet_v3_small.pth` |
| `apps/api/scripts/build_reference_embeddings.py` | Create | Renders/reads `samples/images/**` → writes the JSON artifact; `--check` mode for drift |
| `apps/api/pyproject.toml` | Modify | `torch`/`torchvision` CPU deps; ban `torch`/`torchvision` in `banned-api`; add `"scripts/**" = ["TID251"]` per-file-ignore |
| `apps/api/Dockerfile` | Modify | `vision-model` stage; `COPY --from`; `ENV RECEIPT_RISK_VISION_MODEL_DIR=/opt/vision-model` |
| `.github/workflows/ci.yml` | Modify | Cache + fetch steps keyed on `fetch_vision_model.py`; `RECEIPT_RISK_VISION_MODEL_DIR` in the test env |
| `samples/generate.py`, `samples/manifest.json` | Modify | Template diversity + `vision` in `expected_analyzer_statuses` |
| `apps/api/tests/unit/test_vision_mobilenet.py` | Create | Fake-engine unit tests |
| `apps/api/tests/integration/test_vision_integration.py` | Create | `skipif`-guarded real inference |
| `docs/API.md`, `README.md`, `apps/web/.../{en,es}.json`, `apps/web/src/routes/docs/+page.svelte` | Modify | Analyzer roster, threat matrix, stack table, flow copy |

## Interfaces / Contracts

```python
# application/ports.py
@runtime_checkable
class VisionPort(Protocol):
    """Pixel-space visual outlier inspection. `inspect` never raises: missing
    weights, an undecodable image, or a missing reference artifact all fold
    into AnalyzerResult(status="failed", error_code="ANALYZER_UNAVAILABLE")."""
    name: str
    version: str
    async def inspect(self, image: SafeImageRef) -> AnalyzerResult: ...

# adapters/vision/mobilenet_embedder.py
EmbedCallable = Callable[[Path], "np.ndarray"]  # -> (576,) L2-normalised float32

class MobileNetV3VisionAdapter:
    name = "mobilenetv3-embedding"
    version = "1.0.0"
    def __init__(self, *, model_dir: Path | None = None,
                 embed: EmbedCallable | None = None,
                 reference_embeddings: "np.ndarray | None" = None) -> None: ...
```

Signal emitted (evidence values are strings, per `ValidationSignal`):

```python
ValidationSignal(
    code=SignalCode.VISUAL_ANOMALY_DETECTED,
    category=SignalCategory.VISUAL,
    severity=Severity.MEDIUM,               # or LOW
    confidence=Decimal("0.70"),             # or Decimal("0.50")
    description=("This receipt's visual appearance is an outlier relative to the "
                 "bundled set of known-legitimate receipt renders."),
    evidence={"cosine_distance": "0.52", "threshold": "0.45",
              "reference_set_version": "v1", "reference_set_size": "12"},
)
```

Wording rule: "visual outlier" / "unusual visual appearance" — never "AI-generated", never "fake".

## Reference set construction

`samples/generate.py` gains **three** additional deterministic templates (no RNG, byte-identical reruns, per its existing invariant): a second bank identity (different institution string, header band colour, right-aligned value column), a compact layout (smaller canvas, tighter rows, different font sizes), and a dark-header/boxed-rows layout. Each renders clean plus one degraded variant, giving ~10-12 reference images spanning template, layout, and degradation axes. `build_reference_embeddings.py` embeds each and writes `reference_embeddings_v1.json`; the adapter loads it once at construction (pure JSON read, no torch). Bumping the set means a new `_v2` file and a `version` bump — old artifacts are never mutated in place.

## Testing Strategy

| Layer | What | How |
|---|---|---|
| Unit | Distance→severity mapping at each threshold boundary; no signal when near a reference; injected `embed` + synthetic reference matrix | Injected fake `EmbedCallable`, never loads weights (mirrors `test_ocr_paddle_onnx.py`) |
| Unit | Missing/unset `RECEIPT_RISK_VISION_MODEL_DIR` → `status="failed"`, `ANALYZER_UNAVAILABLE`, no download attempted | `monkeypatch.delenv`, assert before-construction failure |
| Unit | `sum(_ANALYZER_EVIDENCE_WEIGHTS.values()) == Decimal("1.00")`; `VISUAL_ANOMALY_DETECTED not in _CRITICAL_FLOOR` | Direct ruleset assertion |
| Unit | `_ADAPTER_ROLE` maps the adapter name; vision `completed` contributes exactly `0.15` coverage | `domain/scoring.py` test |
| Unit | Preprocessing determinism (same bytes → identical tensor hash) | Fixture image |
| Integration | Real MobileNetV3 on committed fixtures: every reference fixture scores `d < 0.30`, `corrupted`/off-domain image scores higher | `pytest.mark.skipif(not os.environ.get("RECEIPT_RISK_VISION_MODEL_DIR"))` (mirrors `test_ocr_integration.py`) |
| Integration | `/ready` and `/version` include `vision` | Existing TestClient contract tests |
| E2E | Existing "zero outbound network during analysis" threat-matrix test still passes | Unchanged test, new adapter in the graph |

## Threat Matrix

| Row | Status | Expected behaviour / RED test |
|---|---|---|
| Process integration (model loading) | **Applicable** | Weights load only from `RECEIPT_RISK_VISION_MODEL_DIR`; the file-existence check runs before `torch`/`torchvision` import and before `load_state_dict`; `torch.load(..., map_location="cpu", weights_only=True)` prevents pickle code execution. RED: unset env var → `ANALYZER_UNAVAILABLE`, zero network. |
| Untrusted input decoding | **Applicable** | Image is decoded by the already-hardened ingestion path; the adapter re-opens only the validated `SafeImageRef.path`. RED: adapter never accepts a client-supplied path. |
| Outbound network | **Applicable** | Build-time fetch only; `HF_HUB_OFFLINE=1` plus no `torch.hub`/`weights=` enum usage. RED: existing no-network analysis test. |
| Shell / subprocess | N/A | No subprocess; `S602/S604/S605/S607` remain unignored for `adapters/**`. |
| Routing / VCS-PR automation / executable classification | N/A | No routing or automation surface touched. |

## Migration / Rollout

No data migration. Rollout is additive behind a port. Kill switch: unset `RECEIPT_RISK_VISION_MODEL_DIR` → `ANALYZER_UNAVAILABLE`, 200 responses preserved, `confidence_score` drops by up to 15 points. Full revert restores the previous three-role weights and reproduces prior scores exactly. Golden/contract expectations that hardcode `confidence_score` must be regenerated in the same commit as the weight rebalance.

## Docs / UI copy

- `docs/API.md`: add `"vision": "mobilenetv3-embedding/1.0.0"` to the `/ready` and `/version` examples; add `VISUAL_ANOMALY_DETECTED` (category `visual`, severity low/medium) to the signal/threat matrix.
- `README.md`: stack table gains a Vision row ("PyTorch / MobileNetV3, local weights, no external calls"); Mermaid flow diagram gains the fourth parallel analyzer node.
- i18n new keys (`en` / `es`), plus `'vision'` appended to `STACK_ROWS` in `apps/web/src/routes/docs/+page.svelte`:
  - `docsPage.stack.visionLabel`: `"Vision"` / `"Visión"`
  - `docsPage.stack.visionValue`: `"PyTorch-based visual feature extraction integrated into the document inspection pipeline"` / `"Extracción de características visuales basada en PyTorch, integrada en el pipeline de inspección del documento"`
  - `docsPage.architecture.flow.analyzers` (rewritten): `"Parallel analyzers: metadata/C2PA, OCR, visual inspection and financial rules"` / `"Analizadores en paralelo: metadata/C2PA, OCR, inspección visual y reglas financieras"`

## Open Questions

- [ ] The pinned sha256 for `mobilenet_v3_small-047dcff4.pth` must be downloaded and hashed by hand at apply time before it is written into `fetch_vision_model.py` — the existing script's docstring makes hand-verification a hard precondition, so no hash is asserted here.
- [ ] CPU-wheel install strategy for `torch`/`torchvision` (PyPI default vs the `download.pytorch.org/whl/cpu` index via `[tool.uv.sources]`) must be resolved against `uv.lock` reproducibility and measured image size before merge.
