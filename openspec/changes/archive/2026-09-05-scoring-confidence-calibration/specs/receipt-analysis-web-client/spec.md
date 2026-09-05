# Delta for Receipt Analysis Web Client

## MODIFIED Requirements

### Requirement: Successful result display
On a `200` response, the client MUST render the full `AnalyzeResponse` per DESIGN.md §4.4's visual priority.

When `classification` is `INCONCLUSIVE` and a reported signal carries `evidence.reason == "no_text_detected"` (`CORE_FIELD_EXTRACTION_FAILED`), the client MUST select a more specific hedged message instead of the generic INCONCLUSIVE copy, in both `en` and `es`, following the existing classification-conditional copy pattern in `ScoreSummary.svelte`. The message MUST hedge as an inability to identify transfer data ("no pudimos identificar los datos de una transferencia en este archivo" / "we could not identify transfer data in this file") and MUST NOT assert that the file is not a transfer or is fake/inauthentic.
(Previously: INCONCLUSIVE results always rendered the same generic message regardless of the specific reported signal/reason.)

#### Scenario: Full result renders from the live response
- GIVEN a `200` `AnalyzeResponse` with `classification`, `risk_score`, `confidence_score`, `signals`, and `extracted_data`
- WHEN the result state renders
- THEN classification and risk score, confidence, ordered evidence (`signals` by severity), the reconciliation checklist, extracted data (with CBU/CVU/CUIT masked via `masked_value`), and analyzer/version detail (`engine_version`, `ruleset_version`) are all shown
- AND the mandatory limitation disclaimer from the response's `limitations[]` (or the equivalent DESIGN.md §5 copy) is always present, never omitted

#### Scenario: No forbidden authenticity language appears
- GIVEN any rendered result, regardless of `classification`
- WHEN the UI is inspected
- THEN no copy contains "real", "fake", "authentic", or "verified transfer" (PRD FR-008, DESIGN.md §5)

#### Scenario: INCONCLUSIVE result does not force a risk color
- GIVEN `classification` is `INCONCLUSIVE`
- WHEN the result renders
- THEN confidence and missing-evidence context dominate the summary and no risk-tier color is forced (DESIGN.md §7 "Score summary")

#### Scenario: No-text-detected result shows the hedged specific message
- GIVEN a `200` `AnalyzeResponse` with `classification == "INCONCLUSIVE"` and a signal whose `evidence.reason == "no_text_detected"`, in either the `es` or `en` locale
- WHEN the result state renders
- THEN the summary shows the hedged message that the file does not appear to correspond to a transfer / that transfer data could not be identified in the file, instead of the generic INCONCLUSIVE copy
- AND the message contains no absolute claim (no "is not a transfer", "fake", "authentic", or equivalent certainty language)
