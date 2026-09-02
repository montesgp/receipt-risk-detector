# Tasks: GitHub Repository, Gitflow Enforcement, CI/CD and Issue Bootstrap

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~850 (all-new files; largest: pr-validation.yml ~113, issue-drafts.md ~120, ci.yml ~49, pyproject.toml ~55, wiki pages ~240 combined) |
| 400-line budget risk | Medium (evaluated against the project's 800-line budget; ~6% over) |
| Chained PRs recommended | No |
| Suggested split | Single PR, `size:exception` |
| Delivery strategy | single-pr |
| Chain strategy | size-exception |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Medium

`size:exception` is pre-accepted per project convention (same pattern used by the prior change). No further chaining decision is needed before `sdd-apply` runs. All work below is one PR; live GitHub/Railway mutations run separately, after human review, outside `sdd-apply`.

### Work Unit

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | All local files: `.github/`, `apps/api`, `railway.json`, `docs/wiki/`, issue drafts, README/CONTRIBUTING updates | PR 1 (`size:exception`) | `cd apps/api && uv run pytest` | N/A — workflows unverifiable until a remote exists (accepted design risk); validated on first real PR | `git` revert of the single commit/PR; no live state exists yet |

---

## Local/file tasks (sdd-apply)

### Phase 1: Root support files
- [x] 1.1 Create `.gitignore` (Python/uv/node/OS ignores)
- [x] 1.2 Create `openspec/changes/repo-github-setup/repo-settings-checklist.md`: states visibility `public`, name `montesgp/receipt-risk-detector`, license Apache-2.0 (D1), plus the T0 `dev`/`main` protection JSON payloads and repo-level settings payload, for the orchestrator to apply later

### Phase 2: GitHub templates & workflows (repository-governance)
- [x] 2.1 Create `.github/PULL_REQUEST_TEMPLATE.md` per design T1
- [x] 2.2 Create `.github/ISSUE_TEMPLATE/config.yml` (`blank_issues_enabled: false`)
- [x] 2.3 Create `.github/ISSUE_TEMPLATE/bug_report.md` (Markdown, not YAML form)
- [x] 2.4 Create `.github/ISSUE_TEMPLATE/feature_request.md` (Markdown, not YAML form)
- [x] 2.5 Create `.github/labels.json` per design T4 (30 labels: `type:*`, `status:*`, `capability:*`, `area:*`, `mvp1`, `roadmap`, `good first issue`, `size:exception`)
- [x] 2.6 Create `.github/labels.sh` (idempotent `gh label create --force` applier reading `labels.json`)
- [x] 2.7 Create `.github/workflows/pr-validation.yml` per design T2 — 4 jobs: `Check Issue Reference`, `Check Issue Has status:approved`, `Check PR Has type:* Label`, `Check Source Branch`; untrusted `PR_BODY` passed via `env:`, never interpolated
- [x] 2.8 Create `.github/workflows/ci.yml` per design T3 — job `API Lint and Test` (ruff check, ruff format --check, pytest) in `apps/api`

### Phase 3: apps/api scaffold (continuous-delivery)
- [x] 3.1 Create `apps/api/pyproject.toml` per design T6 (hatchling, src-layout, `flake8-tidy-imports` banned-api for fastapi/starlette/cv2/paddleocr/PIL in domain/application)
- [x] 3.2 Create `apps/api/README.md`
- [x] 3.3 Create empty `__init__.py` skeleton (one-line docstring each) under `src/receipt_risk/{domain,application,adapters/{api,metadata,provenance,ocr},bootstrap}`
- [x] 3.4 RED/GREEN: create `apps/api/tests/test_placeholder.py::test_true_is_true` — trivially green scaffold-harness proof; no domain behavior exists yet, so no prior RED step applies
- [x] 3.5 Verify: `cd apps/api && uv sync --all-extras --dev && uv run pytest` — exactly one test passes
- [x] 3.6 Verify: `uv run ruff check .` and `uv run ruff format --check .` pass; confirm a manual `import fastapi` added temporarily to `domain/__init__.py` is rejected by the banned-api rule, then remove it (layering proof, not a committed change)

### Phase 4: Railway config (continuous-delivery)
- [x] 4.1 Create `railway.json` per design T5 (inert: references `apps/api/Dockerfile` and `receipt_risk.bootstrap.app:app`, neither exists yet — accepted per user decision)

### Phase 5: Wiki source pages (contributor-onboarding)
- [x] 5.1 Create `docs/wiki/Home.md`
- [x] 5.2 Create `docs/wiki/Local-Setup.md`
- [x] 5.3 Create `docs/wiki/Contributing.md`
- [x] 5.4 Create `docs/wiki/Environment-and-Secrets.md` (includes one-time maintainer bootstrap runbook: labels, protection, Railway, wiki push)
- [x] 5.5 Create `docs/wiki/Release-Process.md`
- [x] 5.6 Verify: grep all `docs/wiki/*.md` for copied PRD/ARCHITECTURE/DESIGN section text — none found, only links to `docs/`

### Phase 6: Issue drafts and doc updates
- [x] 6.1 Create `openspec/changes/repo-github-setup/issue-drafts.md` — exactly 6 drafts (one per capability spec: `receipt-analysis`, `public-api-contract`, `api-rate-limiting`, `data-retention`, `ui-localization-and-theming`, `architecture-documentation`) per design T8 template; title/labels/summary/spec-link/DoD only, no copied Given/When/Then
- [x] 6.2 Modify `README.md`: add CI badge, Wiki link, Issues link only — no other section changes
- [x] 6.3 Modify `CONTRIBUTING.md`: point to `.github/PULL_REQUEST_TEMPLATE.md`, `.github/labels.json`, and the T0 protection rules

### Phase 7: Local verification (no live calls)
- [x] 7.1 Confirm zero `mcp__github__*` or Railway API calls were made during this phase
- [x] 7.2 Diff `README.md` before/after: only CI badge + Wiki link + Issues link added, all prior sections intact
- [x] 7.3 Manually review `pr-validation.yml` / `ci.yml` YAML for syntax validity (`actionlint` if available, else visual review) — real CI validation deferred to first live PR (accepted design risk)

---

## Live GitHub/Railway mutations (orchestrator-executed, human-confirmed)

**Only after human review of the PR from the phase above.** Not assigned to `sdd-apply` — no `mcp__github__*` tools are available there. Order below is load-bearing (design "Migration / Rollout"): applying protection before branches exist returns 404.

- [ ] L1. **Init and first push to `main`**: `git init`, `git add -A`, initial commit (conventional, e.g. `chore: initial repository scaffold`). Manual `git`/`gh` CLI — no MCP git-init tool exists.
- [ ] L2. **Create the GitHub repository**: `mcp__github__create_repository` (name `receipt-risk-detector`, owner `montesgp`, `public`, Apache-2.0) — or manual `gh repo create` if tool scope is restricted. Then `git remote add origin ...` and `git push -u origin main`.
- [ ] L3. **Create `dev` branch**: `mcp__github__create_branch` (base `main`) — or `git checkout -b dev && git push -u origin dev`.
- [ ] L4. **Set `dev` as default branch + repo-level settings**: `mcp__github__update_repository` (or direct `PATCH /repos/{owner}/{repo}`) applying `default_branch: dev`, `has_issues: true`, `has_wiki: true`, `allow_merge_commit: false`, `allow_squash_merge: true`, `allow_rebase_merge: true`, `allow_auto_merge: true`, `delete_branch_on_merge: true` per design T0.
- [ ] L5. **Bootstrap labels**: manual `gh` CLI — run `.github/labels.sh montesgp/receipt-risk-detector` (requires `gh` admin auth + `jq`). No `mcp__github__*` label-creation tool exists (flagged risk A3); must run before L6 needs `type:*` labels.
- [ ] L6. **Apply branch protection, `main` then `dev`**: `mcp__github__update_branch_protection` (or `PUT /repos/{owner}/{repo}/branches/main/protection`) with the T0 `main` payload (required checks, PR-only, linear history), then the same for `dev` with the T0 `dev` payload (no required checks, force-push/deletion blocked).
- [ ] L7. **Publish issues**: `mcp__github__create_issue` once per draft in `issue-drafts.md` (6 issues) with the specified `type:*`/`capability:*`/`area:*`/`mvp1`/`status:needs-triage` labels; then apply `status:approved` to the first issue selected to unblock work (`mcp__github__update_issue` or label add).
- [ ] L8. **Publish wiki pages**: manual — clone `https://github.com/montesgp/receipt-risk-detector.wiki.git`, copy `docs/wiki/*.md` in as page names, commit, push. No MCP wiki-publish tool exists.
- [ ] L9. **Railway linkage** (manual, out of design control): create the Railway project via the Railway UI, connect the GitHub repo, create `staging` (watches `dev`) and `production` (watches `main`) environments, set env vars, enable "wait for CI to pass."

## Key Learnings

1. Design.md places `git init`/first push inside its own rollout-order step, but the orchestrator's explicit instruction reclassifies all git-init and branch-creation actions as live mutations deferred outside `sdd-apply`, overriding that placement.
2. No `mcp__github__*` tool exists for label creation, so the design's `.github/labels.sh` + `gh` CLI script is the sanctioned workaround for live label bootstrap (design decision A3).
3. Branch protection payloads (T0) must be applied only after both `main` and `dev` exist and are pushed, because the GitHub API returns 404 on protection calls against branches that do not yet exist.
4. Estimated changed lines (~850) exceed the project's 800-line review budget slightly, but the pre-accepted `size:exception` delivery strategy removes the need for a further chaining decision before apply.
5. Issue templates must stay Markdown (`.md`), not YAML issue forms, because YAML forms route through `gh issue create --web` and block non-interactive publishing of the drafted issue bodies.
