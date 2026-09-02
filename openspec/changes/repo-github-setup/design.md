# Design: GitHub Repository, Gitflow Enforcement, CI/CD and Issue Bootstrap

## Technical Approach

Author every governance artifact as a **static, committed file** whose content is fully
specified here, so `sdd-apply` materializes it 1:1 without design decisions. Anything that
requires a live remote (repo creation, branch protection, labels, Railway linkage) is
expressed as a **literal settings payload plus an executable `gh` command**, executed by the
orchestrator/human after review (proposal D4). Enforcement that GitHub's native settings
cannot express (`main` may only be merged from `dev`) is pushed into a workflow check.

## Architecture Decisions

| # | Decision | Alternatives rejected | Rationale |
|---|----------|----------------------|-----------|
| A1 | Railway **native GitHub integration** (branch-based auto-deploy); repo ships `railway.json` only, no `deploy.yml` | GitHub Actions calling `railway up` via CLI + `RAILWAY_TOKEN` secret | No app code, no image, no tests to gate on yet. A CLI workflow needs a secret that cannot exist until the account is linked, so it would be permanently red. Native integration is zero-maintenance and reversible: adding `deploy.yml` later is additive. Supersedes proposal D7's `deploy.yml` line. |
| A2 | `main`-only-from-`dev` enforced by a **workflow job**, not branch protection | Rely on protection rules alone | GitHub branch protection has no "allowed source branch" field. Without the job, D2 is unenforced. |
| A3 | Labels created via **`gh label create` script** (`.github/labels.sh` + `labels.json` manifest), run manually once | GitHub MCP tools; a bootstrap GitHub Action | The GitHub MCP toolset exposes no label-creation tool (**flagged risk**). An Action would need to run before the labels its own PR checks require. |
| A4 | Required status checks referenced by **job `name:`** strings, frozen in this design | Default job-id contexts | Renaming a job silently disables a required check. Names are contract. |
| A5 | `apps/api` uses **src-layout + hatchling + uv**, packages `domain/application/adapters/bootstrap` created with `__init__.py` only | Flat layout; poetry | Matches `docs/ARCHITECTURE.md` §6 verbatim; src-layout forces tests to import the installed package, which is what makes a future import-boundary lint meaningful. |
| A6 | Layering enforced by **`ruff` `flake8-tidy-imports` banned-api**, not a custom script | Custom AST checker; import-linter dep | AGENTS.md line 51 bans FastAPI/OpenCV/PaddleOCR imports in domain/application. `ruff` is already the linter; zero extra dependency. |

## Data Flow

```
issue (status:approved)  ──→  branch feat/x  ──→  PR → dev  ──→  pr-validation + ci
                                                                       │
                                              dev (direct push allowed) ┘
                                                                       │
                                     PR dev → main (source-branch check) ┘
                                                                       │
                                    Railway watches dev → staging, main → production
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `.gitignore` | Create | Python/uv/node/OS ignores |
| `.github/PULL_REQUEST_TEMPLATE.md` | Create | §T1 |
| `.github/ISSUE_TEMPLATE/config.yml` | Create | Disable blank issues, link to Discussions/docs |
| `.github/ISSUE_TEMPLATE/bug_report.md` / `feature_request.md` | Create | Markdown templates (issue-creation skill reads `.md`, never `.yml` forms) |
| `.github/labels.json` | Create | §T4 manifest |
| `.github/labels.sh` | Create | `gh`-based idempotent applier |
| `.github/workflows/pr-validation.yml` | Create | §T2 |
| `.github/workflows/ci.yml` | Create | §T3 |
| `railway.json` | Create | §T5 |
| `apps/api/pyproject.toml` | Create | §T6 |
| `apps/api/src/receipt_risk/{domain,application,adapters/{api,metadata,provenance,ocr},bootstrap}/__init__.py` | Create | Empty layering skeleton |
| `apps/api/tests/test_placeholder.py` | Create | §T6 |
| `docs/wiki/{Home,Local-Setup,Contributing,Environment-and-Secrets,Release-Process}.md` | Create | §T7 |
| `openspec/changes/repo-github-setup/issue-drafts.md` | Create | §T8 |
| `README.md` | Modify | CI badge, Wiki link, Issues link; layout gains `.github/`, `docs/wiki/` |
| `CONTRIBUTING.md` | Modify | Point to enforced templates, label taxonomy, protection rules |

---

## T0. Branch protection — literal settings

Repository: `montesgp/receipt-risk-detector`, **public**. Default branch: `dev`.
API: `PUT /repos/montesgp/receipt-risk-detector/branches/{branch}/protection`.

### `dev` (minimal)

```json
{
  "required_status_checks": null,
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": false,
  "lock_branch": false,
  "allow_fork_syncing": false
}
```

Effect: maintainer direct push allowed; force-push and deletion blocked.

### `main` (strict)

```json
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "Check Issue Reference",
      "Check Issue Has status:approved",
      "Check PR Has type:* Label",
      "Check Source Branch",
      "API Lint and Test"
    ]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 0,
    "require_last_push_approval": false
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": true,
  "lock_branch": false,
  "allow_fork_syncing": false
}
```

Notes: `required_approving_review_count: 0` because solo maintainer — the PR gate itself plus
status checks are the control; raise to 1 when a second contributor joins. `enforce_admins:false`
leaves an emergency escape hatch. `required_linear_history:true` pairs with repo setting
`allow_merge_commit=false, allow_squash_merge=true, allow_rebase_merge=true,
delete_branch_on_merge=true`.

Repo-level settings payload (`PATCH /repos/{owner}/{repo}`):

```json
{
  "default_branch": "dev",
  "has_issues": true,
  "has_wiki": true,
  "has_projects": false,
  "has_discussions": false,
  "allow_merge_commit": false,
  "allow_squash_merge": true,
  "allow_rebase_merge": true,
  "allow_auto_merge": true,
  "delete_branch_on_merge": true
}
```

---

## T1. `.github/PULL_REQUEST_TEMPLATE.md`

```markdown
## Linked issue

