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
