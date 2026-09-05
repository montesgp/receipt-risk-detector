"""Env-configurable CORS allowlist (public-api-contract spec's "CORS
allowlist" requirement, D4). No origins are allowed by default: server-side
clients (workflow-automation tools, bots, generic HTTP) are entirely
unaffected by CORS either way, since CORS is a browser-enforced mechanism --
an empty allowlist only means no *browser* origin can read the response
until one is configured."""

from __future__ import annotations

import os

_ENV_VAR = "RECEIPT_RISK_CORS_ALLOWED_ORIGINS"


def allowed_origins() -> list[str]:
    """Comma-separated list of exact origins, e.g.
    'https://app.example.com,https://staging.example.com'. Empty/unset means
    no browser origin is allowlisted (safe default -- see module docstring)."""
    raw = os.environ.get(_ENV_VAR, "")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]
