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

The frontend calls the API directly cross-origin (no dev-server proxy), so the API must allow
the web dev server's origin before `npm run dev` can reach it:

    cd apps/api
    RECEIPT_RISK_CORS_ALLOWED_ORIGINS=http://localhost:5173 uv run uvicorn receipt_risk.bootstrap.app:app --reload

Then, in another terminal:

    cd apps/web
    npm install
    npm run dev

    Web: http://localhost:5173

`apps/web/.env` sets `PUBLIC_API_BASE_URL` (defaults to `http://localhost:8000`); copy
`apps/web/env.sample` to `apps/web/.env` if it is missing locally. Without
`RECEIPT_RISK_CORS_ALLOWED_ORIGINS` set to the web dev server's origin, every request from the
browser fails as a network error indistinguishable from the API being down — set it explicitly
rather than debugging a CORS rejection as if it were an outage.

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