<!-- REQUIRED. The issue must already carry the `status:approved` label. -->
Closes #

## PR type

<!-- Check exactly ONE and add the matching `type:*` label to this PR. -->
- [ ] Bug fix (`type:bug`)
- [ ] New feature (`type:feature`)
- [ ] Documentation only (`type:docs`)
- [ ] Code refactoring (`type:refactor`)
- [ ] Maintenance / tooling (`type:chore`)
- [ ] Breaking change (`type:breaking-change`)

## Summary

-
-

## Changes

| File | Change |
|------|--------|
|      |        |

## PRD / spec traceability

<!-- Requirement IDs or capability spec paths this PR implements. -->
-

## Test plan

- [ ] `uv run pytest` passes in `apps/api`
- [ ] `uv run ruff check .` passes in `apps/api`
- [ ] Manually exercised the affected behavior

## Privacy and performance impact

<!-- Required by CONTRIBUTING.md. Write "None" if genuinely none. -->
-

## Contributor checklist

- [ ] Linked an issue that has `status:approved`
- [ ] Exactly one `type:*` label applied
- [ ] Branch name matches `^(feat|fix|chore|docs|style|refactor|perf|test|build|ci|revert)/[a-z0-9._-]+$`
- [ ] Conventional commit messages, no `Co-Authored-By` trailers
- [ ] No real receipts or personal/banking data added
- [ ] Docs (`docs/`, ADR, OpenSpec) updated when behavior changed
- [ ] Scoring changes document old/new frozen-fixture outputs and bump `ruleset_version`
```

---

## T2. `.github/workflows/pr-validation.yml`

```yaml
name: PR Validation

on:
  pull_request:
    types: [opened, edited, reopened, synchronize, labeled, unlabeled]

permissions:
  contents: read
  issues: read
  pull-requests: read

