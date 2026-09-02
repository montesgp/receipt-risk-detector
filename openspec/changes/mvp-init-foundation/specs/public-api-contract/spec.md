# Public API Contract Specification

## Purpose

Versioned JSON API, CORS allowlist, no-auth-in-MVP1, consumable by browser, n8n, bots, and generic HTTP clients without browser-session coupling (PRD FR-009, FR-010, NFR-002; proposal D4).

## Requirements

### Requirement: Versioned public endpoints
The API SHALL expose `GET /health`, `GET /ready`, `GET /version`, `POST /v1/receipts/analyze`, `GET /openapi.json`, `GET /docs`, `GET /redoc`, with the analysis endpoint synchronous (FR-009).

#### Scenario: Analysis endpoint works without session
- GIVEN a client with no cookies, browser state, or access token
- WHEN it calls `POST /v1/receipts/analyze` with a valid image
- THEN the API returns a `200` result without requiring authentication

#### Scenario: Version endpoint reports engine and ruleset
- GIVEN a client calls `GET /version`
- WHEN the response is returned
- THEN it includes `engine_version` and `ruleset_version`

### Requirement: No authentication in MVP 1
The API MUST NOT require API keys, OAuth, or any credential to call public endpoints in MVP 1 (PRD §5 non-goal; D4 reaffirmation).

#### Scenario: Unauthenticated third-party call succeeds
- GIVEN an n8n HTTP Request node with no credentials configured
- WHEN it submits a binary multipart image to `/v1/receipts/analyze`
- THEN the request is processed and returns structured JSON (FR-010)

### Requirement: CORS allowlist
The API MUST enforce a configurable CORS allowlist so browser-origin requests are restricted while server-side clients remain unaffected (D4).

#### Scenario: Allowed browser origin
- GIVEN the web client's origin is on the CORS allowlist
- WHEN it calls the API from a browser
- THEN the response includes the matching `Access-Control-Allow-Origin` header

#### Scenario: Disallowed browser origin
- GIVEN an origin not on the CORS allowlist
- WHEN a browser sends a cross-origin request
- THEN the browser blocks the response per standard CORS enforcement

### Requirement: Stable error contract
All errors MUST return a stable problem-details format with a documented status code (NFR-002).

#### Scenario: Documented error shape
- GIVEN any request that fails validation or processing
- WHEN the API responds
- THEN the body follows the problem-details format including `type`, `title`, `status`, and `instance`

## Key Learnings

1. D4 defines "API independence" as CORS allowlist + versioned contract + rate limiting + no browser-session coupling, not as authentication.
2. Server-side automation (n8n, bots, backends) is an explicitly intended consumer class, not an edge case.
