# Design: Eager Model Warmup at API Startup

## Technical Approach

Add one `@asynccontextmanager` `lifespan` to `bootstrap/app.py` that awaits a new public
`warmup()` on both heavy adapters inside an `anyio` task group. Each `warmup()` is `async def`,
offloads its blocking load to a worker thread via `anyio.to_thread.run_sync` (the same primitive
`extract()`/`inspect()` already use), and absorbs its own failures. Startup therefore blocks the
ASGI `lifespan.startup.complete` message — and thus uvicorn's listen socket — for
`max(ocr, vision)`, never crashing. No endpoint, budget, or scoring code changes.

## Architecture Decisions

### Decision: `warmup()` is `async def` with an internal thread offload

**Choice**: `async def warmup(self) -> None` awaiting `anyio.to_thread.run_sync(self._warm_sync)`.
**Alternatives**: a sync `warmup()` that bootstrap offloads itself.
**Rationale**: mirrors the existing port shape (`async def extract`/`async def inspect` own their
own offload); keeps `bootstrap/` free of threading concerns; lets the task group call
`tg.start_soon(_ocr.warmup)` with no lambda. It also offloads `_resolve_engine()`/`_resolve()`,
which `extract()`/`inspect()` currently call *on the event loop* (paddle_onnx.py:183,
mobilenet_embedder.py:217) — warmup does not inherit that blocking-loop wart.

### Decision: warmup catches `Exception`, not only the typed unavailable error

**Choice**: two-tier `except OcrEngineUnavailable / VisionEngineUnavailable` → `warmup_unavailable`,
then `except Exception` → `warmup_failed`. Both log WARNING and return normally.
**Alternatives**: catch only the typed unavailable exception and let anything else abort startup.
**Rationale**: `AnalyzeReceiptUseCase._guarded` (analyze_receipt.py:191) already swallows *any*
adapter exception into a degraded `AnalyzerResult`. A warmup that hard-failed boot on a corrupt
`.pth` or a torch import error would be **stricter than the request contract**, bricking a deploy
that would otherwise serve degraded results. Fail-open at boot, fail-closed per request.

### Decision: vision warmup runs a synthetic forward pass; `_load_embedder` returns a warm hook

**Choice**: refactor `_embed`'s tensor tail into a shared `_forward(tensor)`; `_load_embedder`
returns `tuple[EmbedCallable, WarmCallable]`; `_warm()` runs `torch.zeros((1,3,224,224))` through
`_forward`.
**Alternatives**: attach `.warm` as a function attribute on `_embed` (untyped magic); make
`EmbedCallable` accept `Path | None` (overloads the contract, breaks injected fakes).
**Rationale**: only the closure holds `model`/`torch`, so the hook must come out of the loader.
The tuple is explicit and type-checkable. The one existing direct caller
(`tests/unit/test_vision_mobilenet.py:77`) only asserts it raises, so it is unaffected.
OCR keeps its signature — `_load_rapidocr_engine` is used as an engine factory by
`tests/integration/test_ocr_integration.py:109` and construction alone pays ONNX Runtime's
session/graph-optimization cost.

### Decision: no `ENGINE_VERSION` bump

**Choice**: `ENGINE_VERSION` stays `0.3.0`; ruleset untouched.
**Rationale**: it versions detection/scoring semantics. Warmup changes *when* a model loads, not
any signal, score, or verdict. Identical inputs still produce identical outputs.

### Decision: `docs/features/<name>/` mirroring is N/A

`config.yaml` `rules.design` asks for it, but the last four archived changes (c2pa-ai-claim-detection,
scoring-confidence-calibration, generic-receipt-field-extraction, ui-design-refresh) skipped it.
Observed practice reserves it for feature-scale capabilities; this is an operational change.

## Data Flow

    uvicorn start
      └─ import bootstrap.app  (adapters constructed, cheap, no model I/O)
      └─ ASGI "lifespan.startup"
           └─ _lifespan()
                └─ anyio.create_task_group()
                     ├─ _ocr.warmup()    → thread → _resolve_engine() → RapidOCR(...)
                     └─ _vision.warmup() → thread → _resolve() + _warm() (zeros fwd pass)
                     (both concurrent; group joins at max(ocr, vision))
      └─ "lifespan.startup.complete" ──→ listen socket opens ──→ Railway /health passes
                                                                 request 1 == request N

Failure branch: either `warmup()` logs WARNING and returns `None`; the group still joins normally,
startup completes, and the adapter's lazy `_resolve*` path raises per request exactly as today →
`AnalyzerResult(status="failed", error_code="ANALYZER_UNAVAILABLE")`.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `apps/api/src/receipt_risk/bootstrap/app.py` | Modify | Add `_lifespan` above line 52; pass `lifespan=_lifespan` to `FastAPI(...)` |
| `apps/api/src/receipt_risk/adapters/ocr/paddle_onnx.py` | Modify | Module `log`; `warmup()` + `_warm_sync()` |
| `apps/api/src/receipt_risk/adapters/vision/mobilenet_embedder.py` | Modify | Module `log`; `_forward`/`_warm` split; `_load_embedder` returns a tuple; `_lazy_warm` state; `warmup()` + `_warm_sync()` |
| `apps/api/tests/unit/test_bootstrap_app.py` | Modify | Keep 3 existing tests as-is; add 2 lifespan tests |