concurrency:
  group: pr-validation-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  issue-reference:
    name: Check Issue Reference
    runs-on: ubuntu-latest
    outputs:
      issue: ${{ steps.extract.outputs.issue }}
    steps:
      - id: extract
        uses: actions/github-script@v7
        env:
          PR_BODY: ${{ github.event.pull_request.body }}
        with:
          script: |
            const body = process.env.PR_BODY || '';
            const match = body.match(/\b(?:closes|fixes|resolves)\s+#(\d+)\b/i);
            if (!match) {
              core.setFailed('PR body must contain "Closes #N", "Fixes #N" or "Resolves #N".');
              return;
            }
            core.setOutput('issue', match[1]);
            core.info(`Linked issue: #${match[1]}`);

  issue-approved:
    name: Check Issue Has status:approved
    runs-on: ubuntu-latest
    needs: issue-reference
    steps:
      - uses: actions/github-script@v7
        env:
          ISSUE_NUMBER: ${{ needs.issue-reference.outputs.issue }}
        with:
          script: |
            const issue_number = Number(process.env.ISSUE_NUMBER);
            const { data } = await github.rest.issues.get({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number,
            });
            const labels = data.labels.map(l => (typeof l === 'string' ? l : l.name));
            if (!labels.includes('status:approved')) {
              core.setFailed(`Issue #${issue_number} does not have the "status:approved" label.`);
              return;
            }
            core.info(`Issue #${issue_number} is approved.`);

  type-label:
    name: Check PR Has type:* Label
    runs-on: ubuntu-latest
    steps:
      - uses: actions/github-script@v7
        with:
          script: |
            const labels = context.payload.pull_request.labels.map(l => l.name);
            const typeLabels = labels.filter(n => n.startsWith('type:'));
            if (typeLabels.length !== 1) {
              core.setFailed(
                `PR must have exactly one "type:*" label, found ${typeLabels.length}: ` +
                (typeLabels.join(', ') || 'none')
              );
              return;
            }
            core.info(`Type label: ${typeLabels[0]}`);

  source-branch:
    name: Check Source Branch
    runs-on: ubuntu-latest
    steps:
      - uses: actions/github-script@v7
        with:
          script: |
            const pr = context.payload.pull_request;
            const base = pr.base.ref;
            const head = pr.head.ref;
            const sameRepo = pr.head.repo.full_name === pr.base.repo.full_name;

            if (base === 'main') {
              if (!sameRepo || head !== 'dev') {
                core.setFailed('Pull requests into "main" are only allowed from the "dev" branch of this repository.');
                return;
              }
              core.info('main <- dev promotion: allowed.');
              return;
            }

            if (base === 'dev') {
              const pattern = /^(feat|fix|chore|docs|style|refactor|perf|test|build|ci|revert)\/[a-z0-9._-]+$/;
              if (!pattern.test(head)) {
                core.setFailed(`Branch "${head}" does not match ^(feat|fix|chore|docs|style|refactor|perf|test|build|ci|revert)/[a-z0-9._-]+$`);
                return;
              }
              core.info(`Branch name "${head}" is valid.`);
              return;
            }

            core.setFailed(`Unexpected base branch "${base}". PRs must target "dev" or "main".`);
```

Design notes: `permissions` is least-privilege and read-only; no `pull_request_target`, so a fork
PR can never run with write scope. All untrusted text (`PR_BODY`) is passed through `env:` and read
via `process.env`, never interpolated into the script body — this closes the classic
`${{ github.event.* }}` script-injection hole.

---

## T3. `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [dev, main]
  pull_request:
    branches: [dev, main]

permissions:
  contents: read

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  api:
    name: API Lint and Test
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: apps/api
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
          cache-dependency-glob: apps/api/uv.lock

      - name: Set up Python
        run: uv python install 3.12

      - name: Sync dependencies
        run: uv sync --all-extras --dev

      - name: Lint
        run: uv run ruff check .

      - name: Format check
        run: uv run ruff format --check .

      - name: Test
        run: uv run pytest
```

`web` job is intentionally absent: `apps/web` has no scaffold yet. Adding it is a follow-up issue,
and adding a job later is additive to the required-check list.

---

## T4. Label taxonomy — `.github/labels.json`

```json
[
  { "name": "type:bug",              "color": "d73a4a", "description": "Defect in existing behavior" },
  { "name": "type:feature",          "color": "0e8a16", "description": "New user-facing capability" },
  { "name": "type:docs",             "color": "0075ca", "description": "Documentation-only change" },
  { "name": "type:refactor",         "color": "5319e7", "description": "Internal restructuring, no behavior change" },
  { "name": "type:chore",            "color": "fef2c0", "description": "Tooling, CI, dependencies, maintenance" },
  { "name": "type:breaking-change",  "color": "b60205", "description": "Backward-incompatible change" },

  { "name": "status:needs-triage",   "color": "ededed", "description": "Awaiting maintainer review" },
  { "name": "status:needs-info",     "color": "d4c5f9", "description": "Blocked on missing evidence from the reporter" },
  { "name": "status:approved",       "color": "0e8a16", "description": "Approved for implementation; required before any PR links it" },
  { "name": "status:in-progress",    "color": "fbca04", "description": "Actively being implemented" },
  { "name": "status:blocked",        "color": "b60205", "description": "Blocked by an external dependency or decision" },
  { "name": "status:wontfix",        "color": "ffffff", "description": "Out of scope; will not be implemented" },

  { "name": "capability:receipt-analysis",            "color": "1d76db", "description": "openspec/specs/receipt-analysis" },
  { "name": "capability:public-api-contract",         "color": "1d76db", "description": "openspec/specs/public-api-contract" },
  { "name": "capability:api-rate-limiting",           "color": "1d76db", "description": "openspec/specs/api-rate-limiting" },
  { "name": "capability:data-retention",              "color": "1d76db", "description": "openspec/specs/data-retention" },
  { "name": "capability:ui-localization-and-theming", "color": "1d76db", "description": "openspec/specs/ui-localization-and-theming" },
  { "name": "capability:architecture-documentation",  "color": "1d76db", "description": "openspec/specs/architecture-documentation" },

  { "name": "area:api",   "color": "c5def5", "description": "apps/api" },
  { "name": "area:web",   "color": "c5def5", "description": "apps/web" },
  { "name": "area:docs",  "color": "c5def5", "description": "docs/ and openspec/" },
  { "name": "area:infra", "color": "c5def5", "description": ".github/, Docker, Railway" },

  { "name": "mvp1",           "color": "5319e7", "description": "In MVP 1 scope" },
  { "name": "roadmap",        "color": "bfd4f2", "description": "Post-MVP 1; must not leak into MVP 1" },
  { "name": "good first issue","color": "7057ff", "description": "Suitable for a first-time contributor" },
  { "name": "size:exception", "color": "e99695", "description": "Explicitly accepted breach of the 400-line review budget" }
]
```

### `.github/labels.sh` (idempotent applier)

```bash
#!/usr/bin/env bash
set -euo pipefail

# One-time (and re-runnable) label bootstrap.
# Requires: gh CLI authenticated with repo admin scope, jq.
# Usage: .github/labels.sh [owner/repo]

REPO="${1:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"
MANIFEST="$(dirname "$0")/labels.json"

jq -c '.[]' "$MANIFEST" | while read -r label; do
  name="$(jq -r '.name' <<<"$label")"
  color="$(jq -r '.color' <<<"$label")"
  description="$(jq -r '.description' <<<"$label")"
  gh label create "$name" --repo "$REPO" --color "$color" --description "$description" --force
  echo "synced: $name"
done
```

`gh label create --force` upserts, so re-running reconciles drift. **Flagged (A3):** no
`mcp__github__*` label-creation tool exists; this script is the sanctioned workaround and is a
documented manual one-time step in `docs/wiki/Environment-and-Secrets.md`.

---

## T5. Railway wiring — `railway.json`

Deployment uses Railway's **native GitHub integration** (A1). No `deploy.yml` is authored.

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "apps/api/Dockerfile",
    "watchPatterns": ["apps/api/**"]
  },
  "deploy": {
    "startCommand": "uv run uvicorn receipt_risk.bootstrap.app:app --host 0.0.0.0 --port ${PORT}",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 60,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

`apps/api/Dockerfile` and `bootstrap/app.py` do not exist yet, so this file is **inert
configuration**: Railway only reads it once a service is linked. It is committed now so the
service is correct on first link. Manual, out-of-design steps for the user, documented in the
Release-Process wiki page:

1. Create the Railway project and connect the GitHub repo.
2. Create two environments: `staging` (watch branch `dev`) and `production` (watch branch `main`).
3. Set `RAILWAY_DOCKERFILE_PATH` / root directory if the monorepo service root differs.
4. Configure environment variables and secrets per environment.
5. Enable "wait for CI to pass" in the Railway service settings so a red `CI` blocks the deploy.

Migration path if native integration proves insufficient: add `.github/workflows/deploy.yml`
calling `railway up --service <id>` with a `RAILWAY_TOKEN` repository secret and
`environment:` protection rules. Purely additive; `railway.json` is unchanged.

---

## T6. `apps/api` minimal scaffold

### Directory skeleton

```text
apps/api/
├── pyproject.toml
├── README.md
├── src/receipt_risk/
│   ├── __init__.py
│   ├── domain/__init__.py
│   ├── application/__init__.py
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── api/__init__.py
│   │   ├── metadata/__init__.py
│   │   ├── provenance/__init__.py
│   │   └── ocr/__init__.py
│   └── bootstrap/__init__.py
└── tests/
    └── test_placeholder.py
```

Every `__init__.py` is empty except a one-line docstring naming its layer role. No business logic.

### `apps/api/pyproject.toml`

```toml
[project]
name = "receipt-risk-api"
version = "0.1.0"
description = "Transfer Receipt Risk Engine API"
readme = "README.md"
requires-python = ">=3.12"
license = { text = "Apache-2.0" }
dependencies = [
    "fastapi>=0.115",
    "pydantic>=2.9",
]

[project.optional-dependencies]
server = ["uvicorn[standard]>=0.32"]

[dependency-groups]
dev = [
    "pytest>=8.3",
    "ruff>=0.8",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/receipt_risk"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q --strict-markers"

[tool.ruff]
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "TID"]

# AGENTS.md architecture rule: domain and application code must not import
# FastAPI, PaddleOCR, ExifTool, OpenCV or storage implementations.
[tool.ruff.lint.flake8-tidy-imports.banned-api]
"fastapi".msg = "Framework imports are only allowed in adapters/ and bootstrap/."
"starlette".msg = "Framework imports are only allowed in adapters/ and bootstrap/."
"cv2".msg = "OpenCV is an adapter-only dependency."
"paddleocr".msg = "PaddleOCR is an adapter-only dependency."
"PIL".msg = "Pillow is an adapter-only dependency."

[tool.ruff.lint.per-file-ignores]
"src/receipt_risk/adapters/**" = ["TID251"]
"src/receipt_risk/bootstrap/**" = ["TID251"]
"tests/**" = ["TID251"]
```

The banned-api block is the machine-readable form of AGENTS.md line 51: the ban applies
repository-wide and is *lifted* only for `adapters/**` and `bootstrap/**`, which is exactly the
allowed direction of dependency. `domain/` and `application/` therefore fail CI on a FastAPI
import today, before any code exists.

### `apps/api/tests/test_placeholder.py`

```python
"""Placeholder test proving the pytest harness runs in CI.

Delete this file once the first real behavior test exists.
"""


def test_true_is_true() -> None:
    assert True
```

---

## T7. GitHub Wiki content (`docs/wiki/` → pushed to the `.wiki.git` repo)

Anti-duplication rule (D3): a page may summarize *process*, and MUST link to `docs/` for any
product, architecture or design content. Links use absolute GitHub URLs because wiki pages live
in a separate repository and relative `docs/` links would 404.

### `Home.md`

```markdown
# Transfer Receipt Risk Engine — Wiki

This wiki covers **process and onboarding only**: how to set the project up, how to contribute,
how environments and secrets work, and how a release is cut.

Product scope, architecture and design live in the repository and are **not duplicated here** —
duplicated documents drift.

## Process pages

- [Local Setup](Local-Setup)
- [Contributing](Contributing)
- [Environment and Secrets](Environment-and-Secrets)
- [Release Process](Release-Process)

## Source-of-truth documents (repository)

| Topic | Document |
|-------|----------|
| Product scope and acceptance criteria | [docs/PRD.md](https://github.com/montesgp/receipt-risk-detector/blob/main/docs/PRD.md) |
| Boundaries and dependency rules | [docs/ARCHITECTURE.md](https://github.com/montesgp/receipt-risk-detector/blob/main/docs/ARCHITECTURE.md) |
| Public integration contract | [docs/API.md](https://github.com/montesgp/receipt-risk-detector/blob/main/docs/API.md) |
| UX and visual language | [docs/DESIGN.md](https://github.com/montesgp/receipt-risk-detector/blob/main/docs/DESIGN.md) |
| Post-MVP stages | [docs/ROADMAP.md](https://github.com/montesgp/receipt-risk-detector/blob/main/docs/ROADMAP.md) |
| Agent/implementation workflow | [AGENTS.md](https://github.com/montesgp/receipt-risk-detector/blob/main/AGENTS.md) |
| Architecture decision records | [docs/adr/](https://github.com/montesgp/receipt-risk-detector/tree/main/docs/adr) |
| Capability specifications | [openspec/specs/](https://github.com/montesgp/receipt-risk-detector/tree/main/openspec/specs) |

If a fact belongs in one of those documents, change it there and link to it — do not restate it
in the wiki.
```

### `Local-Setup.md`

```markdown
# Local Setup

## Prerequisites

| Tool | Version | Why |
|------|---------|-----|
| Python | 3.12+ | API runtime |
| `uv` | latest | Python packaging and task running |
| Node.js | 20+ | SvelteKit web client |
| Docker + Compose | latest | Target local developer experience |
| `gh` CLI | latest | Issues, PRs, one-time label bootstrap |

Full stack table: [README — Stack](https://github.com/montesgp/receipt-risk-detector#stack).

## Clone

    git clone https://github.com/montesgp/receipt-risk-detector.git
    cd receipt-risk-detector
    git checkout dev

`dev` is the default branch and the integration branch. `main` is release-only.

## API

    cd apps/api
    uv sync --all-extras --dev
    uv run pytest
    uv run ruff check .

`uv run pytest` currently runs one placeholder test. That is expected until the first capability
is implemented.

## Web

`apps/web` is not scaffolded yet. Track it in
[Issues](https://github.com/montesgp/receipt-risk-detector/issues).

## Whole stack

    docker compose up --build

    Web:  http://localhost:5173
    API:  http://localhost:8000
    Docs: http://localhost:8000/docs

This is target-state until the scaffold lands; see
[README — Local development target](https://github.com/montesgp/receipt-risk-detector#local-development-target).

## Data rule

Never place a real transfer receipt containing personal or banking data in the working tree,
a fixture, an issue or a PR. Use synthetic or fully anonymized samples.
```

### `Contributing.md`

```markdown
# Contributing (process summary)

Authoritative rules:
[CONTRIBUTING.md](https://github.com/montesgp/receipt-risk-detector/blob/main/CONTRIBUTING.md).
This page only explains the mechanics of the GitHub workflow.

## 1. Start from an approved issue

Every PR must link an issue that carries `status:approved`. CI enforces this — a PR without it
cannot merge. Open an issue first; a maintainer applies `status:approved`.

Granularity: one issue per PRD requirement group or capability, not per FR line and not one for
the whole MVP.

## 2. Branch

Branch from `dev`. Names must match:

    ^(feat|fix|chore|docs|style|refactor|perf|test|build|ci|revert)/[a-z0-9._-]+$

Example: `feat/receipt-upload-validation`.

## 3. Commit

Conventional commits:

    ^(build|chore|ci|docs|feat|fix|perf|refactor|revert|style|test)(\([a-z0-9._-]+\))?!?: .+

No `Co-Authored-By` or AI-attribution trailers.

## 4. Open the PR

Target `dev`. Fill the PR template completely, keep `Closes #N`, and apply **exactly one**
`type:*` label.

## 5. Checks that must pass

| Check | What it verifies |
|-------|------------------|
| Check Issue Reference | Body contains `Closes/Fixes/Resolves #N` |
| Check Issue Has status:approved | Linked issue is approved |
| Check PR Has type:* Label | Exactly one `type:*` label |
| Check Source Branch | Branch name is valid; `main` only receives PRs from `dev` |
| API Lint and Test | `ruff` and `pytest` pass in `apps/api` |

## 6. Labels

The taxonomy is a committed manifest:
[.github/labels.json](https://github.com/montesgp/receipt-risk-detector/blob/main/.github/labels.json).
Only a maintainer applies `status:*`. Never invent a label; change the manifest instead.

## 7. Branch model

- Feature/fix branches → PR → `dev` (deploys to staging).
- `dev` → PR → `main` (deploys to production). Only `dev` may be merged into `main`.
- `dev` accepts maintainer direct pushes for trivial maintenance; force-push and deletion are
  blocked on both branches.

## 8. Architecture constraints

`domain/` and `application/` must not import FastAPI, OpenCV, PaddleOCR, Pillow or any storage
implementation. `ruff` enforces this in CI. Rationale:
[docs/ARCHITECTURE.md](https://github.com/montesgp/receipt-risk-detector/blob/main/docs/ARCHITECTURE.md).
```

### `Environment-and-Secrets.md`

```markdown
# Environment and Secrets

## Principles

- No secret is ever committed, pasted into an issue, or included in a PR body.
- MVP 1 has no database and no durable receipt storage — there is no persistence credential.
- MVP 1 has no API access token; deployments enforce file-size limits, timeouts and rate
  limiting instead. See
  [docs/API.md](https://github.com/montesgp/receipt-risk-detector/blob/main/docs/API.md).

## Environments

| Environment | Branch | Host |
|-------------|--------|------|
| staging | `dev` | Railway staging |
| production | `main` | Railway production |

Rationale: [ADR 0001](https://github.com/montesgp/receipt-risk-detector/blob/main/docs/adr/0001-railway-as-deployment-target.md).

## Local environment

Copy `.env.example` to `.env` when it exists. `.env` is git-ignored. Do not add real values to
`.env.example` — placeholders only.

## GitHub repository secrets

None are required today. Deployment runs through Railway's native GitHub integration, so no
`RAILWAY_TOKEN` lives in GitHub Actions. If a deploy workflow is ever added, its token belongs in
a GitHub **Environment** secret with required reviewers, not a plain repository secret.

## One-time maintainer bootstrap

These steps are manual and are not automated by CI:

1. **Labels** — `.github/labels.sh montesgp/receipt-risk-detector` (needs `gh` with admin scope
   and `jq`). Re-runnable; reconciles drift from `.github/labels.json`.
2. **Branch protection** — apply the `dev` and `main` payloads from the change design.
3. **Railway** — create the project, connect the repo, create `staging` and `production`
   environments watching `dev` and `main`, and set per-environment variables.
4. **Wiki** — clone `receipt-risk-detector.wiki.git` and push the pages from `docs/wiki/`.

## Leak response

If a secret is exposed: rotate it first, then rewrite history or delete the artifact, then record
what was rotated. Report privately per
[SECURITY.md](https://github.com/montesgp/receipt-risk-detector/blob/main/SECURITY.md) — never in
a public issue.
```

### `Release-Process.md`

```markdown
# Release Process

A release is a promotion of `dev` to `main`. `main` is always deployable.

## Steps

1. **Verify staging.** `dev` is deployed to Railway staging. Exercise the analyze flow and the
   documented failure modes.
2. **Open the promotion PR.** `gh pr create --base main --head dev --title "chore(release): promote dev to main"`.
   Link the release-tracking issue and apply `type:chore` (or `type:breaking-change`).
3. **Wait for checks.** `Check Source Branch` confirms the PR really comes from `dev`;
   `API Lint and Test` must be green. `main` requires linear history, so merge by squash or rebase.
4. **Merge.** Railway production deploys automatically from `main`.
5. **Tag.** `git tag -a vX.Y.Z -m "vX.Y.Z" && git push origin vX.Y.Z`.
6. **Release notes.** Generate from the squashed conventional commits; call out any
   `type:breaking-change` and any `ruleset_version` bump explicitly.

## Versioning

- `engine_version` / `ruleset_version` are scoring artifacts and change whenever scoring behavior
  changes, independent of the repository tag. Scoring changes must document old/new outputs for
  frozen signal fixtures — see
  [CONTRIBUTING.md](https://github.com/montesgp/receipt-risk-detector/blob/main/CONTRIBUTING.md).
- The repository tag follows semantic versioning of the public API contract:
  [docs/API.md](https://github.com/montesgp/receipt-risk-detector/blob/main/docs/API.md).

## Rollback

Redeploy the previous successful production deployment from the Railway dashboard — that is the
fast path. Then land a `revert/<description>` branch through the normal `dev` → `main` flow so the
repository state matches production. Never force-push `main`; protection blocks it.
```

---

## T8. `issue-drafts.md` format

Per user decision 4: title + short summary + spec link + labels. **No copied Given/When/Then**
— the spec file is the single source, and copying it guarantees drift.

### Per-draft template

```markdown
### Draft N — {Capability Title}

- **Title**: `{type}({capability-slug}): implement {capability title}`
- **Labels**: `type:feature`, `capability:{slug}`, `area:{api|web|docs|infra}`, `mvp1`, `status:needs-triage`
- **Body**:

  ```markdown
  ## Summary

  {2-3 sentences: what capability this delivers and why it is in MVP 1. No requirement text.}

  ## Specification

  Authoritative requirements and acceptance scenarios:
  [`openspec/specs/{slug}/spec.md`](https://github.com/montesgp/receipt-risk-detector/blob/main/openspec/specs/{slug}/spec.md)

  This issue intentionally does not restate the requirements. Implement against the spec file.

  ## Definition of done

  - [ ] Every requirement in the linked spec has a passing test
  - [ ] Layering respected: no framework imports in `domain/` or `application/`
  - [ ] `docs/` updated if the public contract or architecture changed
  ```
```

### Draft inventory (one per capability spec)

| # | Slug | Suggested title | Primary area |
|---|------|-----------------|--------------|
| 1 | `receipt-analysis` | `feat(receipt-analysis): implement receipt analysis pipeline` | `area:api` |
| 2 | `public-api-contract` | `feat(public-api-contract): implement the public analyze endpoint contract` | `area:api` |
| 3 | `api-rate-limiting` | `feat(api-rate-limiting): implement request limits and abuse controls` | `area:api` |
| 4 | `data-retention` | `feat(data-retention): implement ephemeral upload handling and retention guarantees` | `area:api` |
| 5 | `ui-localization-and-theming` | `feat(ui-localization-and-theming): implement web localization and theming` | `area:web` |
| 6 | `architecture-documentation` | `docs(architecture-documentation): keep architecture documentation in sync` | `area:docs` |

Draft 6 uses `type:docs`; drafts 1-5 use `type:feature`.

Issue templates in `.github/ISSUE_TEMPLATE/` are **Markdown** (`bug_report.md`,
`feature_request.md`), not YAML issue forms, because the `issue-creation` skill routes `.yml`
forms to `gh issue create --web` and stops for human completion — Markdown lets the drafts be
published non-interactively. `config.yml` sets `blank_issues_enabled: false`.

---

## Interfaces / Contracts

Frozen strings that other artifacts depend on. Changing any of them requires updating the
branch-protection `contexts` array in the same commit.

| Contract | Value |
|----------|-------|
| Required check names | `Check Issue Reference`, `Check Issue Has status:approved`, `Check PR Has type:* Label`, `Check Source Branch`, `API Lint and Test` |
| Branch regex | `^(feat\|fix\|chore\|docs\|style\|refactor\|perf\|test\|build\|ci\|revert)/[a-z0-9._-]+$` |
| Issue-link regex | `\b(?:closes\|fixes\|resolves)\s+#(\d+)\b` (case-insensitive) |
| Approval label | `status:approved` |
| Type label prefix | `type:` — exactly one per PR |
| Package import root | `receipt_risk` |

## Testing Strategy

| Layer | What to Test | Approach |
|-------|--------------|----------|
| Unit | `apps/api` harness runs | `tests/test_placeholder.py::test_true_is_true` via `uv run pytest` |
| Lint | Layering rule holds | `uv run ruff check .`; banned-api rejects `fastapi` in `domain/`/`application/` |
| Static | Workflow YAML is well-formed | `actionlint` locally, or first CI run |
| Integration | pr-validation logic | Unverifiable until a remote exists (accepted proposal risk). Validate on the first real PR against `dev`; treat a failure as a follow-up `ci/*` fix. |
| Manual | Branch protection applied | `gh api repos/montesgp/receipt-risk-detector/branches/main/protection` diffed against the T0 payload |

## Threat Matrix

| Boundary | Minimum adversarial cases | Applicability | Design response | Planned RED tests |
|---|---|---|---|---|
| Documentation-like paths | `requirements.txt`, executable Markdown, `README.sh` | **N/A** — no file-classification or execution logic is authored; the change only adds declarative config plus one operator-run script | — | — |
| Git repository selection | `git -C`, relative/absolute paths | **N/A** — no tool selects a repository; `git init` and pushes are operator actions in the documented cwd | — | — |
| Commit state | staged, `commit -a`, empty index | **N/A** — no automated commit is produced by this change | — | — |
| Push state | tracking branch, first push, explicit refspec | **Applicable** — first push creates `dev` and `main`; protection must exist before the first PR | Push `main` first, then branch `dev` from it, set `dev` as default, then apply both protection payloads before opening any PR. If protection is applied before the branch exists the API returns 404 — order is load-bearing. | Manual verification: `gh api .../branches/{dev,main}/protection` returns the T0 payloads |
| PR commands | explicit `--head`, environment prefix, composed commands | **Applicable** — a PR into `main` from a branch other than `dev`, or from a fork, would bypass the gitflow policy | `Check Source Branch` job asserts `base==main ⇒ head=='dev' && same repository`; any other base fails closed | On the first PR: (a) `feat/x → main` must fail; (b) `dev → main` must pass; (c) invalid branch name into `dev` must fail |
| Untrusted PR text in workflows | script injection via `${{ github.event.pull_request.body }}` | **Applicable** — the body is attacker-controlled on a public repo | Body passed via `env:` and read with `process.env`, never string-interpolated into `github-script`; `permissions` read-only; `pull_request` (not `pull_request_target`), so fork PRs get no write token or secrets | Open a PR whose body contains a backtick/`${{ }}` payload; the check must fail cleanly with the normal error, not execute anything |

## Migration / Rollout

No data migration. Rollout order is load-bearing and must be followed by the post-apply
orchestrator step:

1. `git init`, commit on `main`, create repo, push `main`.
2. Branch and push `dev`; set `dev` as default branch.
3. Run `.github/labels.sh` (labels must exist before any PR needs a `type:*` label).
4. Apply `main` then `dev` protection payloads.
5. Publish issues from `issue-drafts.md`; apply `status:approved` to whichever is next.
6. Push `docs/wiki/*` to the wiki repository.
7. Link Railway manually (out of design control).

Rollback is per the proposal: nothing is published until step 1, and the repository can be
deleted with no consumers affected.

## Open Questions

- [ ] `apps/web` has no scaffold, so CI has no `web` job. Confirm this is a follow-up issue rather
      than in-scope here.
- [ ] `railway.json` references `apps/api/Dockerfile` and `receipt_risk.bootstrap.app:app`, which
      do not exist yet. Confirm shipping inert config now (recommended) versus deferring the file
      until the Dockerfile lands.
- [ ] `required_approving_review_count: 0` on `main` — confirm the solo-maintainer default.
