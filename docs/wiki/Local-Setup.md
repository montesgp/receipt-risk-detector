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
