# Architecture Documentation Specification

## Purpose

Documentation completeness and traceability for MVP1 architecture: existing Mermaid diagrams retained, new source-editable draw.io files added, and UML use-case + activity diagrams for the core upload → risk-assessment flow (proposal decision D3).

## Requirements

### Requirement: Draw.io source-editable diagrams
The repository MUST contain raw `.drawio` source files under `docs/diagrams/` for the four existing architecture views, each with an exported `.svg` embedded in `docs/ARCHITECTURE.md` (D3).

#### Scenario: Draw.io source present and diffable
- GIVEN the four existing Mermaid architecture views
- WHEN a contributor opens `docs/diagrams/`
- THEN a corresponding `.drawio` file exists for each view and is reviewable as a text diff

#### Scenario: SVG embedded in ARCHITECTURE.md
- GIVEN a `.drawio` source file is exported to SVG
- WHEN `docs/ARCHITECTURE.md` is rendered
- THEN the corresponding SVG is embedded and visible without opening the `.drawio` file

#### Scenario: Mermaid retained alongside draw.io
- GIVEN the existing Mermaid diagrams in the repository
- WHEN this change is applied
- THEN the Mermaid diagrams remain present and unremoved (D3)

### Requirement: UML use-case and activity diagrams for core flow
The repository MUST contain a UML use-case diagram and a UML activity/swimlane diagram covering the "upload receipt → risk assessment" flow, superseding the non-UML PRD §7 flowchart for this purpose (D3, proposal Approach step 3).

#### Scenario: Use-case diagram covers actors
- GIVEN the three PRD actors (beneficiary operator, external automation, contributor/integrator)
- WHEN the UML use-case diagram is reviewed
- THEN each actor's interaction with the analyze flow is represented as a use case

#### Scenario: Activity diagram covers the full flow
- GIVEN the upload → preprocess → analyze → score → respond sequence
- WHEN the UML activity/swimlane diagram is reviewed
- THEN each stage and its responsible swimlane (client, API, analyzers, risk engine) is represented in order

### Requirement: DESIGN.md as canonical visual reference
`docs/DESIGN.md` MUST document the theme-switcher and language-switcher UX (placement, persistence, system-preference default) so it functions as the canonical visual reference (proposal Approach step 4; ui-localization-and-theming spec).

#### Scenario: Switcher placement documented
- GIVEN a contributor reads `docs/DESIGN.md`
- WHEN they look for switcher UX guidance
- THEN placement, persistence behavior, and default-detection rules for both switchers are documented

## Key Learnings

1. This capability's scenarios validate documentation artifacts and traceability, not runtime behavior — verification means checking file existence and content, not executing code.
2. The PRD §7 Mermaid flowchart is explicitly superseded by the new UML diagrams for the upload→risk-assessment flow per D3, while other Mermaid architecture views are retained.
