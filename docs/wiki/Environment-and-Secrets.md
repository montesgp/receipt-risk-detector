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
