# API Rate Limiting Specification

## Purpose

Concrete per-IP token-bucket mechanism for abuse control, in-process and non-persistent, per NFR-003 and proposal decision D2.

## Requirements

### Requirement: In-process per-IP token bucket
The API MUST enforce rate limiting via an in-process, per-IP token-bucket algorithm implemented as FastAPI middleware, with no external persistence (NFR-003, D2).

#### Scenario: Default limit enforced
- GIVEN a client IP has not exceeded the default bucket (30 req/min)
- WHEN it makes a request within that budget
- THEN the request proceeds normally

#### Scenario: Analysis endpoint stricter limit
- GIVEN a client IP calling `POST /v1/receipts/analyze` more than 10 times within one minute
- WHEN the 11th request arrives
- THEN the API returns `429` with problem-details and a `Retry-After` header

### Requirement: Env-configurable limits
Rate limit thresholds MUST be configurable via environment variables without code changes (D2).

#### Scenario: Overridden default via environment
- GIVEN an operator sets a custom requests-per-minute env variable
- WHEN the service starts
- THEN the token bucket uses the configured value instead of the default

### Requirement: Documented single-instance limitation
The system MUST document that the in-process token bucket resets on restart and is not shared across multiple instances, as an accepted MVP1 limitation, not a silent gap (D2, proposal Risks).

#### Scenario: Restart resets counters
- GIVEN a client has partially consumed its rate-limit bucket
- WHEN the service process restarts
- THEN the client's bucket resets to full capacity, and this behavior is documented as an MVP1 limitation

#### Scenario: Multi-instance deployment not rate-limit-safe
- GIVEN the service is deployed as more than one running instance behind a load balancer
- WHEN traffic is distributed across instances
- THEN each instance enforces its own independent bucket, and documentation states this is not multi-instance-safe until deferred with the auth phase

## Key Learnings

1. D2 explicitly rejects Redis/gateway-based limiting because MVP1 forbids persistence and runs as a single modular monolith container.
2. The proposal requires the reset-on-restart and per-instance limitation to be an explicit documented scenario, not an implicit gap.