**Existing module-level wiring does not move.** `_ocr`/`_vision` (lines 73/76),
`_use_case`, and `app.dependency_overrides[get_use_case]` (line 88) stay exactly where they are.
`_lifespan` resolves `_ocr`/`_vision` as globals *at startup call time*, not at definition time, so
defining it above `FastAPI(...)` while the adapters are defined below is correct Python.
(Incidental: `load_dotenv()` is duplicated at lines 42 and 50 — noted, not in scope.)

## Interfaces / Contracts

`bootstrap/app.py` (new imports: `logging`, `time`, `contextlib.asynccontextmanager`,
`collections.abc.AsyncIterator`, `anyio`):

```python
log = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Warm both heavy models before uvicorn opens its listen socket.
    ASGI holds `lifespan.startup.complete` until this reaches `yield`, so no
    request can observe a partially warmed process. Never raises: each
    `warmup()` absorbs its own failure and leaves the per-request
    `ANALYZER_UNAVAILABLE` contract untouched."""
    started = time.monotonic()
    async with anyio.create_task_group() as tg:
        tg.start_soon(_ocr.warmup)
        tg.start_soon(_vision.warmup)
    log.info("startup_warmup_completed", extra={"duration_ms": int((time.monotonic() - started) * 1000)})
    yield


app = FastAPI(title="Transfer Receipt Risk Engine", lifespan=_lifespan)
```

`adapters/ocr/paddle_onnx.py`:

```python
    async def warmup(self) -> None:
        """Eagerly pay ONNX Runtime session-creation cost at startup."""
        await anyio.to_thread.run_sync(self._warm_sync)

    def _warm_sync(self) -> None:
        started = time.monotonic()
        try:
            self._resolve_engine()
        except OcrEngineUnavailable:
            log.warning("warmup_unavailable", extra={"analyzer": self.name})
            return
        except Exception:  # noqa: BLE001 -- boot must never fail harder than a request
            log.warning("warmup_failed", extra={"analyzer": self.name})
            return
        log.info("warmup_completed", extra={"analyzer": self.name, "duration_ms": _elapsed_ms(started)})
```

`adapters/vision/mobilenet_embedder.py`:

```python
WarmCallable = Callable[[], None]


def _load_embedder(model_dir: Path | None) -> tuple[EmbedCallable, WarmCallable]:
    ...  # unchanged validation + torch/torchvision import + load_state_dict + eval

    def _forward(tensor) -> np.ndarray:  # (1, 3, 224, 224) -> (576,)
        with torch.no_grad():
            features = model.features(tensor)
            pooled = torch.nn.functional.adaptive_avg_pool2d(features, 1)
            flat = torch.flatten(pooled, 1)
            normalized = torch.nn.functional.normalize(flat, p=2, dim=1)
        return normalized.squeeze(0).cpu().numpy().astype(np.float32)

    def _embed(path: Path) -> np.ndarray:
        return _forward(torch.from_numpy(preprocess(path)).unsqueeze(0))

    def _warm() -> None:
        # No file, no preprocess(), no fixture -- an in-memory tensor is enough to
        # pay PyTorch's first-call thread-pool / oneDNN kernel-dispatch cost that
        # torch.load()/.eval() alone does not.
        _forward(torch.zeros((1, 3, 224, 224), dtype=torch.float32))

    return _embed, _warm
```

`_resolve()` becomes `self._lazy_embed, self._lazy_warm = _load_embedder(self._model_dir)` and still
returns `(embed, reference)`, so `inspect()` is untouched. `__init__` gains
`self._lazy_warm: WarmCallable | None = None`. `warmup()` mirrors OCR's, calling `self._resolve()`
then `self._lazy_warm()` when it is not `None` (it stays `None` under an injected `embed` override,
so tests warm only the reference embeddings — cheap and correct).

## TestClient / lifespan: settled from source

**Pinned**: `fastapi 0.141.1`, `starlette 1.6.0`, `anyio 4.14.2` (`apps/api/uv.lock`).

**Definitive answer: bare `TestClient(app)` does NOT run lifespan.**
Traced in `apps/api/.venv/Lib/site-packages/starlette/testclient.py`: `TestClient.__init__`
(lines 382–420) only builds `_TestClientTransport` and an empty `self.app_state` — it sends no
lifespan message. The only sender is `__enter__` (lines 679–706):
`self.task = portal.start_task_soon(self.lifespan)` then `portal.call(self.wait_startup)`, where
`wait_startup` sends `{"type": "lifespan.startup"}` (line 719). `request()` goes through
`_TestClientTransport.handle_request`, which builds an `http` scope and calls the app directly
(lines 349–351) with no lifespan involvement.

