# Verification Report: repo-github-setup

**Mode**: Full artifact set (proposal, specs x3, design, tasks, apply-progress)
**Verdict**: PASS WITH WARNINGS

## Completeness

| Phase | Status |
|---|---|
| Phase 1-7 (local/file tasks) | All [x] -- confirmed against tasks.md |
| Live-mutation L1-L9 | All unchecked [ ] -- boundary intact, no .git exists, no mcp__github__* calls made |

## Runtime Evidence (re-executed independently, not trusted from apply-progress)

| Command | Result |
|---|---|
| cd apps/api && uv run pytest | 1 passed in 0.01s, exit 0 |
| uv run ruff check . | All checks passed!, exit 0 |
| uv run ruff format --check . | 11 files already formatted, exit 0 |
| Layering proof: temporarily appended import fastapi to domain/__init__.py, re-ran ruff check . | TID251 fastapi is banned + F401 unused import -- 2 errors, exit 1. Reverted the file afterward (single-line removal, file now identical to prior committed content). |
| .git directory check | Absent -- confirmed via ls -la .git returning No such file or directory |

Ruff banned-api (A6) is genuinely enforced, not just documented -- verified by causing and observing the failure directly rather than trusting the apply report.

## Spec Compliance Matrix

### repository-governance

| Requirement | Evidence | Status |
|---|---|---|
| Repository Identity (D1) | repo-settings-checklist.md states public / montesgp/receipt-risk-detector / Apache-2.0 | COMPLIANT |
| Branch Model and Protection (D2) | repo-settings-checklist.md T0 payloads for dev (no required checks, force-push/delete blocked) and main (5 required checks, PR-only) | COMPLIANT (manual verification only -- accepted design risk, unverifiable pre-remote) |
| Label Taxonomy Manifest (D5) | Spec text says labels.yml; actual committed file is .github/labels.json (26 labels, matches design T4 exactly, status:approved present, all 6 type:* present) | CRITICAL (spec-text drift) -- functionally correct and consistent with design.md, pr-validation.yml, and issue-drafts.md, but the spec's own scenario references a filename that does not match the shipped file. This is a spec-authoring defect from sdd-spec, not an apply error -- design.md always specified .json. |
| PR/Issue Templates + Validation Gates (D5) | pr-validation.yml has all 4 jobs with exact contract names (Check Issue Reference, Check Issue Has status:approved, Check PR Has type:* Label, Check Source Branch); PR body and labels read via env: / context.payload, never string-interpolated | COMPLIANT |
| Issue Draft Traceability (D6) | issue-drafts.md has exactly 6 drafts, one per capability spec, title+summary+link+DoD only, zero copied GWT text (spot-checked full file) | COMPLIANT |
| No Live Mutation From Apply (D4) | No .git, no mcp__github__* calls per apply-progress and independent confirmation of directory state | COMPLIANT |

### continuous-delivery

| Requirement | Evidence | Status |
|---|---|---|
| Minimal API Scaffold (D6) | apps/api/src/receipt_risk/{domain,application,adapters/{api,metadata,provenance,ocr},bootstrap}/__init__.py, all empty plus one-line docstring; matches design T6 skeleton exactly; layering re-verified live (see Runtime Evidence) | COMPLIANT |
| One test passes via uv | uv run pytest -> 1 passed | COMPLIANT |
| CI Workflow Runs Real Commands (D5/D6) | ci.yml job API Lint and Test: ruff check, ruff format --check, pytest, working-directory apps/api; no apps/web job (explicit, documented deferral, matches the stated decision) | COMPLIANT |
| Railway Deploy Configuration (D7, ADR 0001) | railway.json matches design T5 exactly (DOCKERFILE builder, inert paths). Spec requires "a deploy workflow mapping dev to staging, main to production"; design A1 explicitly supersedes this (no deploy.yml, native GitHub integration, mapping done manually via Railway environments -- documented in docs/wiki/Environment-and-Secrets.md and Release-Process.md). No deploy workflow file exists, and railway.json itself contains no branch/environment mapping. | CRITICAL (spec-text drift) -- design.md rationale for A1 is sound (no app image or secret to gate a CLI workflow on yet) and apply correctly followed the design, but the spec's own two scenarios ("Dev branch maps to staging" / "Main branch maps to production", both phrased "GIVEN railway.json and the deploy workflow") reference an artifact that was deliberately never built. As currently worded, a reader of only the spec would flag this as unimplemented. |

