# Delta for Receipt Analysis

## MODIFIED Requirements

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
