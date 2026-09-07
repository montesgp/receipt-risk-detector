# Delta for Receipt Analysis

## MODIFIED Requirements

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
