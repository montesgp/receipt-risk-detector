# TDD: Receipt Analysis Implementation

> OpenSpec is the source of truth for task tracking. This file is an `AGENTS.md`-required mirror for
> discoverability; it summarizes and links rather than duplicates. Do not edit task text here — edit
> `openspec/changes/receipt-analysis-implementation/tasks.md` instead.

## Test strategy (see `design.md` "Testing Strategy" for the full table)

Strict TDD (RED → GREEN → REFACTOR) is enforced for every behavior. Test layout under `apps/api/tests/`:

| Layer | Location | What it proves |
| --- | --- | --- |
| Unit — domain | `tests/unit/test_{ruleset,scoring,assessment}.py` | Pure scoring arithmetic, evidence-coverage/`INCONCLUSIVE`, `FraudAssessment` assembly — no I/O |
| Unit — application | `tests/unit/test_analyze_receipt.py` | `_guarded` never aborts on exception/timeout; whole-request budget exhaustion; cleanup in `finally` |
| Unit — API adapter | `tests/unit/test_api_schemas.py`, `test_router.py`, `test_api_error_contract.py` | Response shape vs `docs/API.md` §3; forbidden-verdict-vocabulary; every reachable `problem+json` error code |
| Unit — rate limiting | `tests/unit/test_rate_limit.py`, `test_rate_limit_middleware.py` | Token-bucket algorithm in isolation; ASGI 429 contract, exempt paths, headers |
| Unit — privacy | `tests/unit/test_log_privacy.py` | No raw bytes / unmasked CBU-CUIT-amount in logs, success and failure paths |
| Integration — E2E | `tests/integration/test_analyze_endpoint_e2e.py` | Real HTTP route + real ingestion + real scoring, against committed `samples/` fixtures |

## Traceability (slice 4 tasks → spec scenarios)

| Task range | Spec scenario / locked decision |
| --- | --- |
| 4.1–4.10 | `receipt-analysis` "Deterministic score for identical input"; whole-request `INCONCLUSIVE` coverage (proposal.md locked decision) |
| 4.11–4.12 | `receipt-analysis` FR-007 (`classification`, `risk_score`, `confidence_score`, `recommended_action`, `ruleset_version`, `engine_version`) |
| 4.13–4.17 | design.md "a failed analyzer produces a signal, never an aborted request" |
| 4.18–4.22 | `public-api-contract` field-for-field shape; "No absolute verdict" scenario; documented `problem+json` error codes |
| 4.23–4.24 | design.md "router module absent until slice 4" — first public registration |
| 4.25–4.26 | `data-retention` log-masking scenario |

## Known deviations from the literal 28-task list

- The `api-rate-limiting` capability spec (already frozen, referenced by `docs/API.md` §5b) is
  implemented in this slice (`adapters/api/rate_limit/`, `adapters/api/middleware/rate_limit.py`)
  even though it is not itemized as a separate numbered task in `tasks.md`'s Slice 4 section. It was
  added because `POST /v1/receipts/analyze` is publicly reachable for the first time in this slice and
  the spec's "In-process per-IP token bucket" requirement applies from first exposure, not a later
  change.
- `ANALYZER_UNAVAILABLE` (503) from `docs/API.md` §5's error table is documented but intentionally
  unreachable through the router: design.md's locked decision routes every analyzer failure into a
  `ValidationSignal` (never a request abort), so no code path returns a request-level 503 for a
  degraded analyzer. Recorded as a known contract gap, not silently dropped.
