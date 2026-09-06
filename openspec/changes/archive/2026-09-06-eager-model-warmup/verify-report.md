# Verification Report: eager-model-warmup

**Mode**: full spec-driven verification (proposal + specs + design + tasks + apply-progress all present).
**Verdict**: PASS

## Task Completeness

All 24 tasks across 4 phases in `tasks.md` are checked `[x]`. Spot-checked against source: all claims hold (see Correctness table). No unchecked tasks.

## Correctness -- source inspection vs. contract

| # | Claim | Verified |
|---|---|---|
| 1 | `PaddleOnnxOcrAdapter.warmup()` is `async def`, offloads via `anyio.to_thread.run_sync`, `_warm_sync` catches `OcrEngineUnavailable` then broad `Exception`, both WARNING-log, never raises | YES -- `paddle_onnx.py:183-199` |
| 2 | `_load_embedder` returns `tuple[EmbedCallable, WarmCallable]`; `_forward` shared between `_embed` and `_warm`; warm path uses in-memory `torch.zeros((1,3,224,224))`, no file I/O; `MobileNetV3VisionAdapter.warmup()` same async/exception shape as OCR | YES -- `mobilenet_embedder.py:99-144` (`_forward` at 125, called by both `_embed`:136 and `_warm`:142), `warmup()`/`_warm_sync()` at 228-246 |
| 3 | `_lifespan` (`@asynccontextmanager`) defined BEFORE `app = FastAPI(...)`, wired via `lifespan=`, runs both warmups CONCURRENTLY via `anyio.create_task_group()`/`start_soon` referencing `_ocr`/`_vision` as module globals; duplicated `load_dotenv()` (lines 47/55) deliberately untouched | YES -- `bootstrap/app.py:60-78`; git diff on this file shows only lifespan additions, no touch to the load_dotenv duplication |
| 4 | `/health`, `TimeBudget` fields, `railway.json`, `ENGINE_VERSION` byte-for-byte unchanged | YES -- git diff on analyze_receipt.py and railway.json is empty (no changes); `TimeBudget` at analyze_receipt.py:51-57 (whole_request_s=10.0, ocr_s=6.0, vision_s=3.0, max_concurrent_analyzers=2) untouched; ENGINE_VERSION = "0.3.0" untouched; /health handler in app.py untouched |
| 5 | No new `/ready` `warmed` flag | YES -- only match for "warmed" (case-insensitive) in apps/api/src is the log-event names inside app.py (warmup_completed etc.), not a /ready response field; ReadyResponse schema unchanged |
| 6 | `test_bootstrap_app.py`: 3 pre-existing tests unchanged (bare TestClient(app)), new tests use `with TestClient(app) as client:`, covering concurrent warmup, missing-OCR-dir, missing-vision-dir | YES -- 3 pre-existing tests (lines 26-52) still bare-form with an added deliberate-comment block above them (lines 19-23); 4 new tests (lines 55-144) all use `with TestClient(app) as client:` and cover: concurrent-warmup overlap proof, parametrized missing-dir boot-succeeds test (ocr+vision), and parametrized post-failure ANALYZER_UNAVAILABLE contract test (ocr+vision) |
| 7 | New unit tests for each adapter's warmup() in isolation | YES -- test_ocr_paddle_onnx.py: 3 tests (resolve-once, bogus-dir warning, unexpected-exception warning); test_vision_mobilenet.py: analogous 3 tests plus an injected-embed-override test (5 total) |
| 8 | Test suite run and reported | YES -- see Build/Test Evidence below |
| 9 | Concurrency structurally guaranteed, not just theoretical | YES -- `async with anyio.create_task_group() as tg: tg.start_soon(_ocr.warmup); tg.start_soon(_vision.warmup)` (both scheduled before either awaited/joined); the new concurrent-warmup test asserts overlapping execution windows using 50ms async-sleep spies, and this test passed at runtime |
| 10 | Diff size ~335/-7 across ~6 files | YES -- `git diff --stat` (working tree, uncommitted): exactly 6 files changed, 335 insertions(+), 7 deletions(-), matching apply-progress's self-report exactly. Change is uncommitted (working tree modifications + untracked openspec/changes/eager-model-warmup/) -- not yet committed to a branch/PR. |

## Spec Compliance Matrix (delta spec, "Analysis latency budget" MODIFIED requirement)

| Scenario | Covering test | Result |
|---|---|---|
| Typical request meets p50 target | pre-existing (unchanged) | n/a -- untouched by this change |
| Slow request still meets p95 target | pre-existing (unchanged) | n/a -- untouched by this change |
| First request after fresh process start meets same budgets as request N | integration timing test (design.md Testing Strategy row); skip-guarded, no local model dirs | Not independently re-verified with real models this session -- consistent with apply-progress's skipif-guarded report. Structural guarantee (warmup before listen socket opens) verified. |
| Connection acceptance gated on warmup completion | ASGI lifespan semantics + `_lifespan` reaches `yield` only after task group join | PASS (structural) |
| OCR and vision warmup run concurrently, not sequentially | concurrent-warmup unit test | PASS (ran, green) |
| Missing OCR model dir fails warmup closed without blocking startup | missing-dir startup test [ocr], availability-contract-unchanged test [ocr], OCR adapter warmup unit tests | PASS (ran, green) |
| Missing vision model dir fails warmup closed without blocking startup | same tests [vision] + vision adapter warmup unit tests | PASS (ran, green) |
| Non-regression of health/budgets/availability contract | source diff shows zero changes to analyze_receipt.py, railway.json, /health handler | PASS (confirmed via git diff) |

## Design Coherence

All architecture decisions in design.md were checked against code and match: async warmup() with internal thread offload, two-tier exception handling fail-open at boot, shared _forward + tuple-returning _load_embedder, no ENGINE_VERSION bump, no docs/features/<name>/ mirror. The TestClient/lifespan behavior claim (bare form skips lifespan, `with` form triggers it) is exercised correctly in tests.

## Build/Test Evidence

Command: `uv run pytest -v --color=no` (run from apps/api/; -v used because -q mode's final summary line did not render to redirected output in this pytest 9.1.1/Windows/Git-Bash combination -- a terminal-rendering quirk, confirmed unrelated to test correctness by re-running identically with -v).

**Result**: 220 passed, 14 skipped, 1 warning in 7.61s. Exit code: 0.

- The 1 warning is a pre-existing StarletteDeprecationWarning (httpx/starlette.testclient), unrelated to this change.
- The 14 skipped tests are integration tests requiring real model directories not present in this environment (skipif-guarded).
- No failures.

Diff evidence: `git diff --stat` (working tree) -> 6 files changed, 335 insertions(+), 7 deletions(-).

## Issues

**CRITICAL**: None.

**WARNING**: None.

**SUGGESTION**:
- The change is currently uncommitted (working tree only). Recommend committing before archive, per single-pr delivery strategy.
- `pytest -q` failed to render its final summary line to redirected output on Windows/Git-Bash/pytest-9.1.1; future verify runs on this stack should default to `pytest -v` or verify via a captured file to avoid mistaking this rendering quirk for a hung run.

## Final Verdict: PASS

All 24 tasks complete and independently corroborated against source, not just apply-progress's self-report. All spec scenarios have a passing covering test or a structural/ASGI-semantic guarantee. No regression to /health, TimeBudget, railway.json, or ENGINE_VERSION. No new /ready warmed flag. Full unit suite green (220 passed, 14 skipped, 0 failed, exit 0). Diff size matches apply-progress's claim exactly (335/-7, 6 files). Ready for archive once committed.
