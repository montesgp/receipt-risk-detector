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

The system MUST recognize an algorithmic-source (AI-generation) claim whether `digitalSourceType` appears as the flat `Iptc4xmpExt:DigitalSourceType` field (claim-v1 shape) or nested inside `assertions[].data.actions[].digitalSourceType` (claim-v2 shape). The algorithmic-source marker set MUST include `compositesynthetic`.

The system MUST classify a recognized algorithmic-source claim by `validation_status` into exactly one of three outcomes: (a) an empty `validation_status` emits `VALID_AI_GENERATED_CLAIM`; (b) a `validation_status` whose every entry is on the allowlist (currently only `signingCredential.untrusted`) emits `AI_GENERATED_CLAIM_UNTRUSTED_SIGNER` (category PROVENANCE, severity CRITICAL, confidence 0.85); (c) a `validation_status` containing any entry not on the allowlist — including `signingCredential.expired` or any unrecognized code — emits `PROVENANCE_VALIDATION_FAILED` (MEDIUM, confidence 0.60), even if other entries in the same array are allowlisted.
(Previously: only the flat `Iptc4xmpExt:DigitalSourceType` field was read, no `compositesynthetic` marker existed, and any non-empty `validation_status` unconditionally produced `PROVENANCE_VALIDATION_FAILED` with no untrusted-signer tier.)

#### Scenario: Missing metadata is neutral
- GIVEN an image with no embedded metadata
- WHEN metadata inspection runs
- THEN the absence MUST NOT reduce risk score or imply authenticity

#### Scenario: Valid AI-generated provenance claim (claim-v1 flat field, unchanged)
- GIVEN an image carrying a valid C2PA claim of `VALID_AI_GENERATED_CLAIM` via the flat `Iptc4xmpExt:DigitalSourceType` field and empty `validation_status`
- WHEN provenance inspection completes
- THEN the result is reported as a critical risk signal, not as proof about bank settlement

#### Scenario: Claim-v2 nested actions recognized as algorithmic source
- GIVEN a manifest with `digitalSourceType` present only inside `assertions[].data.actions[].digitalSourceType` (claim-v2 shape) and absent from the flat field
- WHEN provenance inspection runs
- THEN the claim is recognized as an algorithmic-source claim, identically to the flat-field case

#### Scenario: Untrusted signer alone yields a distinct CRITICAL signal
- GIVEN a recognized algorithmic-source claim whose `validation_status` contains only `signingCredential.untrusted`
- WHEN provenance inspection runs
- THEN the system emits `AI_GENERATED_CLAIM_UNTRUSTED_SIGNER` (PROVENANCE, CRITICAL, confidence 0.85) instead of `PROVENANCE_VALIDATION_FAILED`

#### Scenario: Any non-allowlisted status code keeps the strict bucket
- GIVEN a recognized algorithmic-source claim whose `validation_status` contains `signingCredential.expired`, an unrecognized code, or a mix of `signingCredential.untrusted` plus one non-allowlisted code
- WHEN provenance inspection runs
- THEN the system emits `PROVENANCE_VALIDATION_FAILED` (MEDIUM, confidence 0.60), unchanged from prior behavior

#### Scenario: Existing claim-v1 and non-claim behaviors unchanged
- GIVEN any of: a flat-field claim-v1 manifest, no manifest present, an undecodable manifest, a manifest whose source type is not algorithmic, or a manifest with clean (empty) `validation_status`
- WHEN provenance inspection runs
- THEN the reported signal for each case is byte-for-byte identical to pre-change behavior

### Requirement: Local OCR extraction
The system SHALL run OCR locally, without paid per-request model tokens, extracting amount, date, names, CBU/CVU, CUIT/CUIL, institution, and operation ID when visible (FR-005).

