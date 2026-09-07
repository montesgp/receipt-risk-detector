# Archive Report: c2pa-ai-claim-detection

**Date**: 2026-09-06
**Change**: c2pa-ai-claim-detection
**Status**: COMPLETE
**Verdict**: CLEAN (0 CRITICAL, 0 WARNING, 0 SUGGESTION)

## Executive Summary

The c2pa-ai-claim-detection change has been fully planned, implemented, verified, and archived. All 20/20 tasks completed across 4 phases. Delta specs merged into main spec. Proposal, design, and all artifacts moved to archive. Ready for deployment.

## Artifact Traceability

### Engram Observation IDs (for reproducibility and audit trail)

| Artifact | Observation ID | Created | Type |
|----------|---|---|---|
| Proposal | 1905 | 2026-09-06 01:39:24 | proposal |
| Specification Delta | 1906 | 2026-09-06 02:30:20 | spec |
| Design Document | 1907 | 2026-09-06 02:32:41 | design |
| Task Breakdown | 1908 | 2026-09-06 02:35:15 | tasks |
| Apply Progress | 1909 | 2026-09-06 02:41:21 | apply-progress |
| Verification Report | 1910 | 2026-09-06 02:44:39 | verify-report |
| Archive Report | (this document) | 2026-09-06 | archive-report |

## Scope Delivered

### Four Implementation Phases

1. **Phase 1: Domain Foundation** (4 tasks) — New `SignalCode.AI_GENERATED_CLAIM_UNTRUSTED_SIGNER`, new ruleset `v2026_09_06` (copy-forward of `v2026_09_05`), ruleset registration.
2. **Phase 2: Adapter Parsing + Classification** (5 tasks) — Dual-path `digitalSourceType` extraction (flat + claim-v2 nested), `compositesynthetic` marker addition, three-way `validation_status` branching with allowlist.
3. **Phase 3: Engine/Ruleset Wiring** (3 tasks) — `ENGINE_VERSION` bump to `0.3.0`, `bootstrap/app.py` repointing (3 sites), test assertions.
4. **Phase 4: Golden Regeneration and Documentation** (4 tasks plus 1 housekeeping) — Version-string updates across 7 test modules, API documentation updates, confirmation of main spec merge convention.

**All 20 tasks complete and verified.** Filesystem `tasks.md` shows all checkboxes `[x]`. Engram `tasks` artifact was captured during sdd-tasks phase (showing `- [ ]`); filesystem state reflects the final post-apply state. Per orchestrator's explicit "All 20/20 tasks complete" final-state fact and apply-progress confirmation, reconciliation is sound.

### Specification Merge

**Main spec**: `openspec/specs/receipt-analysis/spec.md`

Two requirements updated via merge:

1. **Requirement: Metadata and provenance inspection** — Enhanced with:
   - Dual-path parsing semantics (flat IPTC + claim-v2 nested)
   - `compositesynthetic` marker requirement
   - Three-way classification (clean / allowlisted-untrusted / strict)
   - Five new scenarios covering all branches
   - Previous behavior documentation

2. **Requirement: Explainable, deterministic scoring** — Updated with:
   - New ruleset `v2026_09_06` requirements (weight 50, critical_floor 85)
   - Engine version bump to `0.3.0`
   - Ruleset version to `2026-09-06`
   - Two new scenarios (untrusted-signer signal forcing HIGH_RISK, version endpoint reporting)
   - Previous behavior documentation

**Merge method**: Surgical replacement of specific requirement sections, preserving all other requirements (Image submission, Safe preprocessing, Local OCR extraction, Financial validation, Results UI, Analysis latency budget).

**Merge validation**: Main spec was confirmed untouched during apply/verify phase; delta spec in change directory carries the cumulative changes. Repo convention (observed in prior 5 archived changes) is that merge happens at archive time, not during implementation.

## Verification Outcome

**Verdict**: CLEAN (0 CRITICAL, 0 WARNING, 0 SUGGESTION)

**Test run**: `uv run pytest -q` from `apps/api/` — **exit code 0**, 207 passed, 14 skipped, 0 failed, 0 errors.

