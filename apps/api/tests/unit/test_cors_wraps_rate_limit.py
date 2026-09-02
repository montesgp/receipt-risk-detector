"""Confirms CORS is the OUTERMOST middleware: an allowlisted origin gets
`Access-Control-Allow-Origin` on every response shape, including a 429 from
the rate limiter -- per docs/API.md §5's documented contract ("the rate
limiter runs inside the CORS middleware, not in front of it"). A
disallowed origin gets no such header, proving the allowlist is real, not
a wildcard."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from receipt_risk.adapters.api.middleware.rate_limit import RateLimitMiddleware

_ALLOWED_ORIGIN = "https://app.example.com"


def _app() -> FastAPI:
    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/v1/receipts/analyze")
    def analyze():
        return {"ok": True}

    # Registration order matters: Starlette applies middleware in reverse
    # order, so the one added LAST becomes OUTERMOST. Rate limiter first,
    # CORS last -> CORS wraps the rate limiter, matching docs/API.md §5.
    app.add_middleware(RateLimitMiddleware, default_limit_per_minute=1, analyze_limit_per_minute=1)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[_ALLOWED_ORIGIN],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


def test_allowed_origin_gets_cors_header_on_normal_response() -> None:
    client = TestClient(_app())

    response = client.get("/health", headers={"Origin": _ALLOWED_ORIGIN})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == _ALLOWED_ORIGIN


def test_allowed_origin_gets_cors_header_even_on_429_from_rate_limiter() -> None:
    client = TestClient(_app())

    client.post("/v1/receipts/analyze", headers={"Origin": _ALLOWED_ORIGIN})  # consume the 1 token
    response = client.post("/v1/receipts/analyze", headers={"Origin": _ALLOWED_ORIGIN})

    assert response.status_code == 429
    assert response.headers["access-control-allow-origin"] == _ALLOWED_ORIGIN


def test_disallowed_origin_gets_no_cors_header() -> None:
    client = TestClient(_app())

    response = client.get("/health", headers={"Origin": "https://evil.example.com"})

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
