# Proposal: Eager Model Warmup at API Startup

## Intent

OCR and vision models load lazily on the first real request after every process start. On Railway, every redeploy resets warm state, so the first caller after each deploy pays ~5.5s of model loading (vision alone 4866ms) and blows its 3.0s per-analyzer budget, producing a degraded/timeout result. The same endpoint serves non-human automation clients that cannot be told "retry once", and identical requests returning different scores depending on invisible server warmth contradicts the project's deterministic-scoring principle. Moving that cost into container startup makes request 1 behave exactly like request N at no extra hosting cost (Railway usage billing has no sleep state; the container is billed either way).

## Scope

### In Scope

- An async `lifespan` context manager on `FastAPI(...)` in `bootstrap/app.py` that warms OCR and vision concurrently before uvicorn opens the listen socket.
- A small public `warmup()` method on `PaddleOnnxOcrAdapter` and `MobileNetV3VisionAdapter`, so bootstrap never reaches into `_resolve_engine()`/`_resolve()`.
- Vision warmup = construction **plus** one synthetic forward pass over an in-memory `torch.zeros((1,3,224,224))`, mirroring `_embed`'s body. Rationale: PyTorch CPU carries first-call thread-pool/kernel-dispatch cost that `torch.load`/`.eval()` does not pay; no image file or fixture needed.
- OCR warmup = `RapidOCR(...)` construction only. Rationale: ONNX Runtime performs graph optimization at session creation; no repo evidence of residual first-inference cost.
- Fail-closed parity: each warmup independently wrapped; a missing/unset `RECEIPT_RISK_*_MODEL_DIR` logs a warning and startup continues, leaving the per-request `ANALYZER_UNAVAILABLE` contract untouched.
- Resolve empirically whether bare `TestClient(app)` triggers lifespan under the pinned Starlette; update the 3 existing tests if not, and add missing-model-dir startup coverage.

### Out of Scope

- Recalibrating `TimeBudget` (`ocr_s`, `vision_s`, `whole_request_s`) or `max_concurrent_analyzers`.
- Any change to `/health` behavior — ASGI lifespan already gates reachability.
- A new `/ready` `warmed` flag. Redundant once `/ready` is unreachable until warmup finishes, and it would expand a documented contract for no operational gain.
- Changing `railway.json` timeouts.

## Capabilities

### New Capabilities

- `service-startup-warmup`: the API SHALL complete model warmup before accepting connections, and SHALL still start when a model directory is absent.

### Modified Capabilities

- None. `public-api-contract` endpoints and payloads are unchanged.

## Approach

`@asynccontextmanager` lifespan; both `warmup()` calls offloaded via `anyio.to_thread.run_sync` and run concurrently (`asyncio.gather`) so startup cost is `max(ocr, vision)`, not the sum. Adapters keep their existing internal caching, so warmup is just an early first call.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `apps/api/src/receipt_risk/bootstrap/app.py` | Modified | Add lifespan, wire warmup |
| `apps/api/src/receipt_risk/adapters/ocr/paddle_onnx.py` | Modified | Public `warmup()` |
| `apps/api/src/receipt_risk/adapters/vision/mobilenet_embedder.py` | Modified | Public `warmup()` + synthetic pass |
| `apps/api/tests/unit/test_bootstrap_app.py` | Modified | Lifespan-aware client, new startup test |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Startup exceeds `healthcheckTimeout: 60` | Low | ~5.5-8s measured; monitor, do not assume permanent |
| Bare `TestClient` skips lifespan | Med | Verify against pinned version before implementing |
| Synthetic vision pass insufficient/excessive | Low | Spot-check request-1-after-warmup timing during verify |
| Deploy traffic delayed until warmup ends | Certain | Intended: Railway holds routing, hiding cold start |

## Rollback Plan

Revert the lifespan wiring in `bootstrap/app.py`; adapters fall back to their unchanged lazy `_resolve*` path. The `warmup()` methods are additive and harmless if left in place.

## Dependencies

- None new. `anyio` already ships with Starlette.

## Success Criteria

- [ ] First request after a fresh container start meets all per-analyzer budgets.
- [ ] App starts and serves `/health` and `/ready` with both model dirs unset.
- [ ] No `/health`, `/ready`, `/version`, or `TimeBudget` contract changes.

## Proposal question round

Ran in auto mode, so these were resolved from the exploration and the session's confirmed direction rather than asked: (1) is delaying post-deploy traffic acceptable — assumed yes, it is the goal; (2) is warmup observability needed — assumed no, deferred; (3) must warmup ever hard-fail a deploy — assumed no, fail-closed parity wins. Correct any of these before spec.