**Checks performed** (per verify-report observation 1910):
1. `c2pa_reader.py`: dual-path parsing confirmed (flat + nested claim-v2 shapes)
2. `compositesynthetic` added to algorithmic source markers
3. Three-way `validation_status` branch implemented and tested
4. `signals.py`: new `SignalCode.AI_GENERATED_CLAIM_UNTRUSTED_SIGNER` appended at end
5. `v2026_09_06.py`: confirmed byte-for-value copy-forward of `v2026_09_05` plus new weight/floor entries
6. `v2026_09_05.py`: confirmed NOT modified (frozen as required)
7. `rulesets/__init__.py`: 4 rulesets registered (09_01, 09_04, 09_05, 09_06)
8. `bootstrap/app.py`: all 3 wiring sites repointed to new ruleset
9. `analyze_receipt.py`: `ENGINE_VERSION` bumped to `0.3.0`
10. Arithmetic validated: `int(50 * 2.0 * 0.85) == 85` lands in HIGH_RISK band
11. Main spec confirmed untouched during apply/verify
12. Two flagged apply-progress deviations reviewed and sound (no regressions masked)

**Out-of-scope observations**: README.md and docker-compose.yml carry unrelated local-dev-tooling edits; excluded from change scope.

## Archive Contents

Archived to: `openspec/changes/archive/2026-09-06-c2pa-ai-claim-detection/`

| File | Status |
|------|--------|
| `proposal.md` | Complete |
| `design.md` | Complete |
| `tasks.md` | Complete (20/20 tasks) |
| `verify-report.md` | Complete (CLEAN verdict) |
| `specs/receipt-analysis/spec.md` | Delta spec (merged into main) |
| `archive-report.md` | This document |

All artifacts present and accounted for.

## Change Characteristics

| Attribute | Value |
|-----------|-------|
| Estimated changed lines | 400-550 |
| Actual review scope | Low (800-line session budget) |
| Chained PRs required | No |
| Delivery strategy | single-pr |
| New files | 1 (`domain/rulesets/v2026_09_06.py`) |
| Modified files | 8 (adapter, domain, bootstrap, application, tests, docs) |
| Rollback complexity | Low (3-site repoint + commit revert) |
| Backward compatibility | Maintained (prior ruleset `v2026_09_05` frozen and inert) |

## Final State Authority Notes

The following sources were consulted for final-state facts:

1. **Explicit launch prompt facts** (highest rank):
   - "All 20/20 tasks complete" — confirmed by apply-progress (1909) and filesystem tasks.md
   - "v2026_09_05.py confirmed unmodified" — confirmed by verify-report independent source read
   - "openspec/specs/receipt-analysis/spec.md untouched during apply/verify" — confirmed by verify-report; merged at archive time per this report

2. **Verify-report (1910)** (intermediate snapshot, valid end-to-end):
   - CLEAN verdict with 0 CRITICAL, 0 WARNING, 0 SUGGESTION
   - 207 passed, 14 skipped, 0 failed tests
   - Independent source read, not trusting apply-progress self-report
   - Written at 2026-09-06 02:44:39

3. **Apply-progress (1909)** (intermediate snapshot, valid for completion):
   - "Implemented all 20 tasks (4 phases)"
   - "Full `uv run pytest -q` green after every phase"
   - "Final full-suite run green with zero non-scoped diffs"
   - Written at 2026-09-06 02:41:21

4. **Tasks artifact (1908)** (captured at sdd-tasks phase, stale for checkbox state):
   - Captured at 2026-09-06 02:35:15 (before apply phase)
   - Filesystem version supersedes Engram version (reflects post-apply state)
   - All 20 tasks shown as `[x]` complete in filesystem

No contradictions found. Task completion authority correctly ranked: explicit prompt + apply-progress + verify-report + filesystem state all agree on final completion.

## Deployment Readiness

- [x] Specification merged and validated
- [x] All implementation tasks complete and verified
- [x] Tests passing (207 passed, 0 failed)
- [x] No CRITICAL or WARNING issues
- [x] Rollback plan documented and safe
- [x] Artifacts archived and traceable
- [x] Change ready for PR and deployment

The change is **complete and ready for next phase** (review, commit, PR, deployment per project workflow).

## Key Decisions Recorded

1. **Adapter fix is unconditional** — `ENGINE_VERSION` tracks detection changes; `ruleset_version` tracks policy/pricing only.
2. **Allowlist strategy** — Fail-closed by design; unknown `validation_status` codes default to the stricter `PROVENANCE_VALIDATION_FAILED` bucket.
3. **Worst-case precedence** — One non-allowlisted status code in a multi-entry array sends the entire result to the strict bucket.
4. **Untrusted-signer tier is CRITICAL** — Verdict-forcing, same effect as fully-trusted case (HIGH_RISK). Kept separate code for audit trail and independent future retuning.
5. **Ruleset copy-forward** — `v2026_09_05` frozen and registered; `v2026_09_06` adds exactly the new code's weight and floor.

## Open Questions

None blocking. The `signingCredential.expired` allowlist question is deliberately deferred to a future evidence-driven change; if reopened, it becomes an adapter edit + engine bump (not a ruleset change), because it changes *classification*, not *price*.