The system MUST detect and normalize the four core financial fields — `amount`, `destination_cbu`, `cuit`, `date_time` — by validating candidate values against each field's domain-specific shape/checksum, independent of the issuing bank or wallet's label wording, whether a label is present at all, or the label's layout relative to the value (above, inline, or absent). Detection MUST NOT depend on matching a fixed label vocabulary:
- `amount`: any currency-pattern substring (AR `.`/`,` and US `,`/`.` separator conventions), normalized via `normalize_amount`.
- `destination_cbu` / `cuit`: any boundary-anchored 22-digit / 11-digit digit run, shape-checked via `validate_cbu` / `validate_cuit`.
- `date_time`: any recognizable date/time text — numeric with common separators, day-month-name in Spanish or English, ISO 8601, 12h/24h clock, with or without seconds/timezone, tolerant of single-character OCR digit-for-letter typos in month names — normalized to an ISO 8601 string, backstopped by the existing plausibility-bounds check.

When a receipt contains two structurally valid CUIT/CBU candidates (an origin and a destination), the system MUST collapse them to exactly one `ExtractedField` per field name, chosen by: (1) proximity to a destination/beneficiary-style keyword when any candidate has one nearby; else (2) positional order, treating the first-appearing candidate as origin and the second as destination. The system MUST NOT emit two `ExtractedField` entries sharing the same name for the same field slot.

When a field slot has exactly one structurally valid candidate, the system MUST surface it (populate `normalized`) regardless of whether its checksum passes. Checksum validity MUST gate selection only when disambiguating among multiple candidates for the same slot, never a lone candidate — checksum-failure signaling stays the Financial validation requirement's job.

#### Scenario: Field extracted with confidence
- GIVEN a receipt image with a visible amount field
- WHEN OCR completes
- THEN the amount is returned with raw text, normalized value, and extraction confidence

#### Scenario: Same field extracted despite different label wording
- GIVEN two receipts encoding the same destination CBU value, one labeled "CBU Destino", the other labeled "CVU", and a third with no label at all
- WHEN core-field extraction runs on each
- THEN all three produce an equivalent `destination_cbu` field with the same `normalized` value

#### Scenario: Inline label:value on a single line
- GIVEN an OCR text box containing `"CUIT: 20-12345678-9"` on one line rather than a label box paired with a value box below it
- WHEN core-field extraction runs
- THEN the `cuit` field is extracted with `normalized` populated

#### Scenario: Two CUIT/CBU pairs disambiguated by keyword proximity
- GIVEN a receipt with two valid CBU candidates, one near the text "origen"/"remitente" and the other near "destino"/"beneficiario"
- WHEN core-field extraction runs
- THEN exactly one `destination_cbu` field is returned, matching the candidate near the destination-style keyword

#### Scenario: Two CUIT/CBU pairs disambiguated by position when no keyword exists
- GIVEN a receipt with two valid CBU candidates and no destination/origin keyword near either
- WHEN core-field extraction runs
- THEN exactly one `destination_cbu` field is returned, matching the second-appearing (lower-on-page) candidate

#### Scenario: Sole checksum-failing candidate is still surfaced
- GIVEN a receipt with exactly one 22-digit CBU-shaped candidate whose check digit is deliberately wrong, and no other CBU-shaped candidate
- WHEN core-field extraction runs
- THEN `destination_cbu.normalized` is populated with that candidate's value (checksum failure detection remains the Financial validation requirement's job, producing `INVALID_CBU_CHECK_DIGIT` unchanged)

#### Scenario: Stray digit run ignored when a better candidate exists
- GIVEN a receipt with one valid 11-digit CUIT candidate and one unrelated 11-digit number (e.g. an order/reference ID) that fails the CUIT checksum
- WHEN core-field extraction runs
- THEN the `cuit` field's `normalized` value is the checksum-valid candidate, never the failing one

#### Scenario: Wide date/time format coverage including an OCR-typo month name
- GIVEN OCR text boxes with dates in varied formats — `"15/03/2026 14:30"`, `"15 de marzo de 2026"`, `"2026-03-15T14:30:00"`, and `"15 de mar20 de 2026"` (digit-for-letter typo in "marzo")
- WHEN core-field extraction runs on each
- THEN each produces a `date_time` field normalized to the same ISO 8601 instant, provided it falls within the plausibility-bounds window

### Requirement: Financial validation
The system MUST apply deterministic validators to extracted values: CBU/CVU and CUIT/CUIL check digits, monetary normalization, date bounds, contradiction detection (FR-006).

