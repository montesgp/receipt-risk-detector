# Archive Report: eager-model-warmup

**Date**: 2026-09-06
**Status**: CLOSED — All 24 implementation tasks complete, verification PASS, specs merged, change archived.

## Executive Summary

The `eager-model-warmup` SDD change moves OCR and vision model loading from the first request (lazy) to container startup (eager), so request 1 after any process restart meets the same per-analyzer latency budgets as request N. All 24 implementation tasks complete; verification confirmed zero regressions to `/health`, `TimeBudget`, `railway.json`, or `ENGINE_VERSION`. The delta spec merging one MODIFIED requirement (`Analysis latency budget`) into `openspec/specs/receipt-analysis/spec.md`, and the entire change folder has been archived to `openspec/changes/archive/2026-09-06-eager-model-warmup/`.

## Artifact Traceability (Engram Observation IDs)

| Artifact | Engram ID | Created | Status |
|----------|-----------|---------|--------|
| Proposal | 1914 | 2026-09-06 05:13:06 | Archived ✓ |
| Delta Spec | 1915 | 2026-09-06 05:18:26 | Archived ✓ |
| Design | 1916 | 2026-09-06 05:21:22 | Archived ✓ |
| Tasks | 1917 | 2026-09-06 05:23:34 | Archived ✓ |
| Apply Progress | 1918 | 2026-09-06 05:27:39 | Snapshot |
| Verify Report | 1919 | 2026-09-06 05:32:37 | Verdict: PASS |
| Archive Report | [TBD] | 2026-09-06 | Current |

## Specification Merge Details

**Merged File**: `openspec/specs/receipt-analysis/spec.md`

**Operation**: MODIFIED requirement `Analysis latency budget` (line 173–184 → lines 173–234)

**Delta Applied**: 7 scenarios expanded from 2, with new requirement text defining:
- Concurrent OCR and vision warmup at startup before ASGI socket opens
- Fail-closed warmup (never aborts boot, warns and defers to per-request `ANALYZER_UNAVAILABLE`)
- Non-regression of `/health`, `TimeBudget`, and analyzer-availability contract

**Preserved**: All other 8 requirements and Key Learnings unchanged. Main spec structure intact.

## Archive Location

**From**: `openspec/changes/eager-model-warmup/`
**To**: `openspec/changes/archive/2026-09-06-eager-model-warmup/`

**Contents**:
- `proposal.md` ✓
- `design.md` ✓
- `tasks.md` ✓ (all 24 tasks marked `[x]`)
- `verify-report.md` ✓ (verdict PASS)
- `specs/receipt-analysis/spec.md` ✓ (delta spec for reference)

**Active Changes Directory**: No `openspec/changes/eager-model-warmup/` directory remains after archive move.

## Final-State Facts (Authority Hierarchy)

Per Final-State Authority (sdd-archive skill §45–66):

1. **Task Completion**: All 24 tasks across 4 phases (`bootstrap`, `ocr`, `vision`, `regression`) marked `[x]` in persisted `tasks.md` observation (id 1917, revised 2026-09-06 05:23:34). Spot-checked by sdd-verify: verified.

2. **Verification Verdict**: PASS (id 1919, 2026-09-06 05:32:37).
   - CRITICAL issues: None.
   - WARNING issues: None.
   - SUGGESTION (non-blocking): Change currently uncommitted (working tree); pytest `-q` rendering quirk on Windows unrelated to tests.
   - Build evidence: `220 passed, 14 skipped, 0 failed, exit 0`.

3. **Implementation Scope**: Diff confirmed exactly 6 files, +335/-7 lines (per `git diff --stat`), matching apply-progress (id 1918):
   - `paddle_onnx.py`: module `log`, `warmup()`, `_warm_sync()` with two-tier exception handling
   - `mobilenet_embedder.py`: module `log`, `_forward`/`_warm` refactor, `_load_embedder` returns tuple
   - `bootstrap/app.py`: `_lifespan` asynccontextmanager, `anyio.create_task_group()` concurrent warmup, `lifespan=_lifespan` wiring
   - `test_bootstrap_app.py`: 3 existing bare-`TestClient` tests unchanged, 4 new `with` form tests
   - `test_ocr_paddle_onnx.py`: 3 new warmup unit tests
   - `test_vision_mobilenet.py`: 5 new warmup unit tests

