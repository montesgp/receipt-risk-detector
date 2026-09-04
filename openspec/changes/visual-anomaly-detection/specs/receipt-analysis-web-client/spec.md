# Delta for Receipt Analysis Web Client

## MODIFIED Requirements

### Requirement: Idle/upload state
The client MUST present an upload-focused idle state per DESIGN.md §4.1 before any file is selected. The idle state MUST also present a static, non-interactive, bilingual pipeline explainer summarizing the real analysis steps, so a first-time visitor understands what the tool does before uploading (PRD FR-013, new). The explainer's step list MUST include the PyTorch-based visual feature extraction step, worded as "PyTorch-based visual feature extraction integrated into the document inspection pipeline", and any engine label for it MUST read "Engine: PyTorch".
(Previously: the pipeline explainer listed six real pipeline steps without a visual-inspection step or a PyTorch engine label.)

#### Scenario: Idle state shows constraints and disclaimer
- GIVEN the client loads with no prior selection
- WHEN the workspace renders
- THEN the drop zone, supported formats, the 10 MB limit, and the reconciliation-limitation statement (DESIGN.md §5) are all visible without requiring a scroll on common viewports

#### Scenario: Idle state renders the pipeline explainer including vision
- GIVEN the client loads with no prior selection, in either the Spanish or English locale
- WHEN the workspace renders
- THEN a static, non-interactive component below the drop zone lists the real pipeline steps — including "PyTorch-based visual feature extraction integrated into the document inspection pipeline" — in the active locale, without displacing the reconciliation-limitation statement
- AND the component carries no `aria-live`/`role="status"` live-region semantics and is distinct from the uploading-state `ProcessingStages` widget

#### Scenario: Pipeline explainer never overstates system capability
- GIVEN the pipeline explainer is rendered, regardless of locale
- WHEN its copy is inspected
- THEN it contains none of "real", "fake", "authentic", or "verified transfer" (PRD FR-013, DESIGN.md §5), consistent with the existing forbidden-language rule for result copy

### Requirement: Successful result display
On a `200` response, the client MUST render the full `AnalyzeResponse` per DESIGN.md §4.4's visual priority. Any visual-anomaly finding (`VISUAL_ANOMALY_DETECTED`) MUST be worded as an outlier or unusual-pattern finding, and MUST NOT use "AI-generated" or equivalent phrasing, which stays exclusive to the existing C2PA `VALID_AI_GENERATED_CLAIM` signal.
(Previously: result rendering had no wording constraint distinguishing a visual-outlier finding from an AI-generated provenance claim.)

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

#### Scenario: Visual anomaly finding is worded as an outlier, never an AI claim
- GIVEN a rendered `signals` list containing a `VISUAL_ANOMALY_DETECTED` entry
- WHEN its evidence text is inspected
- THEN it reads as an outlier or unusual-pattern finding and does not use "AI-generated" phrasing, keeping it distinguishable from a `VALID_AI_GENERATED_CLAIM` C2PA finding

## Key Learnings

1. "Engine: PyTorch" and the AI-generated C2PA claim must stay visibly distinct in copy, since both concern image authenticity signals but carry very different evidentiary weight.
2. The pipeline explainer's step-list wording is treated as normative copy, not decoration, because PRD FR-013 requires it to accurately describe real analysis steps.
