# Contributing

Thanks for helping improve the Transfer Receipt Risk Engine.

## Before opening a change

1. Read `docs/PRD.md`, `docs/ARCHITECTURE.md` and `AGENTS.md`.
2. Confirm the proposal belongs to MVP 1 or label it as a roadmap discussion.
3. Open an issue for scoring changes, new analyzers or external dependencies.
4. Do not attach real transfer receipts containing personal or financial data.

## Pull requests

A pull request should include:

- Problem and intended behavior.
- PRD requirement IDs affected.
- Tests and fixture provenance.
- SDD/TDD/RDD or ADR updates when applicable.
- Privacy and performance impact.
- Before/after screenshots for visible UI changes.

Scoring changes must document old/new outputs for frozen signal fixtures and update `ruleset_version` when behavior changes.

## Branching policy (gitflow)

Two long-lived branches, per proposal decision D5:

- `dev` deploys to the Railway staging environment.
- `main` deploys to the Railway production environment.

Feature and fix branches target `dev`; `dev` is promoted to `main` only after staging verification.
Only `dev` may be merged into `main` — enforced by the `Check Source Branch` job in
[`.github/workflows/pr-validation.yml`](.github/workflows/pr-validation.yml). Branch protection
rules for both branches are defined in
`openspec/changes/repo-github-setup/repo-settings-checklist.md`.

Every pull request must use
[`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md), link an issue carrying
`status:approved`, and apply exactly one `type:*` label — all enforced by `pr-validation.yml`.

## Issue granularity

Per proposal decision D6: open one GitHub issue per PRD requirement group (for example, one issue for
FR-005 Local OCR, one for the `api-rate-limiting` capability), not one issue per FR/NFR line item and
not one issue for the whole MVP. The label taxonomy is a committed manifest,
[`.github/labels.json`](.github/labels.json) — never invent a label; change the manifest instead.

## Development values

- Prefer evidence and reproducible rules over opaque conclusions.
- Preserve domain boundaries.
- Keep MVP 1 small.
- Make failures explicit.
- Treat uploads and fixture data as sensitive.

By contributing, you agree that your contribution is licensed under Apache License 2.0.
