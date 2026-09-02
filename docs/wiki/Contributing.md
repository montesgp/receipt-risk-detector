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