### contributor-onboarding

| Requirement | Evidence | Status |
|---|---|---|
| Wiki Scoped to Process/Onboarding (D3) | docs/wiki/*.md total 223 lines vs. 980 lines in docs/{PRD,ARCHITECTURE,DESIGN}.md; grepped wiki pages for receipt-domain terms (hash/EXIF/OCR/confidence/risk score/GWT) -- zero matches; every architecture/design reference is an absolute GitHub link, never inline content | COMPLIANT |
| Onboarding topics covered | Home, Local-Setup, Contributing, Environment-and-Secrets, Release-Process all present | COMPLIANT |
| README GitHub Surface Additions Only (D8) | README retains all prior sections (Product principle, MVP 1, Stack, Architecture, API example, Local dev target, Repository layout, Docs list, Privacy, Open source, Disclaimer); only additions are the CI badge and Wiki/Issues links | COMPLIANT |

## Design Coherence

- A1 (Railway native integration, no deploy.yml) -- implemented as designed, but see CRITICAL finding above: the spec was never updated to match this design decision.
- A2 (Check Source Branch job, not a branch-protection field) -- implemented verbatim in pr-validation.yml.
- A3 (labels.sh plus gh label create --force) -- implemented verbatim; see CRITICAL finding on filename mismatch with spec text.
- A4 (required-check names frozen as job name: strings) -- pr-validation.yml job names match repo-settings-checklist.md's main protection contexts array verbatim.
- A5/A6 (src-layout plus hatchling plus uv, ruff banned-api layering) -- implemented and independently re-verified live.

## Non-Goals Verified

- No .git directory created.
- No live GitHub/Railway API calls made (checked apply-progress memory and directory state; no mcp__github__* tool usage recorded).
- No application business logic beyond test_true_is_true -- every __init__.py under apps/api/src/receipt_risk/ is a one-line docstring only.

## Issues

### CRITICAL

1. repository-governance/spec.md's "Label Taxonomy Manifest" requirement and scenario reference labels.yml, but the actually-committed, design-mandated, functionally-correct file is .github/labels.json. Recommend a small spec-text correction (change labels.yml to .github/labels.json in the requirement and scenario) before archive -- no code/config change needed.
2. continuous-delivery/spec.md's "Railway Deploy Configuration" requirement and its two branch-mapping scenarios require "a deploy workflow," which design decision A1 explicitly and correctly supersedes (no deploy.yml; native GitHub integration; mapping is a manual Railway-dashboard step documented in docs/wiki/). Recommend updating the spec requirement/scenarios to describe native-integration plus manual-environment-linkage instead of a committed deploy workflow, so the spec accurately reflects the accepted design decision.

Both CRITICAL items are spec-authoring drift from sdd-spec/sdd-design (design.md already reflects the final decision), not implementation defects in sdd-apply. No source file needs to change -- only the two spec.md requirement texts.

### WARNING

None beyond the above.

### SUGGESTION

1. Consider adding an actionlint step (or CI job) once the remote exists, since local actionlint was unavailable during this verification pass -- YAML validity was confirmed via yaml.safe_load() only, not schema/semantic linting of Actions-specific syntax.

## Key Learnings

1. sdd-apply's ruff banned-api layering enforcement was independently re-verified by injecting and then reverting a fastapi import into domain/__init__.py, confirming TID251 fires as designed.
2. Two spec-text/design mismatches were found: repository-governance/spec.md says labels.yml where the design and implementation correctly use .github/labels.json, and continuous-delivery/spec.md requires a "deploy workflow" that design decision A1 deliberately removed in favor of Railway's native GitHub integration.
3. Both mismatches originate in spec authoring, not in sdd-apply, since design.md already reflects the final, implemented decisions in both cases.
4. Wiki anti-duplication was confirmed quantitatively: docs/wiki/*.md total 223 lines against 980 lines of source docs/{PRD,ARCHITECTURE,DESIGN}.md, and a targeted grep for receipt-domain terminology found zero matches in the wiki.
5. The Phase 1-7 / Live-mutation L1-L9 boundary in tasks.md is intact: all local file tasks are checked, and all nine live-mutation tasks remain unchecked with no .git directory or GitHub API calls present.
