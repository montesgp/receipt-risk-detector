"""ASGI application entrypoint.

Wires adapters into a FastAPI app. This module is the only place allowed to
import both the framework and the application/domain layers directly (see
AGENTS.md's architecture rules and the `bootstrap/` layering exception in
pyproject.toml).

Only the liveness endpoint exists today. `/ready`, `/version` and
`POST /v1/receipts/analyze` are implemented by the `receipt-analysis` and
`public-api-contract` capability specs (see openspec/specs/), tracked as
GitHub issues #1 and #2.
"""

from fastapi import FastAPI

app = FastAPI(title="Transfer Receipt Risk Engine")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe used by Railway's healthcheck (see railway.json)."""
    return {"status": "ok"}
