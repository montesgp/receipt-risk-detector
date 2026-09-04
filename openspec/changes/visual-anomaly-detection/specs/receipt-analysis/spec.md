# Delta for Receipt Analysis

## ADDED Requirements

### Requirement: Visual inspection
The system SHALL run a fourth analyzer that embeds the receipt image with a frozen MobileNetV3 model and compares it by cosine distance against a bundled reference set of legitimate receipt renders, without inferring authenticity — only distributional outlier status.

#### Scenario: Visual outlier flagged
- GIVEN a receipt image whose embedding's cosine distance to the reference set exceeds the documented threshold
- WHEN visual inspection completes
- THEN a `VISUAL_ANOMALY_DETECTED` signal is emitted with category `VISUAL` and severity `LOW` or `MEDIUM`, never contributing to a critical verdict on its own

#### Scenario: Vision listed first in signal ordering
- GIVEN an analysis that produces signals from more than one analyzer
- WHEN the response's `signals` list is assembled
- THEN any vision-analyzer signal appears first in that list; analyzer scheduling and concurrency are unaffected

#### Scenario: No outbound network calls during visual inspection
- GIVEN a submitted receipt image and a locally available vision model
- WHEN visual inspection runs
- THEN no outbound network connection is made, matching the existing zero-outbound-network guarantee for OCR

### Requirement: Vision analyzer graceful degradation
The system SHALL degrade the vision analyzer the same way as OCR, metadata, and provenance analyzers when it is unavailable or fails, without special-casing it.

#### Scenario: Missing vision weights degrade without failing analysis
- GIVEN the vision model weights are not configured or fail to load
- WHEN analysis runs
- THEN an `ANALYZER_UNAVAILABLE` pattern signal is emitted at info severity with weight 0, the vision role contributes 0 to evidence coverage, and the request still returns `200`

## MODIFIED Requirements

### Requirement: Explainable, deterministic scoring
The system MUST return `classification`, `risk_score` (0-100), `confidence_score` (0-100), `recommended_action`, ordered `signals`, `ruleset_version`, and `engine_version` (FR-007). The system MUST NOT return absolute authenticity verdicts (AGENTS.md invariant). The analyzer evidence-coverage weights used to compute `confidence_score` MUST sum to exactly 1.00 across the four analyzer roles (ocr, metadata, provenance, vision).
(Previously: evidence-coverage weighting was implicit and covered only three analyzer roles; adding vision rebalances the other three roles proportionally, which changes their prior `confidence_score` contribution.)

#### Scenario: Deterministic score for identical input
- GIVEN identical normalized evidence and ruleset version
- WHEN the risk engine scores twice
- THEN both runs produce the same `risk_score`, `confidence_score`, and `classification`

#### Scenario: No absolute verdict
- GIVEN any analysis outcome
- WHEN the response is generated
- THEN the response MUST NOT contain `is_real`, `is_fake`, `authentic`, `verified transfer`, or equivalent labels

#### Scenario: Evidence weights sum to one across four roles
- GIVEN the ruleset's analyzer evidence-coverage weights
- WHEN they are summed across ocr, metadata, provenance, and vision
- THEN the total equals exactly 1.00

### Requirement: Analysis latency budget
The system MUST complete the end-to-end upload → validate → preprocess → analyze → score → respond flow within the documented latency targets on the reference CPU and fixture set, including the vision analyzer's time budget (NFR-001).
(Previously: the latency budget covered three concurrent analyzers; it now accounts for a fourth concurrent analyzer with its own documented time budget.)

#### Scenario: Typical request meets p50 target
- GIVEN a supported receipt image submitted on the documented reference CPU and fixture set
- WHEN the request follows the normal upload-to-response flow with all four analyzers running concurrently
- THEN the median (p50) end-to-end analysis time is under 4 seconds (NFR-001)

#### Scenario: Slow request still meets p95 target and shows processing state
- GIVEN a supported receipt image whose analysis exceeds the p50 target
- WHEN the request runs past 300 ms without a response
- THEN the client shows a processing state, and the response still completes within the p95 target of 10 seconds (NFR-001)

## Key Learnings

1. Vision-first ordering is a signal-list presentation rule, not a scheduling change — all four analyzers still run concurrently in the existing task group.
2. Evidence-weight rebalancing is an intentional behavior change to `confidence_score` for existing analyzers, not a regression, so it is expressed as MODIFIED rather than ADDED.