#### Scenario: Invalid CBU check digit
- GIVEN an extracted CBU that fails its check-digit algorithm
- WHEN validation runs
- THEN a validation signal reports the failure with severity and evidence

### Requirement: Explainable, deterministic scoring
The system MUST return `classification`, `risk_score` (0-100), `confidence_score` (0-100), `recommended_action`, ordered `signals`, `ruleset_version`, and `engine_version` (FR-007). The system MUST NOT return absolute authenticity verdicts (AGENTS.md invariant).

`evidence_coverage` MUST distinguish an analyzer that *ran without error* from one that *found meaningful evidence*: for the `provenance` and `vision` analyzer roles, a `status == "completed"` result with no manifest/anomaly signal to report MUST NOT count as full (`1.0`) completeness toward `evidence_coverage`. Only the OCR analyzer's own core-field completeness drives whether zero-evidence OCR can be offset by genuinely informative provenance/vision findings.

The system MUST apply a hard floor forcing `Classification.INCONCLUSIVE` whenever OCR's core-field completeness is `0` (no core financial fields extracted at all) and no other analyzer reports a strong signal, regardless of what `evidence_coverage` sums to from provenance/vision.

The system MUST support a signal-**combination** floor on `ScoringRuleset`, generalizing the existing single-signal `critical_floor`: when a configured pair (or set) of `SignalCode`s co-occurs in one analysis, the ruleset MAY define a floor that raises `risk_score` into a higher band than either signal alone would produce for the ruleset version that defines it.

Ruleset `v2026_09_06` MUST define `AI_GENERATED_CLAIM_UNTRUSTED_SIGNER` with weight 50 and `critical_floor` 85, so that this signal alone forces `classification == HIGH_RISK`, identically to `VALID_AI_GENERATED_CLAIM`. Ruleset `v2026_09_05` and all earlier versions MUST remain byte-for-byte frozen and MUST NOT define this code. When ruleset `v2026_09_06` is active, `GET /version` MUST report `engine_version: "0.3.0"` and `ruleset_version: "2026-09-06"`.
(Previously: no ruleset defined `AI_GENERATED_CLAIM_UNTRUSTED_SIGNER`; `ENGINE_VERSION` was `0.2.0`; the active ruleset was `v2026_09_05`.)

#### Scenario: Deterministic score for identical input
- GIVEN identical normalized evidence and ruleset version
- WHEN the risk engine scores twice
- THEN both runs produce the same `risk_score`, `confidence_score`, and `classification`

#### Scenario: No absolute verdict
- GIVEN any analysis outcome
- WHEN the response is generated
- THEN the response MUST NOT contain `is_real`, `is_fake`, `authentic`, `verified transfer`, or equivalent labels

#### Scenario: Untrusted-signer AI claim forces HIGH_RISK like a fully-trusted claim
- GIVEN an analysis under ruleset `v2026_09_06` reporting only `AI_GENERATED_CLAIM_UNTRUSTED_SIGNER`, with no other signal present
- WHEN scoring runs
- THEN `critical_floor` 85 applies and `classification` is `HIGH_RISK`, the same verdict `VALID_AI_GENERATED_CLAIM` alone would produce

#### Scenario: Version endpoint reports the new engine and ruleset
- GIVEN the deployed service runs ruleset `v2026_09_06`
- WHEN a client calls `GET /version`
- THEN the response reports `engine_version: "0.3.0"` and `ruleset_version: "2026-09-06"`

### Requirement: Results UI
The web client MUST show score, confidence, a plain-language limitation statement, ordered evidence, masked sensitive fields by default, and a manual-reconciliation checklist (FR-008).

#### Scenario: Limitation statement always visible
- GIVEN any completed analysis
- WHEN results render
- THEN a statement clarifies that low risk does not confirm the transfer reached the account

### Requirement: Analysis latency budget
The system MUST complete the end-to-end upload → validate → preprocess → analyze → score → respond flow within the documented latency targets on the reference CPU and fixture set (NFR-001).

