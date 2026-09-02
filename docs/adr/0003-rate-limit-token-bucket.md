# ADR 0003: In-process per-IP token bucket for rate limiting

## Status

Accepted

## Context

`docs/PRD.md` NFR-003 requires rate limiting but did not name a concrete mechanism. MVP1 forbids
durable persistence (`docs/PRD.md` §5 non-goals; `data-retention` capability) and runs as a single
modular-monolith container (`docs/ARCHITECTURE.md` §1), which rules out shared external state as a
default requirement. A concrete mechanism, its placement in the request pipeline, and its
header-trust behavior all need to be decided before implementation can start (proposal decision D2;
`openspec/changes/mvp-init-foundation/design.md` DD5, DD6).

## Decision

1. **Algorithm**: per-key token bucket with lazy refill on a monotonic clock, no background task. Two
   independent buckets are evaluated per analysis request — `default` (30 req/min) and `analyze`
   (10 req/min) — and the analysis route must satisfy both.
2. **Placement**: pure ASGI middleware registered in the composition root, running before body
   parsing, so an abusive client is rejected before a multipart upload streams. This is
   `apps/api/src/receipt_risk/adapters/api/middleware/rate_limit.py`, wrapped by CORS middleware so a
   `429` still carries `Access-Control-Allow-Origin`. The pure algorithm lives in
   `adapters/api/rate_limit/bucket.py` with no framework import, so it is unit-testable without ASGI.
3. **Key selection**: key on the socket peer address by default. Only trust `X-Forwarded-For` when
   `RATE_LIMIT_TRUST_FORWARDED_FOR=true` is explicitly set, in which case use the leftmost entry.
4. **Memory bound**: an LRU map capped at `RATE_LIMIT_MAX_TRACKED_KEYS` (default 10 000), swept lazily
   when idle longer than two refill windows.
5. **Concurrency**: a single `asyncio.Lock` guards the map — correct for one uvicorn worker on one
   event loop, explicitly incorrect for multiple workers (documented limitation, not silently
   assumed).

### Alternatives considered

- **FastAPI `Depends`**: rejected — it runs only after multipart streaming has started, so a
  rate-limited client still uploads up to 10 MB before rejection, and it needs per-route repetition.
- **Redis-backed limiting**: rejected — Redis is durable shared state, contradicting the no-persistence
  invariant and adding an operational dependency the single-container MVP1 does not otherwise need.
- **Reverse-proxy / gateway limiting**: rejected as the default — proxy configuration is not portable
  across Railway's `dev`/`main` environments and would live outside this repository's source of truth.
  Reverse-proxy limiting remains available as optional deployment hardening on top of this middleware.
- **Always trusting `X-Forwarded-For`**: rejected — any client can spoof the header and evade the
  limit entirely.
- **Never trusting `X-Forwarded-For`**: rejected for the Railway deployment — every request would key
  to the shared edge IP, so one abusive client would rate-limit every other user.

## Consequences

- The mechanism is fully specified in
  `openspec/changes/mvp-init-foundation/specs/api-rate-limiting/spec.md` and documented for API
  consumers in `docs/API.md` §5b, including the `429` problem-details body and
  `RateLimit-Limit/Remaining/Reset` / `Retry-After` headers.
- **Accepted limitation**: state lives in process memory. It resets on every restart/redeploy and is
  not shared across instances, so horizontal scaling multiplies the effective limit by instance count.
  This is abuse damping, not a security control against distributed abuse. It is documented, not
  silent, in `docs/API.md` §5b and `docs/ARCHITECTURE.md` §11. Shared-store limiting is deferred to
  the authentication phase (`docs/ROADMAP.md` Phase 4).
- `RATE_LIMIT_TRUST_FORWARDED_FOR` defaulting to `true` specifically in Railway environments (versus
  requiring explicit operator configuration everywhere) is an open question deferred to the future
  `repo-github-setup` change, which owns the environment template
  (`openspec/changes/mvp-init-foundation/design.md`, Open Questions).
- The threat-matrix cases for this boundary (spoofed `X-Forwarded-For`, IP rotation against the LRU
  cap, clock non-monotonicity, preflight bypass) carry no runtime surface in this documentation-only
  change and must be re-evaluated as an applicable matrix in the implementation change that ships the
  middleware (`design.md` Threat Matrix).

## References

- `openspec/changes/mvp-init-foundation/specs/api-rate-limiting/spec.md`
- `openspec/changes/mvp-init-foundation/design.md` (DD5, DD6, Rate-Limiting Design)
- `docs/API.md` §5b
- `docs/ARCHITECTURE.md` §11
- `openspec/changes/mvp-init-foundation/proposal.md` decision D2
