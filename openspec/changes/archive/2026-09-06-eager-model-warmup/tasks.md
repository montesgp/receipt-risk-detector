# Tasks: Eager Model Warmup at API Startup

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 220-320 (paddle_onnx.py ~25-35; mobilenet_embedder.py ~50-70, mostly the `_load_embedder` tuple/`_forward` split; bootstrap/app.py ~20-25; test_bootstrap_app.py ~60-80 new; two new adapter test files ~60-100 combined) |
| Session review budget (cached) | 800 lines |
| 400-line budget risk | Low (well inside both the session's cached 800-line budget and the skill's generic 400-line default) |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Whole change: adapter `warmup()` methods, `_load_embedder` tuple refactor, `_lifespan` wiring, unit tests | PR 1 | `uv run pytest apps/api/tests/unit/test_ocr_paddle_onnx.py apps/api/tests/unit/test_vision_mobilenet.py apps/api/tests/unit/test_bootstrap_app.py -q` | N/A — pure adapter/bootstrap unit logic, mocked engine/embed construction, no real model files loaded | Revert commit; deleting `_lifespan` and `lifespan=_lifespan` from `FastAPI(...)` alone is a safe partial rollback (the `warmup()` methods are additive and inert if never called, per design.md's Migration/Rollout section) |

Estimate is within the cached 800-line budget, so no chaining or exception is required before `sdd-apply`.

## Phase 1: OCR Adapter Warmup

- [x] 1.1 RED: extend `apps/api/tests/unit/test_ocr_paddle_onnx.py` — test that `PaddleOnnxOcrAdapter.warmup()` calls `_resolve_engine()` exactly once when a valid `engine=` override is injected (spy/counter), and does not raise.
- [x] 1.2 RED: same file — test that `warmup()` on an adapter pointed at a missing/bogus `model_dir` (no `engine=` override) returns `None` without raising, and `caplog` captures one WARNING-level `warmup_unavailable` log record with `extra={"analyzer": "paddleocr-onnx"}` (no `model_dir`/path/exception text in the message).
- [x] 1.3 RED: same file — test that when `_resolve_engine()` raises an unexpected `RuntimeError` (patch/mock the resolution path to raise), `warmup()` still returns `None` without propagating, and `caplog` captures one WARNING-level `warmup_failed` log record with `extra={"analyzer": "paddleocr-onnx"}`.
- [x] 1.4 GREEN: `apps/api/src/receipt_risk/adapters/ocr/paddle_onnx.py` — add a module-level `log = logging.getLogger(__name__)` (new `import logging`).
- [x] 1.5 GREEN: same file — add `async def warmup(self) -> None` on `PaddleOnnxOcrAdapter` that awaits `anyio.to_thread.run_sync(self._warm_sync)`.
- [x] 1.6 GREEN: same file — add `def _warm_sync(self) -> None` that calls `self._resolve_engine()` inside `try/except`: `except OcrEngineUnavailable` logs WARNING `warmup_unavailable` with `extra={"analyzer": self.name}` and returns; `except Exception` (with `# noqa: BLE001` and a comment that boot must never fail harder than a request) logs WARNING `warmup_failed` with `extra={"analyzer": self.name}` and returns; on success, logs INFO `warmup_completed` with `extra={"analyzer": self.name, "duration_ms": _elapsed_ms(started)}`.
- [x] 1.7 Verify: run the existing OCR adapter unit tests unchanged and green — `_resolve_engine()`'s existing caching behavior (second `extract()` call reusing the engine after a `warmup()` call) is unaffected, since `warmup()` only calls the same `_resolve_engine()` path already used by `extract()`.

## Phase 2: Vision Adapter Warmup

- [x] 2.1 RED: extend `apps/api/tests/unit/test_vision_mobilenet.py` — test with a fake `_load_embedder` (or an injected loader hook, per whatever seam the adapter exposes after refactor) returning `(_embed, spy_warm)`: `MobileNetV3VisionAdapter.warmup()` calls the returned warm hook exactly once, and no `preprocess()`/file I/O occurs (assert the spy received no arguments / a synthetic tensor, not a `Path`).
- [x] 2.2 RED: same file — confirm the one existing direct caller of `_load_embedder` (line ~77 per design.md) still only asserts it raises on a bogus `model_dir`; update that call site's unpacking to the new `tuple[EmbedCallable, WarmCallable]` return shape if the raise happens before unpacking, verify no behavior change is needed.
- [x] 2.3 RED: same file — test that `warmup()` on an adapter pointed at a missing/bogus `model_dir` (no `embed=` override) returns `None` without raising, and `caplog` captures one WARNING-level `warmup_unavailable` log record with `extra={"analyzer": "mobilenetv3-embedding"}`.
- [x] 2.4 RED: same file — test that when the embedder-loading path raises an unexpected `RuntimeError`, `warmup()` still returns `None` without propagating, and `caplog` captures one WARNING-level `warmup_failed` log record with `extra={"analyzer": "mobilenetv3-embedding"}`.
- [x] 2.5 RED: same file — test that when the adapter is constructed with an injected `embed=` override (so `self._lazy_warm` stays `None` per design.md's "tests warm only the reference embeddings" note), `warmup()` still resolves the reference embeddings (via `self._resolve()`) but does not attempt to call a `None` warm hook and does not raise.
- [x] 2.6 GREEN: `apps/api/src/receipt_risk/adapters/vision/mobilenet_embedder.py` — add a module-level `log = logging.getLogger(__name__)` (new `import logging`); add `WarmCallable = Callable[[], None]` type alias near `EmbedCallable`.
- [x] 2.7 GREEN: same file — refactor `_load_embedder`'s inner `_embed` function: extract the tensor-forward tail (from `with torch.no_grad():` through the `return normalized.squeeze(0)...` line) into a new nested `_forward(tensor) -> np.ndarray` helper; rewrite `_embed(path)` as `preprocess(path)` → `torch.from_numpy(...).unsqueeze(0)` → `return _forward(tensor)`.
- [x] 2.8 GREEN: same file — add a nested `_warm() -> None` function calling `_forward(torch.zeros((1, 3, 224, 224), dtype=torch.float32))` and discarding the result, with a comment explaining the in-memory synthetic tensor pays PyTorch's first-call thread-pool/kernel-dispatch cost that `torch.load`/`.eval()` alone does not.
- [x] 2.9 GREEN: same file — change `_load_embedder`'s return type/statement from `return _embed` to `return _embed, _warm`; update its signature to `-> tuple[EmbedCallable, WarmCallable]`.
- [x] 2.10 GREEN: same file — `MobileNetV3VisionAdapter.__init__` gains `self._lazy_warm: WarmCallable | None = None`; `_resolve()`'s `self._lazy_embed = _load_embedder(self._model_dir)` line becomes `self._lazy_embed, self._lazy_warm = _load_embedder(self._model_dir)`; the injected-`embed=` override branch leaves `self._lazy_warm` as `None` (unchanged, no assignment there).
- [x] 2.11 GREEN: same file — add `async def warmup(self) -> None` awaiting `anyio.to_thread.run_sync(self._warm_sync)`, and `def _warm_sync(self) -> None` following the same two-tier `except VisionEngineUnavailable` / `except Exception` pattern as OCR's `_warm_sync`, logging WARNING `warmup_unavailable` / `warmup_failed` with `extra={"analyzer": self.name}` on failure, and calling `self._resolve()` then `self._lazy_warm()` only when `self._lazy_warm is not None`, followed by INFO `warmup_completed` with `extra={"analyzer": self.name, "duration_ms": _elapsed_ms(started)}` on success.
- [x] 2.12 Verify: run the existing vision adapter unit tests unchanged and green, in particular the `test_vision_mobilenet.py:77`-area test asserting `_load_embedder` raises on a bogus dir — confirm it still raises before ever reaching the tuple-unpacking return.

## Phase 3: Bootstrap Lifespan Wiring

- [x] 3.1 RED: extend `apps/api/tests/unit/test_bootstrap_app.py` — new test using `with TestClient(app) as client:` (not the bare form): monkeypatch `_ocr.warmup` and `_vision.warmup` with async spies that record entry/exit `time.monotonic()` timestamps; assert both spies were called exactly once, and their recorded execution windows overlap (proves concurrent `max(...)`, not sequential `sum(...)`, per the spec's "OCR and vision warmup run concurrently" scenario).
- [x] 3.2 RED: same file — new test: `monkeypatch.delenv` both `RECEIPT_RISK_OCR_MODEL_DIR` and `RECEIPT_RISK_VISION_MODEL_DIR` (or construct adapters with a bogus `model_dir` pointing at a nonexistent path, whichever fits the module's existing adapter-construction seam), enter `with TestClient(app) as client:` without raising, then assert `GET /health` → 200 and `GET /ready` → 200 (app still boots and becomes reachable per the spec's "fails silently... application still starts" scenarios, exercised for OCR and vision independently — write it as two tests, or one parametrized test, whichever matches this file's existing style).
- [x] 3.3 RED: same file — extend 3.2's missing-model-dir test(s): after entering the `with` block with warmup having failed, issue an actual `POST /v1/receipts/analyze` request (or call the affected adapter's `extract()`/`inspect()` directly if a full request needs unrelated fixture plumbing) and assert the response still carries `ANALYZER_UNAVAILABLE` for the affected analyzer, confirming the per-request degradation contract is unchanged after a failed startup warmup.
- [x] 3.4 Confirm (no code change): the 3 existing tests in `test_bootstrap_app.py` (`test_ready_endpoint_reports_four_analyzers_including_vision`, `test_version_endpoint_includes_vision_analyzer_entry`, `test_version_endpoint_reports_active_ruleset_2026_09_06`) use the bare `TestClient(app)` form and never enter the context manager, so per design.md's traced Starlette source they never trigger `lifespan.startup` and never invoke real `warmup()`. Leave these 3 tests byte-for-byte unchanged — do not convert them to the `with` form; add a one-line comment above them noting the bare form is deliberate (fast, no real model load).
- [x] 3.5 GREEN: `apps/api/src/receipt_risk/bootstrap/app.py` — add new imports: `logging`, `time`, `from contextlib import asynccontextmanager`, `from collections.abc import AsyncIterator`, `import anyio`. Add module-level `log = logging.getLogger(__name__)`.
- [x] 3.6 GREEN: same file — define `@asynccontextmanager async def _lifespan(_app: FastAPI) -> AsyncIterator[None]:` **above** the `app = FastAPI(...)` line (per design.md: `_ocr`/`_vision` are resolved as module globals at call time, not definition time, so no existing wiring below it needs to move). Body: record `started = time.monotonic()`, open `async with anyio.create_task_group() as tg:` and `tg.start_soon(_ocr.warmup)` / `tg.start_soon(_vision.warmup)`, then after the group closes log INFO `startup_warmup_completed` with `extra={"duration_ms": int((time.monotonic() - started) * 1000)}`, then `yield`.
- [x] 3.7 GREEN: same file — change `app = FastAPI(title="Transfer Receipt Risk Engine")` to `app = FastAPI(title="Transfer Receipt Risk Engine", lifespan=_lifespan)`. Do not move, reorder, or touch `_temp_dir`, `_ocr`, `_metadata`, `_provenance`, `_vision`, `_ingestion`, `_use_case`, `app.dependency_overrides[get_use_case]`, `/health`, `/ready`, or `/version` — all stay exactly as they are today.
- [x] 3.8 Explicitly do NOT touch: the duplicated `load_dotenv()` calls at lines 42 and 50 stay exactly as-is (design.md flags this as a pre-existing, out-of-scope issue — do not "clean it up" as a drive-by in this change).
- [x] 3.9 Verify: run the full `test_bootstrap_app.py` file — 3 existing bare-`TestClient` tests unchanged and green, plus the new `with`-block tests from 3.1-3.3 green.

## Phase 4: Full Regression and Non-Regression Checks

- [x] 4.1 Run the full API unit suite: `uv run pytest apps/api/tests/unit -q` — confirm all green, in particular no change to any existing `/health`, `TimeBudget`, `ENGINE_VERSION`, or ruleset-version assertion anywhere in the suite (this change touches none of them).
- [x] 4.2 Run `apps/api/tests/integration` if it includes a real-model timing check (per design.md's Testing Strategy "Integration | Real request-1 timing after warmup" row) — confirm first analyze meets `ocr_s`/`vision_s` budgets when both model dirs are genuinely configured. Skip/mark this if no such fixture exists yet; do not fabricate new integration fixtures beyond what design.md scopes.
- [x] 4.3 Confirm no diff touches `railway.json`, `/health`, `/ready`'s `warmed` flag (none added), `TimeBudget.ocr_s`/`vision_s`/`whole_request_s`/`max_concurrent_analyzers` values, or `ENGINE_VERSION`.
- [x] 4.4 Confirm `openspec/specs/receipt-analysis/spec.md` (main spec) is NOT edited by this change — the delta spec at `openspec/changes/eager-model-warmup/specs/receipt-analysis/spec.md` merges at archive time only, per repo convention.

## Key Learnings

1. Bare `TestClient(app)` never sends the ASGI `lifespan.startup` message under the pinned Starlette 1.6.0 — only `with TestClient(app) as client:` triggers it, so warmup-path tests must use the `with` form while the 3 pre-existing tests must stay on the bare form to avoid an accidental real-model-load regression.
2. `_lifespan` can be defined above `app = FastAPI(...)` even though `_ocr`/`_vision` are defined below it, because Python resolves module globals at call time, not at function-definition time.
3. Warmup deliberately fails open at boot (WARNING + return) while the per-request contract stays fail-closed (`ANALYZER_UNAVAILABLE`), because a stricter boot-time failure would brick a deploy that the existing request-time contract would otherwise serve in degraded form.
4. The vision adapter's `_load_embedder` must return a `tuple[EmbedCallable, WarmCallable]` because only its internal closure holds references to the loaded `model` and `torch` module, so the warm hook cannot be reconstructed outside the loader.
5. This change's estimated diff size fits well inside the session's cached 800-line review budget, so no chained-PR decision is required before `sdd-apply`.
