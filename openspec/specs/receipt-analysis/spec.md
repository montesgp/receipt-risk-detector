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

The system MUST support a signal-**combination** floor on `ScoringRuleset`, generalizing the existing single-signal `critical_floor`: when a configured pair (or set) of `SignalCode`s co-occurs in one analysis, the ruleset MAY define a floor that raises `risk_score` into a higher band than either signal alone would produce for the ruleset version that defines it. `ruleset_version`s `v2026_09_01` and `v2026_09_04` MUST keep this combination-floor mapping empty and MUST reproduce their pre-existing scores exactly; only `v2026_09_05` (or later) MAY populate it.
(Previously: only completeness/coverage thresholds and the single-code `critical_floor` existed; provenance/vision "completed" always counted as full completeness; no OCR-zero hard floor and no signal-combination floor existed.)

#### Scenario: Deterministic score for identical input
- GIVEN identical normalized evidence and ruleset version
- WHEN the risk engine scores twice
- THEN both runs produce the same `risk_score`, `confidence_score`, and `classification`

#### Scenario: No absolute verdict
- GIVEN any analysis outcome
- WHEN the response is generated
- THEN the response MUST NOT contain `is_real`, `is_fake`, `authentic`, `verified transfer`, or equivalent labels

#### Scenario: Zero-OCR non-receipt image forces INCONCLUSIVE
- GIVEN an uploaded image with zero core financial fields extracted by OCR (`core_field_completeness == 0`), and no manifest/anomaly signal from provenance or vision beyond a clean "completed, nothing found" status
- WHEN scoring runs under the active ruleset
- THEN `classification` is `INCONCLUSIVE` regardless of the raw `evidence_coverage` sum contributed by provenance/vision completion

#### Scenario: Legitimate low-quality receipt is not forced INCONCLUSIVE
- GIVEN a real transfer receipt with partial OCR success (at least one core financial field extracted) and no C2PA manifest present
- WHEN scoring runs under the active ruleset
- THEN the hard OCR-zero floor does not apply, and the result reaches its ordinary risk-band classification based on the extracted evidence, not `INCONCLUSIVE`

#### Scenario: Signal combination floors the risk score into a higher band
- GIVEN an analysis under ruleset `v2026_09_05` reporting both `CORE_FIELD_EXTRACTION_FAILED` and `DATE_OUT_OF_BOUNDS`
- WHEN scoring runs
- THEN `risk_score` is floored into a classification band clearly more alarming than either signal would produce alone

#### Scenario: Neither signal alone triggers the combination floor
- GIVEN an analysis under ruleset `v2026_09_05` reporting only `CORE_FIELD_EXTRACTION_FAILED` (no `DATE_OUT_OF_BOUNDS`), or only `DATE_OUT_OF_BOUNDS` (no `CORE_FIELD_EXTRACTION_FAILED`)
- WHEN scoring runs
- THEN the combination floor is not applied and the score reflects only the single reported signal's ordinary contribution

#### Scenario: Prior ruleset versions remain unaffected
- GIVEN identical evidence scored under `ruleset_version` `v2026_09_01` or `v2026_09_04`
- WHEN scoring runs before and after this change ships
- THEN the produced `risk_score`, `confidence_score`, and `classification` are byte-for-byte identical to the pre-change output, because both versions' combination-floor mapping is empty

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
