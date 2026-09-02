"""Rate-limiting ASGI middleware — pure `Starlette` `BaseHTTPMiddleware`
wrapping the pure `TokenBucketStore` algorithm (`adapters/api/rate_limit/
bucket.py`). Runs before body parsing, per DD5 (`openspec/changes/archive/
2026-09-01-mvp-init-foundation/design.md`).

Exempt: `OPTIONS` preflights and `GET /health`, `/ready`, `/version`
(docs/API.md §5b). Every non-exempt route is evaluated against the
`default` bucket; `POST /v1/receipts/analyze` must additionally satisfy
the stricter `analyze` bucket.
"""

from __future__ import annotations

import asyncio

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from receipt_risk.adapters.api.rate_limit import config as rate_limit_config
from receipt_risk.adapters.api.rate_limit.bucket import TokenBucketStore

_EXEMPT_PATHS = frozenset({"/health", "/ready", "/version"})
_ANALYZE_PATH = "/v1/receipts/analyze"


def _client_key(request: Request) -> str:
    if rate_limit_config.trust_forwarded_for():
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    client = request.client
    return client.host if client is not None else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        default_limit_per_minute: int | None = None,
        analyze_limit_per_minute: int | None = None,
    ) -> None:
        super().__init__(app)
        default_limit = default_limit_per_minute or rate_limit_config.default_limit_per_minute()
        analyze_limit = analyze_limit_per_minute or rate_limit_config.analyze_limit_per_minute()
        self._lock = asyncio.Lock()
        self._default_store = TokenBucketStore(
            capacity=default_limit,
            refill_per_second=default_limit / 60,
            max_tracked_keys=rate_limit_config.max_tracked_keys(),
        )
        self._analyze_store = TokenBucketStore(
            capacity=analyze_limit,
            refill_per_second=analyze_limit / 60,
            max_tracked_keys=rate_limit_config.max_tracked_keys(),
        )
        self._default_limit = default_limit
        self._analyze_limit = analyze_limit

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method == "OPTIONS" or request.url.path in _EXEMPT_PATHS:
            return await call_next(request)

        key = _client_key(request)
        is_analyze = request.url.path == _ANALYZE_PATH

        async with self._lock:
            allowed = self._default_store.try_acquire(key)
            if allowed and is_analyze:
                allowed = self._analyze_store.try_acquire(key)
            store = self._analyze_store if is_analyze else self._default_store
            limit = self._analyze_limit if is_analyze else self._default_limit
            remaining = store.remaining(key)
            retry_after = store.retry_after_seconds(key)

        if not allowed:
            return JSONResponse(
                status_code=429,
                media_type="application/problem+json",
                content={
                    "type": "https://project.example/problems/rate-limited",
                    "title": "Too many requests",
                    "status": 429,
                    "detail": (
                        "Rate limit exceeded for this client. Retry after the indicated interval."
                    ),
                    "instance": request.url.path,
                    "request_id": "req_00000000",
                    "code": "RATE_LIMITED",
                },
                headers={
                    "Retry-After": str(retry_after or 1),
                    "RateLimit-Limit": str(limit),
                    "RateLimit-Remaining": str(remaining),
                    "RateLimit-Reset": str(retry_after or 1),
                },
            )

        response = await call_next(request)
        response.headers["RateLimit-Limit"] = str(limit)
        response.headers["RateLimit-Remaining"] = str(remaining)
        response.headers["RateLimit-Reset"] = str(retry_after or 1)
        return response
