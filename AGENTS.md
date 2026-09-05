# Agent implementation guide

This file governs coding agents working in this repository.

## Source-of-truth order

When documents disagree, use this priority:

1. `docs/PRD.md` for product behavior and MVP 1 scope.
2. `docs/ARCHITECTURE.md` for boundaries and dependencies.
3. `docs/API.md` for the external contract.
4. `docs/DESIGN.md` for user experience and presentation.
5. `docs/ROADMAP.md` for future intent only.

Do not implement roadmap items unless the task explicitly promotes them into the current scope.

## Before coding a feature

Create or update the following artifacts for the affected feature:

- **SDD**: design, components, interfaces, alternatives and operational behavior.
- **TDD**: test strategy, fixtures, cases, false-positive/false-negative risks and acceptance mapping.
- **RDD**: research record for uncertain external standards, OCR choices, C2PA behavior or financial algorithms.
- **ADR**: one file under `docs/adr/` for irreversible or cross-cutting decisions.

Suggested feature location:

```text
docs/features/<feature-name>/
├── SDD.md
├── TDD.md
└── RDD.md
```

## MVP 1 invariants

- Never return `is_real`, `is_fake`, `authentic` or equivalent absolute verdicts.
- Never infer authenticity from missing metadata or missing C2PA.
- A valid AI-generation provenance claim is a critical risk signal, not proof about the underlying bank transaction.
- `risk_score` and `confidence_score` are separate concepts.
- The score must be deterministic for identical normalized analyzer outputs and ruleset version.
- Every score contribution must map to an explainable `ValidationSignal`.
- The web client must display the limitation that only bank reconciliation confirms payment.
- The API must remain consumable without browser state by workflow-automation tools, bots and generic HTTP clients.
- No database or durable receipt storage in MVP 1.
- No paid LLM or image-model dependency in the critical path.

## Architecture rules

- Keep a modular monolith; do not introduce microservices.
- Domain and application code must not import FastAPI, PaddleOCR, ExifTool, OpenCV or storage implementations.
- Analyzer ports return typed domain results; adapters translate tool-specific output.
- Orchestration may run independent analyzers concurrently with bounded concurrency.
- The risk engine consumes normalized signals, never raw framework responses.
- Frontend scoring is presentation only; the API response is authoritative.
- API models are versioned and use `snake_case` JSON.

## Test expectations

Each behavior must be traceable to a PRD requirement and include:

- Unit tests for financial algorithms and scoring.
- Contract tests for OpenAPI examples and error responses.
- Integration tests for analyzer adapters using deterministic fixtures.
- End-to-end tests for upload, processing, result and failure flows.
- Privacy tests proving raw files and sensitive OCR output do not appear in logs.
- Regression fixtures for malformed, oversized and adversarial images.

Do not label an assessment algorithm accurate without an explicitly versioned evaluation dataset and documented metrics.

## Data and fixture policy

- Prefer synthetic receipts and fully anonymized fixtures.
- Never commit real receipts containing personal or banking data.
- Record fixture provenance and expected signals in a sidecar manifest.
- Keep exact scorer inputs in tests so score changes are deliberate and reviewable.

## Definition of done

A change is complete only when:

- Relevant PRD acceptance criteria pass.
- SDD/TDD/RDD are updated when applicable.
- Unit, integration and contract tests pass.
- OpenAPI documentation reflects the behavior.
- Privacy and cleanup paths are verified.
- The design works on mobile and desktop and meets basic accessibility checks.
- No future-phase capability was introduced implicitly.