**Consequence**: the 3 existing tests in `test_bootstrap_app.py` **need no change**. They assert
`/ready` and `/version` roster content only, and by never entering the context manager they never
trigger warmup — so they stay fast and never touch a real model. Switching them to the `with` form
would be a behavioral regression (every one would attempt a real model load). Add a comment noting
the bare form is deliberate. New warmup coverage uses `with TestClient(app) as client:` explicitly.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit (adapter) | OCR `warmup()` resolves the engine once | Inject `engine=` / patch `_load_rapidocr_engine` with a counting spy; assert one construction and that a second `warmup()`/`extract()` reuses it |
| Unit (adapter) | Vision `_warm()` runs a `(1,3,224,224)` forward pass | Fake loader returning `(_embed, spy_warm)`; assert `spy_warm` called once and no `preprocess`/file I/O occurred |
| Unit (adapter) | Missing model dir → `warmup()` returns `None`, does not raise | Point `model_dir` at a bogus path; `caplog` asserts one WARNING `warmup_unavailable`; no exception |
| Unit (adapter) | Unexpected exception → `warmup()` still returns | Patch loader to raise `RuntimeError`; assert WARNING `warmup_failed`, no raise |
| Unit (bootstrap) | (a) Successful concurrent warmup at startup | Monkeypatch `_ocr.warmup`/`_vision.warmup` with async spies that record entry/exit timestamps; `with TestClient(app) as client:` → both called exactly once, and their execution windows overlap (proves `max`, not `sum`) |
| Unit (bootstrap) | (b) Missing model dirs at startup do not crash boot | `monkeypatch.delenv` both `RECEIPT_RISK_*_MODEL_DIR`, rebuild adapters with bogus `model_dir`; `with TestClient(app) as client:` must enter without raising, `GET /health` → 200, `GET /ready` → 200 |
| Unit (bootstrap) | (b cont.) Availability contract unchanged after failed warmup | With warmup failed, `await adapter.extract(safe)` / `.inspect(safe)` still returns `status="failed"`, `error_code="ANALYZER_UNAVAILABLE"` |
| Integration | Real request-1 timing after warmup | Existing marked integration path with real models; assert first analyze meets `ocr_s`/`vision_s` |

## Logging

House style is `analyze_receipt.py:193` — `log.warning("analyzer_failed", extra={"analyzer": role})`,
snake_case event name, structured `extra`, no payload/PII. Warmup follows it exactly:

| Event | Level | `extra` |
|---|---|---|
| `warmup_completed` | INFO | `analyzer`, `duration_ms` |
| `warmup_unavailable` | WARNING | `analyzer` |
| `warmup_failed` | WARNING | `analyzer` |
| `startup_warmup_completed` | INFO | `duration_ms` |

Never log `model_dir`, paths, env values, or exception text — a path can leak deployment topology,
and `OcrEngineUnavailable`'s message embeds the directory. `analyzer` is a fixed class attribute
(`paddleocr-onnx` / `mobilenetv3-embedding`), so it is safe. No `exc_info`, matching `_guarded`.

## Startup Latency Accounting

`anyio.create_task_group()` with two `start_soon` calls schedules both coroutines before joining, so
each reaches its own `anyio.to_thread.run_sync` and occupies a distinct worker thread (the default
limiter allows 40). Wall clock is therefore `max(ocr, vision)` plus GIL-serialized Python import
machinery, **not** their sum. Measured cold cost ≈ 3.85 s OCR and ≈ 4.87 s vision → expect ≈ 5–8 s,
versus `railway.json`'s `healthcheckTimeout: 60`. Roughly 7× headroom; unchanged and out of scope,
but a monitored assumption rather than a permanent guarantee across Railway CPU tiers.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or
process-integration boundary is changed. Model loading stays in-process library loading from a
directory validated by the untouched `_load_rapidocr_engine`/`_load_embedder` fail-closed checks;
no new path, argv, network call, or download is introduced (`HF_HUB_OFFLINE=1` and `weights_only=True`
remain as-is). This design only changes *when* those existing, unmodified checks run.

## Migration / Rollout

No migration. Deploys naturally serve traffic only after warmup, which is the intent.

**Rollback**: delete `_lifespan` and drop `lifespan=_lifespan` from `FastAPI(...)` — one-hunk revert
restoring lazy first-request loading. The `warmup()` methods and the `_load_embedder` tuple refactor
are additive and inert when never called, so a full `git revert` of the change commit is also clean.
No ruleset, `ENGINE_VERSION`, or golden implications.

## Open Questions

- [ ] Whether OCR needs a synthetic inference in addition to construction — deferred to verify;
      add it only if request-1-after-warmup OCR timing still exceeds the warm baseline.
- [ ] Concurrent first-time `import torch` and `import rapidocr_onnxruntime` from two worker threads
      is safe under CPython 3.12 per-module import locks (both already share an imported `numpy`),
      but has not been exercised in this repo — watch for a startup hang during verify.
