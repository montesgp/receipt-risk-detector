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

---

## Final Re-verification (post-live-deployment)

Context: This change is no longer docs-only. Since the last verify pass, a real git repository was initialized, pushed to github.com/montesgp/receipt-risk-detector, live GitHub/Railway mutations (L1-L9) were executed, and a follow-up Dockerfile plus /health scaffold was added and deployed to fix a real Railway build failure. This section independently re-verifies all of it rather than trusting the narrative.

### 1. Git history

Confirmed via git log --oneline dev and git log --oneline main:

- dev:  fe0504b fix(deploy): build Dockerfile from repo root, not apps/api
- dev:  42bcec8 feat(bootstrap): add minimal Dockerfile and /health endpoint
- dev:  20c8857 docs: record wiki publish (L8) and Railway project creation (L9 partial)
- dev:  25552f1 docs: record live GitHub setup completion (L1-L7) and wiki blocker (L8)
- dev:  4f1ea15 chore: initial repository scaffold
- main: 4f1ea15 chore: initial repository scaffold

Matches the reported narrative exactly: main still holds only the initial scaffold commit (correct, since main is protected and PR-only per D2); dev carries the 4 follow-up commits. No unexplained commits, no rewritten history. COMPLIANT.

### 2. Both CRITICAL spec-text fixes re-confirmed present

Finding 1 (labels.yml to .github/labels.json): specs/repository-governance/spec.md now reads: "The system MUST commit a single .github/labels.json manifest ... plus a .github/labels.sh bootstrap script that upserts them via the gh CLI." The scenario also uses .github/labels.json verbatim. proposal.md's risk table was also grepped: labels.json is present, labels.yml is absent (0 matches). RESOLVED.

Finding 2 (deploy workflow to Railway native integration): specs/continuous-delivery/spec.md's Railway Deploy Configuration requirement now reads: "relying on Railway's native GitHub integration (branch-based auto-deploy) rather than a custom GitHub Actions deploy workflow ... (Decision D7 revised by Design A1, ADR 0001)." Both scenarios now read "GIVEN railway.json and Railway's native GitHub integration configured post-linkage" instead of referencing a nonexistent deploy.yml. RESOLVED.

Both prior CRITICAL findings are genuinely closed at the spec-text level, not just described as closed.

### 3. Dockerfile, bootstrap app.py, and railway.json wiring - independently re-verified

- Dockerfile path: apps/api/Dockerfile exists; railway.json's build.dockerfilePath is "apps/api/Dockerfile". MATCH.
- ASGI entrypoint: Dockerfile CMD invokes receipt_risk.bootstrap.app:app; app.py's module receipt_risk/bootstrap/app.py exports app; railway.json's deploy.startCommand is "uvicorn receipt_risk.bootstrap.app:app --host 0.0.0.0 --port ${PORT}". Dockerfile's CMD is the image default; Railway's startCommand overrides it at runtime with the injected PORT, both point at the same module:attr. MATCH.
- Healthcheck: app.py exposes GET /health returning {"status": "ok"}; railway.json's deploy.healthcheckPath is "/health". MATCH.
- Build context: the Dockerfile's own comment documents that the build context is the repo root, not apps/api, and all COPY paths are root-relative (apps/api/pyproject.toml, apps/api/src); railway.json no longer has a dockerContext field (correctly removed per the documented Railway schema constraint). MATCH.

Re-ran locally in apps/api:
- uv run ruff check . -> All checks passed!, exit 0
- uv run ruff format --check . -> 12 files already formatted, exit 0
- uv run pytest -> 1 passed in 0.01s, exit 0

The ruff-formatted file count grew from 11 (prior verify pass) to 12, consistent with the addition of bootstrap/app.py.

### 4. Independent Docker build and run (not trusted from narrative)

Ran docker build -f apps/api/Dockerfile -t rr-verify:test . from the repo root directly in this verify session:
- Build completed successfully, exit 0, all 6 build stages resolved correctly against the documented root build context.
- Ran the resulting image (docker run -d -p 18000:8000 rr-verify:test) and called curl http://localhost:18000/health after startup.
- Result: {"status":"ok"}, HTTP 200; container logs show "Uvicorn running on http://0.0.0.0:8000" followed by the actual "GET /health HTTP/1.1" 200 OK request line.
- Container and image were stopped and removed after the check, leaving no residue in the local Docker environment.

