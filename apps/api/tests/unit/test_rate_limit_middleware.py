"""ASGI middleware tests: 429 response contract, exempt paths, headers."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from receipt_risk.adapters.api.middleware.rate_limit import RateLimitMiddleware


def _app(*, default_limit: int = 30, analyze_limit: int = 2) -> FastAPI:
    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/v1/receipts/analyze")
    def analyze():
        return {"ok": True}

    @app.get("/other")
    def other():
        return {"ok": True}

    app.add_middleware(
        RateLimitMiddleware,
        default_limit_per_minute=default_limit,
        analyze_limit_per_minute=analyze_limit,
    )
    return app


def test_health_is_exempt_from_rate_limiting() -> None:
    client = TestClient(_app(default_limit=1, analyze_limit=1))
    for _ in range(5):
        assert client.get("/health").status_code == 200


def test_analyze_endpoint_returns_429_with_retry_after_and_problem_details() -> None:
    client = TestClient(_app(analyze_limit=1))
    first = client.post("/v1/receipts/analyze")
    assert first.status_code == 200

    second = client.post("/v1/receipts/analyze")
    assert second.status_code == 429
    assert "Retry-After" in second.headers
    body = second.json()
    assert body["code"] == "RATE_LIMITED"
    assert body["status"] == 429


def test_rate_limit_headers_present_on_every_response() -> None:
    client = TestClient(_app())
    response = client.get("/other")
    assert "RateLimit-Limit" in response.headers
    assert "RateLimit-Remaining" in response.headers
    assert "RateLimit-Reset" in response.headers
