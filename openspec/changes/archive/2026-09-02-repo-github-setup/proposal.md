# Proposal: GitHub Repository, Gitflow Enforcement, CI/CD and Issue Bootstrap

## Intent

The project is fully specified (6 archived capability specs in `openspec/specs/`) but has no `.git`, no remote, no `.github/`, no CI, and no tracked work items. `CONTRIBUTING.md` already commits to gitflow (D5) and issue granularity (D6) with zero enforcement. This change builds the delivery substrate so specified work becomes reviewable, trackable, and deployable.

## Decisions this proposal makes

| # | Decision |
|---|----------|
| D1 | Public repo `montesgp/receipt-risk-detector` (name user-confirmable). Apache-2.0 LICENSE and "open source portfolio piece" README already fit. |
| D2 | Branch protection: `main` strict (PR-only from `dev`, required status checks); `dev` allows maintainer direct push. Pragmatic solo default, user-adjustable. |
| D3 | Wiki holds only process/onboarding (local setup, contributing, env, release runbook) and **links** to `docs/`. Anti-duplication: no PRD/ARCHITECTURE/DESIGN copies — drift risk. |
| D4 | **Tooling boundary, not scope cut**: `sdd-apply` has no `mcp__github__*` tools, so it produces `issue-drafts.md` + a repo-settings checklist. Live repo/issue/label creation is a distinct orchestrator step after human review. |
| D5 | Adopt `branch-pr` fully: author `.github/workflows/pr-validation.yml`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/`, and the `status:approved` + `type:*` label taxonomy it requires. |
| D6 | Minimal `apps/api` uv scaffold (Python 3.12+, FastAPI/Pydantic, one passing test), respecting AGENTS.md layering. No business logic. |
| D7 | Railway: config only (`railway.json` + deploy workflow, `dev`→staging, `main`→production). Account/project linkage is a documented manual runbook step. |
| D8 | README: preserve current structure; add only CI badge, Wiki link, Issues link. |

## Scope

### In Scope
- `git init`, `.gitignore`, `dev`/`main` branch model, branch-protection checklist.
- `.github/`: PR template, issue templates, label taxonomy manifest, `pr-validation.yml`, `ci.yml`, `deploy.yml`.
- `apps/api` minimal uv scaffold + placeholder pytest.
- `openspec/changes/repo-github-setup/issue-drafts.md` — ~6 issues, one per capability spec (D6 of prior change).
- Wiki source pages under `docs/wiki/`; README GitHub-facing additions.

### Out of Scope
- Live GitHub repo/issue/label/wiki creation (orchestrator step after review).
- Railway account creation, project provisioning, secrets.
- Any application, OCR, or UI business logic.
- Modifying the 6 existing capability specs.

## Capabilities

### New Capabilities
- `repository-governance`: branch model, protection rules, label taxonomy, issue/PR templates, PR-validation gates.
- `continuous-delivery`: CI (lint/typecheck/test) and Railway deploy configuration per branch.
- `contributor-onboarding`: Wiki scope, anti-duplication policy, README GitHub surface.

### Modified Capabilities
- None. Existing specs are issue *sources*, not amended.

## Approach

1. `git init`; author `.gitignore`; establish `dev` from `main`.
2. Author `.github/` templates, labels manifest, and workflows satisfying `branch-pr`'s three checks.
3. Scaffold `apps/api` (uv, pytest) so CI runs real commands.
4. Author Railway deploy config + manual-linkage runbook.
5. Generate `issue-drafts.md` from the 6 capability specs.
6. Author `docs/wiki/` process pages; adjust README.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `.git`, `.gitignore` | New | Repo init, gitflow branches |
| `.github/` | New | Templates, labels, 3 workflows |
| `apps/api/` | New | uv scaffold, placeholder test |
| `railway.json` | New | Env mapping config |
| `docs/wiki/` | New | Process/onboarding pages |
| `README.md`, `CONTRIBUTING.md` | Modified | Badges, links, enforcement pointers |
| `openspec/changes/repo-github-setup/issue-drafts.md` | New | Reviewable issue content |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Change exceeds 400-line review budget | High | `sdd-tasks` must chain PRs (git+`.github` / scaffold+CI / deploy+wiki+issues) |
| Workflows unverifiable until remote exists | High | Accept; validate on first real PR, fix as follow-up |
| Label taxonomy drifts from `branch-pr` | Med | Commit a `.github/labels.json` manifest as the single source |
| Railway config wrong without a live project | Med | Config-only; runbook flags manual verification |
| Scaffold violates AGENTS.md layering | Low | Skeleton has no domain imports; CI adds an import-boundary check later |
| Repo name/visibility unconfirmed | Low | D1 flagged user-confirmable before creation |

## Rollback Plan

Nothing is published until the orchestrator step runs. Local rollback: delete `.git/`, `.github/`, `apps/`, `railway.json`, `docs/wiki/`, `openspec/changes/repo-github-setup/`, restore `README.md`/`CONTRIBUTING.md`. If the remote was already created: delete/archive the GitHub repo and close generated issues. No data, no consumers, no deploys.

## Dependencies

- GitHub account `montesgp`; `gh` CLI or GitHub MCP tools available to the orchestrator.
- Railway account (manual, post-change).
- `uv` for the API scaffold.

## Success Criteria

- [ ] Local repo has `dev` and `main` with a documented protection checklist.
- [ ] `.github/` satisfies every `branch-pr` automated check and label requirement.
- [ ] `apps/api` runs one passing pytest via a real CI command.
- [ ] `railway.json` + deploy workflow map `dev`→staging, `main`→production.
- [ ] `issue-drafts.md` contains one issue per capability spec, per D6 granularity.
- [ ] Wiki pages contain no duplicated PRD/ARCHITECTURE/DESIGN content — links only.
- [ ] No live GitHub or Railway mutation occurred inside `sdd-apply`.