This independently reproduces the same result the user reported from the live Railway staging deploy (receipt-risk-detector-staging.up.railway.app/health returning {"status":"ok"}), confirming the fix is real rather than a one-off environmental fluke. COMPLIANT.

### 5. Layering rule check on bootstrap/app.py's FastAPI import

apps/api/pyproject.toml's [tool.ruff.lint.per-file-ignores] section explicitly lists:
- "src/receipt_risk/adapters/**" = ["TID251"]
- "src/receipt_risk/bootstrap/**" = ["TID251"]
- "tests/**" = ["TID251"]

bootstrap/** is explicitly exempted from TID251 (the banned-api rule blocking fastapi/starlette/etc. in domain/application). bootstrap/app.py's "from fastapi import FastAPI" therefore does not violate the layering rule - it is the one designed exception, matching the module's own docstring, which states it is the only place allowed to import both the framework and the application/domain layers directly. The independently re-run ruff check . (all-clean, exit 0) confirms this holds in practice, not only on paper. COMPLIANT.

### 6. tasks.md L1-L9 accuracy vs. observable reality

- L1-L2 (git init, commit 4f1ea15, public repo created, main pushed): git log shows 4f1ea15 as root commit on both branches; repo is reachable and was used as the basis of this verify session. MATCHES.
- L3-L4 (dev created/pushed, set default; repo settings applied): dev branch exists locally with 4 additional commits ahead of main, consistent with dev-as-default workflow. Protection/API-level settings were not independently re-queried via gh api in this pass (same acceptable limitation flagged in the prior verify pass; unverifiable from local git alone without live GitHub API calls).
- L5-L8 (labels synced, branch protection applied, 6 issues created with status:approved on #1, wiki pages pushed): not re-queried live against the GitHub API in this pass. .github/labels.json and labels.sh remain present and internally consistent; bootstrap/app.py's docstring cites "issues #1 and #2" consistent with the claimed issue numbering. No contradicting evidence found, but also not independently re-confirmed live in this session.
- L9 (marked [~], partial): tasks.md itself marks this partial, not done, correctly reflecting that production environment linkage is still pending on the user's side rather than overclaiming completion. MATCHES.
- New Dockerfile/health fix and the three documented bugs: independently reproduced end-to-end in section 4 above via local docker build and docker run, including hitting the /health endpoint successfully. MATCHES.

No task in tasks.md claims a live mutation that contradicts available evidence, and the L9 partial marking is honest rather than inflated. No overclaiming found.

### 7. No unexpected business logic introduced

Every .py file under apps/api/src/receipt_risk/ was read directly. All __init__.py files remain one-line docstrings. The only executable code anywhere is bootstrap/app.py's FastAPI() app object and its single /health route. No routes, schemas, or logic exist yet for receipt-analysis, public-api-contract, api-rate-limiting, data-retention, ui-localization-and-theming, or architecture-documentation - those remain tracked only as GitHub issues, exactly as designed. COMPLIANT.

### 8. Secrets and credentials scan

Searched the full commit history (git log --all -p) for common secret patterns: API key, secret, password, token, PEM private-key headers, AWS access-key prefix. All matches were false positives: references to the domain concept "token bucket" (rate-limiting design docs), "access token" (documentation stating the MVP has none), and the label filename labels.json. No literal secret value, credential, or private key was found anywhere in history. COMPLIANT.

### Updated Issues

No new CRITICAL or WARNING issues found in this pass. Both previously open CRITICAL findings are RESOLVED (see section 2 above).

#### SUGGESTION (new)

2. L5-L8 in tasks.md (label sync, branch protection, issue creation, wiki publish) were not re-queried live against the GitHub API in this final verify pass - only L1-L4 (via git log) and the new Dockerfile/health work (via independent Docker build) were re-confirmed with fresh evidence in this session. This is an acceptable scope boundary for a verify agent without live GitHub write/read credentials, not a defect, but a future audit could re-run gh api read-backs against L5-L8 for full independent confirmation.

### Final Verdict

PASS. Both previously blocking CRITICAL findings are resolved. All local tests and lint pass on independent re-run. The Dockerfile/app.py/railway.json wiring was independently rebuilt, run, and hit with curl, reproducing the reported live Railway result. No secrets were committed. No business-logic scope creep occurred. tasks.md accurately reflects reality, including the honest [~] partial marking for L9.

This change is ready to archive.
