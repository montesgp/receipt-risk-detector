# RDD: Receipt Analysis Implementation

> OpenSpec is the source of truth for requirements. This file is an `AGENTS.md`-required mirror for
> discoverability; it summarizes and links rather than duplicates. Do not edit requirement text here —
> edit `openspec/specs/receipt-analysis/spec.md` (and the other referenced capability specs) instead.

## Requirements covered by this change

| Requirement | Spec | Slice |
| --- | --- | --- |
| Image submission (FR-001) | `receipt-analysis` | 1 |
| Safe preprocessing (FR-002) | `receipt-analysis` | 1 |
| Metadata and provenance inspection (FR-003, FR-004) | `receipt-analysis` | 2 |
| Local OCR extraction (FR-005) | `receipt-analysis` | 3b |
| Financial validation (FR-006) | `receipt-analysis` | 3a |
| Explainable, deterministic scoring (FR-007) | `receipt-analysis` | 4 |
| Public API contract | `public-api-contract` | 4 |
| Rate limiting (NFR-003) | `api-rate-limiting` | 4 |
| Temp file cleanup / no raw content in logs (FR-011) | `data-retention` | 1, 4 |

Out of scope for this change (see `proposal.md`): PDF input, persistence, accounts, batch analysis,
the SvelteKit results UI (FR-008), tuned scoring weights, and a documented reference-CPU benchmark.

## Product invariant carried through every slice

The system MUST NOT return `is_real`, `is_fake`, `authentic`, `verified transfer`, or an equivalent
absolute verdict (AGENTS.md invariant; `receipt-analysis` spec's "No absolute verdict" scenario).
Enforced structurally in slice 4 by `tests/unit/test_api_schemas.py::
test_response_never_contains_forbidden_verdict_vocabulary` scanning the full serialized response.

## Success criteria status (proposal.md)

See `openspec/changes/receipt-analysis-implementation/proposal.md` § Success Criteria for the full
checklist. Slice 4 closes the remaining items: `POST /v1/receipts/analyze` returns a full
`FraudAssessment` with `ruleset_version`/`engine_version`; identical input + ruleset version yields an
identical `(risk_score, confidence_score, classification)` triple; a core-field extraction failure
produces `CORE_FIELD_EXTRACTION_FAILED` contributing to `risk_score` rather than a silent gap or a
forced `INCONCLUSIVE`; `INCONCLUSIVE` triggers only on whole-request low evidence coverage.
