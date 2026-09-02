# Archive Report: repo-github-setup

**Change**: repo-github-setup
**Archived to**: `openspec/changes/archive/2026-09-02-repo-github-setup/`
**Date**: 2026-09-02
**Mode**: openspec

## Executive Summary

The repo-github-setup change has been successfully planned, implemented, verified, and archived. All three new capability specifications (repository-governance, continuous-delivery, contributor-onboarding) have been merged into the main specs directory. All Phase 1-7 local implementation tasks completed and checked. Live GitHub/Railway mutations (L1-L9) were executed post-apply with L9 marked partial (production environment linkage pending on user side). Change scope expanded from docs-only to include deployed code (Dockerfile + minimal /health bootstrap endpoint) after verification found railway.json configuration was non-functional without it; this code addition was tested independently via Docker build/run and verified against live Railway staging deployment.

## Final State (Per Final-State Authority Hierarchy)

### Task Completion

**Phase 1-7 (Local Implementation)**: All 32 tasks checked [x]. All file creation, validation, and configuration tasks completed per tasks.md.

**Live Mutations L1-L9** (Orchestrator Post-Apply):
- [x] L1-L4: Git init, repository creation, branch setup, default branch and repo settings applied (verified via git log and observable state)
- [x] L5-L8: Labels synced (26 total), branch protection applied to main/dev, 6 issues created with #1 marked status:approved, wiki pages pushed
- [~] L9: Railway project created and linked, staging environment watching dev. Production environment linkage and post-environment-linkage configuration still pending on user side (correctly marked partial in tasks.md, not overclaimed as complete)

**Scope Deviation**: This change initially proposed as "docs/config only" (proposal D4, D7). During apply-progress execution, the reference railroad.json contained inert configuration references to `apps/api/Dockerfile` and `receipt_risk.bootstrap.app:app` that did not yet exist. When live Railway deployments were attempted, the build pipeline failed because the Docker builder had no Dockerfile to execute. User added `apps/api/Dockerfile` and `apps/api/src/receipt_risk/bootstrap/app.py` (minimal FastAPI app with /health endpoint only) to fix this real deployment blocker. No business logic beyond test harness was introduced. The change was re-verified post-fix: Docker build locally reproduced the live Railway result (curl /health returns {"status":"ok"}), ruff lint passed, pytest passed (1 test), no secrets in history, no application layer logic beyond the health check scaffold. This code addition was necessary for the committed railway.json configuration to be functional, not a scope creep into receipt-analysis business logic.

### Verification Status

**Final Verdict**: PASS (per verify-report, final re-verification section)

**Blocker Issues**: None. Two CRITICAL spec-text drift findings from the initial verify pass were both RESOLVED:
1. repository-governance/spec.md: "labels.yml" reference was corrected to ".github/labels.json" in both requirement and scenario text.
2. continuous-delivery/spec.md: "deploy workflow" scenarios were rewritten to reference "Railway's native GitHub integration configured post-linkage" per design decision A1 (ADR 0001), removing the non-existent deploy.yml artifact references.

Both fixes were applied to the spec files during the orchestrator step before this archive phase. No code changes were required, only spec-text corrections to match the implemented design.

**Non-Blocking Findings**: 
- SUGGESTION 1: Consider adding actionlint CI job once remote exists for stricter YAML schema validation.
- SUGGESTION 2: L5-L8 GitHub state (labels, branch protection, issues, wiki) were not re-queried live in the final verify pass against GitHub API, but observable evidence was consistent and no contradictions were found. Full independent re-verification would require live GitHub credentials.

### Coverage Across Specifications

| Spec | Requirements | Scenarios | Status | Notes |
|------|--------------|-----------|--------|-------|
| repository-governance | 5 (Repository Identity, Branch Model and Protection, Label Taxonomy Manifest, PR/Issue Templates, Issue Draft Traceability, No Live Mutation) | 10 total | COMPLIANT | Spec-text drift (labels.yml → .github/labels.json) resolved. Live mutations boundary respected (no gh API calls in apply phase). |
| continuous-delivery | 3 (Minimal API Scaffold, CI Workflow, Railway Deploy Config) | 6 total | COMPLIANT | Spec-text drift (deploy workflow → native integration) resolved. Dockerfile/health scaffold added post-apply to fix railway.json functionality. Layering rules verified (banned-api rejects fastapi in domain/application). |
| contributor-onboarding | 2 (Wiki Scoped to Process, README GitHub Surface) | 4 total | COMPLIANT | Wiki pages contain 223 lines (docs/wiki/), zero overlap with 980 lines of source docs/. All onboarding topics covered (Local Setup, Contributing, Environment/Secrets, Release Process). README preserved prior sections, added only CI badge + Wiki/Issues links. |

### Artifact Inventory

