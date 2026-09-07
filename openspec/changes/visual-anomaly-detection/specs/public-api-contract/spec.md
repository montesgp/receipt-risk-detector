# Delta for Public API Contract

## ADDED Requirements

### Requirement: Analyzer readiness roster
The `/ready` and `/version` endpoints SHALL report one entry per analyzer (name and version), and that roster MUST include a `vision` entry alongside the existing `ocr`, `metadata`, and `provenance` entries, in the same shape.

#### Scenario: Ready endpoint reports four analyzers
- GIVEN a client calls `GET /ready`
- WHEN the response is returned
- THEN it lists four analyzer entries — `ocr`, `metadata`, `provenance`, `vision` — each with a name and version, matching the existing entries' shape

#### Scenario: Version endpoint reports the vision analyzer
- GIVEN a client calls `GET /version`
- WHEN the response is returned
- THEN it includes `engine_version`, `ruleset_version`, and a `vision` analyzer entry alongside `ocr`, `metadata`, and `provenance`

### Requirement: Visual anomaly signal on the wire
`POST /v1/receipts/analyze` responses SHALL support the `VISUAL_ANOMALY_DETECTED` signal code under category `VISUAL` in the `signals` array, using the same documented signal schema as existing codes.

#### Scenario: Visual anomaly signal is documented in the schema
- GIVEN the published `openapi.json` or `docs/API.md` signal reference
- WHEN a client inspects the signal code enum
- THEN `VISUAL_ANOMALY_DETECTED` and category `VISUAL` are present alongside existing codes and categories

## Key Learnings

1. `/ready` and `/version` share the same four-entry analyzer roster shape, so adding `vision` is additive to both endpoints, not a breaking change.
2. The new signal code is documented in the same enum as existing codes rather than as a special "AI" category, keeping the wire contract uniform.
