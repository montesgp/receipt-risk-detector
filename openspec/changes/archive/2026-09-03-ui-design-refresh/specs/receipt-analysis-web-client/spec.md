# Delta for Receipt Analysis Web Client

## MODIFIED Requirements

### Requirement: Idle/upload state

The client MUST present an upload-focused idle state per DESIGN.md §4.1 before any file is selected. The idle state MUST also present a static, non-interactive, bilingual pipeline explainer summarizing the real analysis steps, so a first-time visitor understands what the tool does before uploading (PRD FR-013, new).
(Previously: the idle state only surfaced upload constraints and the reconciliation-limitation disclaimer, with no explanation of the pipeline itself.)

#### Scenario: Idle state shows constraints and disclaimer

- GIVEN the client loads with no prior selection
- WHEN the workspace renders
- THEN the drop zone, supported formats, the 10 MB limit, and the reconciliation-limitation statement (DESIGN.md §5) are all visible without requiring a scroll on common viewports

#### Scenario: Idle state renders the pipeline explainer

- GIVEN the client loads with no prior selection, in either the Spanish or English locale
- WHEN the workspace renders
- THEN a static, non-interactive component below the drop zone lists the six real pipeline steps — upload, file validation, metadata/C2PA provenance inspection, local OCR extraction, CBU/CVU and CUIT/CUIL validation, and risk/confidence scoring (PRD FR-001 through FR-007) — in the active locale, without displacing the reconciliation-limitation statement
- AND the component carries no `aria-live`/`role="status"` live-region semantics and is distinct from the uploading-state `ProcessingStages` widget

#### Scenario: Pipeline explainer never overstates system capability

- GIVEN the pipeline explainer is rendered, regardless of locale
- WHEN its copy is inspected
- THEN it contains none of "real", "fake", "authentic", or "verified transfer" (PRD FR-013, DESIGN.md §5), consistent with the existing forbidden-language rule for result copy

## Key Learnings

1. PRD FR-013 (new) is scoped narrowly to the static idle-state pipeline explainer, distinct from FR-008's live result/processing UI.
2. The `ui-localization-and-theming` spec needs no delta: its binary-switcher-compatible scenarios (manual toggle, system-preference default) already match this change's locked binary-switcher decision.
3. The new explainer scenario reuses the existing forbidden-authenticity-language rule rather than inventing a parallel constraint, keeping the spec's vocabulary consistent.
