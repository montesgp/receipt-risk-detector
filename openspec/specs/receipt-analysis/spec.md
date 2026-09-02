# Receipt Analysis Specification

## Purpose

Core upload → validate → preprocess → analyze → score → respond flow for a single transfer-receipt image (PRD FR-001–FR-008).

## Requirements

### Requirement: Image submission
The system MUST accept one `JPEG`, `PNG`, or `WebP` image via drag-and-drop, file selection, or `multipart/form-data` (FR-001).

#### Scenario: Valid image accepted
- GIVEN a JPEG under the configured max size (10 MB default)
- WHEN it is submitted via the web client or API
- THEN the request is accepted for processing without requiring an account

#### Scenario: Oversized or corrupt image rejected
- GIVEN an image exceeding the max size, or content that fails decode
- WHEN it is submitted
- THEN the system returns a documented `4xx` error and does not proceed to analysis

### Requirement: Safe preprocessing
The system MUST validate dimensions, pixel count, and decodability before analysis, and MUST clean up temp files (FR-002).

#### Scenario: Excessive dimensions rejected
- GIVEN an image exceeding configured dimension/pixel limits
- WHEN preprocessing runs
- THEN the request is rejected with a `4xx` error before analyzers run

#### Scenario: Temp files removed on all paths
- GIVEN a submitted image, valid or invalid
- WHEN processing finishes, succeeds, or fails
- THEN temporary files are deleted and raw file content never appears in logs

### Requirement: Metadata and provenance inspection
The system SHALL inspect embedded metadata and MAY detect C2PA/Content Credentials claims, without inferring authenticity from absence (FR-003, FR-004).

#### Scenario: Missing metadata is neutral
- GIVEN an image with no embedded metadata
- WHEN metadata inspection runs
- THEN the absence MUST NOT reduce risk score or imply authenticity

#### Scenario: Valid AI-generated provenance claim
- GIVEN an image carrying a valid C2PA claim of `VALID_AI_GENERATED_CLAIM`
- WHEN provenance inspection completes
- THEN the result is reported as a critical risk signal, not as proof about bank settlement

### Requirement: Local OCR extraction
The system SHALL run OCR locally, without paid per-request model tokens, extracting amount, date, names, CBU/CVU, CUIT/CUIL, institution, and operation ID when visible (FR-005).

#### Scenario: Field extracted with confidence
- GIVEN a receipt image with a visible amount field
- WHEN OCR completes
- THEN the amount is returned with raw text, normalized value, and extraction confidence

### Requirement: Financial validation
The system MUST apply deterministic validators to extracted values: CBU/CVU and CUIT/CUIL check digits, monetary normalization, date bounds, contradiction detection (FR-006).

#### Scenario: Invalid CBU check digit
- GIVEN an extracted CBU that fails its check-digit algorithm
- WHEN validation runs
- THEN a validation signal reports the failure with severity and evidence

### Requirement: Explainable, deterministic scoring
The system MUST return `classification`, `risk_score` (0-100), `confidence_score` (0-100), `recommended_action`, ordered `signals`, `ruleset_version`, and `engine_version` (FR-007). The system MUST NOT return absolute authenticity verdicts (AGENTS.md invariant).

#### Scenario: Deterministic score for identical input
- GIVEN identical normalized evidence and ruleset version
- WHEN the risk engine scores twice
- THEN both runs produce the same `risk_score`, `confidence_score`, and `classification`

#### Scenario: No absolute verdict
- GIVEN any analysis outcome
- WHEN the response is generated
- THEN the response MUST NOT contain `is_real`, `is_fake`, `authentic`, `verified transfer`, or equivalent labels

### Requirement: Results UI
The web client MUST show score, confidence, a plain-language limitation statement, ordered evidence, masked sensitive fields by default, and a manual-reconciliation checklist (FR-008).

#### Scenario: Limitation statement always visible
- GIVEN any completed analysis
- WHEN results render
- THEN a statement clarifies that low risk does not confirm the transfer reached the account

### Requirement: Analysis latency budget
The system MUST complete the end-to-end upload → validate → preprocess → analyze → score → respond flow within the documented latency targets on the reference CPU and fixture set (NFR-001).

#### Scenario: Typical request meets p50 target
- GIVEN a supported receipt image submitted on the documented reference CPU and fixture set
- WHEN the request follows the normal upload-to-response flow
- THEN the median (p50) end-to-end analysis time is under 4 seconds (NFR-001)

#### Scenario: Slow request still meets p95 target and shows processing state
- GIVEN a supported receipt image whose analysis exceeds the p50 target
- WHEN the request runs past 300 ms without a response
- THEN the client shows a processing state, and the response still completes within the p95 target of 10 seconds (NFR-001)

## Key Learnings

1. FR-007's classification bands and FR-008's UI wording both encode the "evidence over verdicts" product principle from PRD §3.
2. FR-002's cleanup requirement and FR-011's retention requirement overlap; retention rules live in the dedicated `data-retention` capability.