The system MUST warm the OCR and vision models during application startup, before the ASGI server accepts any inbound connection, so that the first real request after a process start is subject to the same per-analyzer time budgets as request N (`TimeBudget.ocr_s`, `TimeBudget.vision_s`, `TimeBudget.whole_request_s`, `TimeBudget.max_concurrent_analyzers` remain unchanged and are not part of this delta). Startup warmup MUST run the OCR and vision warmup steps concurrently, not sequentially, so the added startup delay is bounded by the slower of the two rather than their sum. Startup warmup MUST NOT raise or abort application startup when a required model directory is missing or misconfigured: the affected analyzer's warmup step MUST fail silently (logged, not raised), the application MUST still start and become reachable, and the existing per-request `ANALYZER_UNAVAILABLE` degradation contract for that analyzer MUST apply unchanged to the first and every subsequent real request. This requirement change does not alter `/health` behavior, `TimeBudget` values, or any per-request analyzer-availability contract.
(Previously: OCR and vision models loaded lazily on first use with no startup warmup step, so the first request after any process start paid full model-load latency inside its own per-analyzer time budget with no startup-time mitigation.)

#### Scenario: Typical request meets p50 target
- GIVEN a supported receipt image submitted on the documented reference CPU and fixture set
- WHEN the request follows the normal upload-to-response flow
- THEN the median (p50) end-to-end analysis time is under 4 seconds (NFR-001)

#### Scenario: Slow request still meets p95 target and shows processing state
- GIVEN a supported receipt image whose analysis exceeds the p50 target
- WHEN the request runs past 300 ms without a response
- THEN the client shows a processing state, and the response still completes within the p95 target of 10 seconds (NFR-001)

#### Scenario: First request after a fresh process start meets the same budgets as request N
- GIVEN a freshly started application process with both `RECEIPT_RISK_OCR_MODEL_DIR` and `RECEIPT_RISK_VISION_MODEL_DIR` correctly configured
- WHEN the very first inbound connection is accepted and a receipt is analyzed
- THEN OCR and vision analyzers meet their configured per-analyzer time budgets on this first request, identically to any later request

#### Scenario: Connection acceptance is gated on warmup completion
- GIVEN an application process starting up with both model directories configured
- WHEN the process is starting
- THEN the ASGI server does not accept any inbound connection until both the OCR and vision warmup steps have finished (successfully or by failing closed), so no request can observe a partially warmed process

#### Scenario: OCR and vision warmup run concurrently, not sequentially
- GIVEN an application process starting up with both model directories configured
- WHEN startup warmup executes
- THEN the total added startup latency is bounded by the slower of the OCR and vision warmup durations, not their sum

#### Scenario: Missing OCR model directory fails warmup closed without blocking startup
- GIVEN `RECEIPT_RISK_OCR_MODEL_DIR` is unset or points to a missing/misconfigured location
- WHEN the application starts
- THEN OCR warmup fails silently and is logged, the application still starts and becomes reachable, and the first real request needing OCR still receives the existing `ANALYZER_UNAVAILABLE` degradation, unchanged from pre-warmup behavior

#### Scenario: Missing vision model directory fails warmup closed without blocking startup
- GIVEN `RECEIPT_RISK_VISION_MODEL_DIR` is unset or points to a missing/misconfigured location
- WHEN the application starts
- THEN vision warmup fails silently and is logged, the application still starts and becomes reachable, and the first real request needing vision still receives the existing `ANALYZER_UNAVAILABLE` degradation, unchanged from pre-warmup behavior

#### Scenario: Non-regression of health, budgets, and the availability contract
- GIVEN this warmup change is deployed
- WHEN `/health` is polled, `TimeBudget` configuration is inspected, or an analyzer becomes unavailable at request time for any reason
- THEN `/health` behavior, `TimeBudget` values (`ocr_s`, `vision_s`, `whole_request_s`, `max_concurrent_analyzers`), and the per-request `ANALYZER_UNAVAILABLE` contract are all byte-for-byte identical to pre-change behavior

## Key Learnings

1. FR-007's classification bands and FR-008's UI wording both encode the "evidence over verdicts" product principle from PRD §3.
2. FR-002's cleanup requirement and FR-011's retention requirement overlap; retention rules live in the dedicated `data-retention` capability.
