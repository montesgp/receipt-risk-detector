# SDD: Receipt Analysis Implementation

> OpenSpec is the source of truth for this change. This file is an `AGENTS.md`-required mirror for
> discoverability; it summarizes and links rather than duplicates. Do not edit requirement text here —
> edit `openspec/changes/receipt-analysis-implementation/` instead. See
> `openspec/changes/receipt-analysis-implementation/{proposal.md,design.md}` for full content.

## Summary

Implements GitHub issue [#1](https://github.com/montesgp/receipt-risk-detector/issues/1): the full
upload → validate → preprocess → analyze → score → respond pipeline for a single Argentine transfer
receipt image, exposing `POST /v1/receipts/analyze` publicly for the first time (slice 4 of 4).

## Capability specs (source of truth)

| Capability | Spec | Covers |
| --- | --- | --- |
| `receipt-analysis` | `openspec/specs/receipt-analysis/spec.md` | FR-001–FR-008 |
| `public-api-contract` | `openspec/specs/public-api-contract/spec.md` | `docs/API.md` §1–§7 |
| `api-rate-limiting` | `openspec/specs/api-rate-limiting/spec.md` | NFR-003 |
| `data-retention` | `openspec/specs/data-retention/spec.md` | FR-011 |

No new/modified capability requirements: this change implements the frozen specs above without
altering requirements (proposal.md "Capabilities").

## Design decisions (see `design.md` for full rationale and alternatives)

| Decision | Where documented |
| --- | --- |
| Versioned ruleset as a frozen declarative data module (`domain/ruleset.py` + `domain/rulesets/*.py`), not hardcoded weights | `design.md` "Architecture Decisions" |
| `/v1/receipts/analyze` unregistered until slice 4 (404), not a `501` stub | `design.md` "Architecture Decisions" |
| Analyzer ports are `async`; adapters offload blocking work to a worker thread via `anyio` | `design.md` "Architecture Decisions" |
| A failed analyzer produces a `ValidationSignal`, never an aborted request | `design.md` "Architecture Decisions"; `application/analyze_receipt.py::_guarded` |
| `INCONCLUSIVE` is a single whole-request evidence-coverage threshold, never per-analyzer | `design.md` "Architecture Decisions"; `domain/scoring.py` |

## Architecture constraints respected

Per `AGENTS.md` / `docs/ARCHITECTURE.md` §5: one-way dependency `adapters → application → domain`.
`domain/` and `application/` never import FastAPI, Starlette, PaddleOCR, ExifTool, OpenCV, or C2PA —
enforced by ruff's `TID251` banned-import list and verified for this slice by a direct grep over
`domain/` and `application/` for framework imports (zero matches).

## Slice 4 file map (risk engine + response assembly)

| File | Role |
| --- | --- |
| `domain/ruleset.py`, `domain/rulesets/v2026_09_01.py` | `ScoringRuleset` dataclass + the versioned MVP1 default |
| `domain/scoring.py` | Pure `score()`: risk-score arithmetic, evidence-coverage, `INCONCLUSIVE` |
| `domain/assessment.py` | `FraudAssessment` assembly, `recommended_action` mapping |
| `application/analyze_receipt.py` | `AnalyzeReceiptUseCase`: ingestion → bounded-concurrency fan-out → financial validation → scoring |
| `application/clock.py` | `Clock` protocol / `SystemClock`, injectable for deterministic duration tests |
| `adapters/api/{schemas,mappers,errors,dependencies,router}.py` | FastAPI route, Pydantic models, domain→transport mapping, `problem+json` error mapping |
| `adapters/api/rate_limit/`, `adapters/api/middleware/rate_limit.py` | In-process per-IP token-bucket rate limiting (`api-rate-limiting` spec) |
| `bootstrap/app.py` | Registers the router (first public exposure), `/ready`, `/version` |

See `design.md` § File Changes for the full authoritative list across all 4 slices.