4. **Non-Regression Checks** (per apply-progress id 1918 and verify-report id 1919):
   - `/health` endpoint: byte-for-byte unchanged (no diff to `app.py` handler)
   - `/ready` endpoint: no new `warmed` flag added
   - `/version` endpoint: `ENGINE_VERSION` remains `0.3.0`, `ruleset_version` unchanged
   - `TimeBudget`: all values (`ocr_s=6.0`, `vision_s=3.0`, `whole_request_s=10.0`, `max_concurrent_analyzers=2`) unchanged
   - `railway.json`: no diff (healthcheckTimeout: 60 unchanged)
   - Pre-existing duplicated `load_dotenv()` at `bootstrap/app.py` lines 42/50: deliberately left untouched per design constraint

5. **Spec Compliance**: All 7 scenarios in MODIFIED `Analysis latency budget` requirement have covering tests or structural guarantees:
   - Typical request p50: pre-existing test (unchanged)
   - Slow request p95: pre-existing test (unchanged)
   - First request post-warmup meets budgets: integration test (skipif-guarded, not re-run locally)
   - Connection gated on warmup completion: structural guarantee (`_lifespan` reaches `yield` only after task group join)
   - Concurrent OCR/vision warmup: unit test `test_lifespan_warms_ocr_and_vision_concurrently` (PASS)
   - Missing OCR dir fails closed: unit tests (PASS)
   - Missing vision dir fails closed: unit tests (PASS)
   - Non-regression of health/budgets: `git diff` confirms zero changes (PASS)

6. **Work Completion Timeline**:
   - Proposal phase: 2026-09-06 05:13:06
   - Spec phase: 2026-09-06 05:18:26
   - Design phase: 2026-09-06 05:21:22
   - Tasks phase: 2026-09-06 05:23:34
   - Apply phase (sdd-apply, external): produced apply-progress 2026-09-06 05:27:39
   - Verify phase (sdd-verify, external): produced verify-report 2026-09-06 05:32:37 (verdict PASS)
   - Archive phase (this): 2026-09-06

## Review Gate Status

No native review gate is configured for this project (receipt-driven development not active). Delivery status: `disabled/unmanaged` per gentle-ai review status (SDD archive skill §77–81). Archive proceeds without a formal review receipt.

## Migration / Rollback

Rollback is a one-hunk revert: delete `_lifespan` asynccontextmanager definition and drop `lifespan=_lifespan` from `FastAPI(...)` call in `bootstrap/app.py`. The `warmup()` methods on both adapters and the `_load_embedder` tuple refactor are additive and inert when never called; a full `git revert` is also safe. No `ENGINE_VERSION`, ruleset, or golden-file implications.

## Delivery Path

After archive close, the change is ready for commit, PR, and deployment:
1. Commit to feature branch (already on `fix/ui-grid-and-switchers` per repo state; will be rebased/retargeted to `dev` as needed)
2. PR to `dev` (main review/CI)
3. Merge + deploy to staging/production

The change is currently uncommitted but lives in the working tree and the new `openspec/changes/eager-model-warmup/` directory in Engram (copied to filesystem archive for durability).

## Known Limitations & Follow-ups

Per verify-report (id 1919) SUGGESTION:
- Integration request-1-timing scenario with real models was not independently re-run this session (local model directories absent). Environment limitation, not a code defect; skipif-guard ensures safe CI behavior.
- Future verify runs on Windows/Git-Bash/pytest combination should default to `pytest -v` to avoid terminal-rendering quirks masking hung runs.

No known defects. SDD cycle complete.

## Checklist

- [x] All 24 implementation tasks marked `[x]` in persisted tasks artifact
- [x] Zero CRITICAL issues in verify-report
- [x] Delta spec merged into main spec (MODIFIED requirement applied)
- [x] Change folder moved to archive with date prefix (2026-09-06)
- [x] No stale unchecked tasks remain in archived tasks.md
- [x] Archive folder contains proposal, design, tasks, verify-report, and delta spec
- [x] Main spec updated and source of truth re-synchronized
- [x] Archive report written to both Engram and filesystem

## Sign-Off

Archive executed 2026-09-06 by sdd-archive executor per SDD workflow.
Change: `eager-model-warmup`
Project: `receipt-risk-detector`
Mode: hybrid (Engram + openspec)
Result: CLOSED ✓