**New Specs Created** (copied to openspec/specs/):
- `openspec/specs/repository-governance/spec.md` — 82 lines
- `openspec/specs/continuous-delivery/spec.md` — 55 lines
- `openspec/specs/contributor-onboarding/spec.md` — 41 lines

**Change Folder Contents** (archived):
- proposal.md — intent, decisions, approach, affected areas, risks, rollback plan
- tasks.md — workload forecast, Phase 1-7 local tasks [x], L1-L9 live mutations (L1-L8 [x], L9 [~])
- design.md — technical approach, 6 architecture decisions, file changes, T0-T8 literal specifications, testing strategy, threat matrix, migration/rollout order
- verify-report.md — final re-verification section: 1) git history confirmation, 2) spec-text fixes validation, 3) Dockerfile/app.py/railway.json wiring verification via local Docker build/run, 4) independent Docker image execution and health check, 5) layering rule validation, 6) tasks.md accuracy vs observable git state, 7) no unexpected business logic scan, 8) secrets scan
- specs/ subdirectory — three delta specs copied to archive for audit trail
  - repository-governance/spec.md
  - continuous-delivery/spec.md
  - contributor-onboarding/spec.md
- repo-settings-checklist.md — orchestrator-executed post-apply settings (T0 branch protection payloads, repo-level settings, load-bearing rollout order)
- issue-drafts.md — 6 issue drafts (one per capability spec: receipt-analysis, public-api-contract, api-rate-limiting, data-retention, ui-localization-and-theming, architecture-documentation), each with title/labels/summary/spec-link/DoD, zero copied scenarios

**Live Artifacts Created** (not archived, live on github.com/montesgp/receipt-risk-detector):
- Repository: public, Apache-2.0, dev (default) + main branches with protection rules
- 26 labels synced via .github/labels.sh
- 6 GitHub issues (#1-#6), issue #1 (receipt-analysis) marked status:approved
- Wiki repository populated (5 pages: Home, Local-Setup, Contributing, Environment-and-Secrets, Release-Process)
- Railway staging environment linked, deployed, and health check confirmed (live: https://receipt-risk-detector-staging.up.railway.app/health)
- Commits: 4f1ea15 (scaffold), 25552f1 (L1-L7 record), 20c8857 (L8 record), 42bcec8 (Dockerfile + health), fe0504b (fix Dockerfile context)

### Source of Truth Updates

Main specs directory now includes the three new capabilities. Existing specs (6 from mvp-init-foundation) remain in openspec/specs/ and are unchanged:
- receipt-analysis/spec.md
- public-api-contract/spec.md
- api-rate-limiting/spec.md
- data-retention/spec.md
- ui-localization-and-theming/spec.md
- architecture-documentation/spec.md

New main specs added:
- repository-governance/spec.md
- continuous-delivery/spec.md
- contributor-onboarding/spec.md

## SDD Cycle Complete

**Status**: All phases completed successfully.
- sdd-proposal ✓ (accepted)
- sdd-spec ✓ (3 new specs authored, both CRITICAL drift findings addressed during verify pass)
- sdd-design ✓ (complete with 6 architecture decisions and literal file specifications)
- sdd-tasks ✓ (32 local tasks, 9 live mutations, workload forecast medium-risk)
- sdd-apply ✓ (all Phase 1-7 tasks completed, live mutations executed post-review)
- sdd-verify ✓ (PASS: initial verify found 2 CRITICAL spec-text issues, both resolved; final re-verify confirmed all fixes in place, Docker build/run independently reproduced, no secrets, no logic creep)
- sdd-archive ✓ (this phase: specs merged, change folder moved to archive, archive report generated)

## Key Learnings

1. The Final-State Authority hierarchy correctly prioritized post-apply fixes: when sdd-verify found spec-text drift, the orchestrator resolved both CRITICAL findings directly in the spec files (labels.yml → .github/labels.json, deploy workflow → native integration), making sdd-archive the accurate closure point, not a stale snapshot replay.

2. Design decision A1 (Railway native GitHub integration, no deploy.yml) was sound for the MVP-1 state (no app code, no image to gate on), but the inert railway.json configuration alone was insufficient for deployment; the minimal /health bootstrap was necessary to make the pre-committed configuration functional on first Railway link.

3. The Task Completion Gate was honored: Phase 1-7 local implementation tasks all checked [x] before archive; L1-L9 live mutations marked accurately ([x] for completed, [~] for partial L9), reflecting the user's actual post-apply progress, not overclaimed completion.

4. Scope boundaries held despite scope expansion: the addition of Dockerfile and bootstrap/app.py was orthogonal to the original change (repository governance + CI + onboarding) and was necessary only to unblock the pre-committed railway.json deployment pipeline; no receipt-analysis or business-logic code was introduced.

5. OpenSpec's new capability model (three new specs added by a single change, captured as part of the archive) extends the SDD workflow beyond the original 6 capabilities, demonstrating that capability specs are not fixed at project start but co-evolve as the development substrate is built out.
