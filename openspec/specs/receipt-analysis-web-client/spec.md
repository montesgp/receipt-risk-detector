# Receipt Analysis Web Client Specification

## Purpose

Implements PRD FR-008 (Results UI) and the primary journey in PRD §7: the browser-side upload →
analyze → result workflow for `apps/web/`, binding to the real `AnalyzeResponse`/`ExtractedFieldModel`/
`ProblemDetails` schemas (`apps/api/src/receipt_risk/adapters/api/schemas.py`). This is slice 1 of the
`ui-frontend-implementation` proposal. Locale and theme are governed separately by the frozen
`ui-localization-and-theming` spec, implemented as-is (no delta) in slices 2-4.

## Requirements

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

### Requirement: File selection and validation
The client MUST validate the selected file client-side before submission and reject unsupported input without an API call (PRD FR-001).

#### Scenario: Valid file moves to preview
- GIVEN the user selects a JPEG, PNG, or WebP file under 10 MB
- WHEN the file is accepted
- THEN a constrained preview, filename, type, and human-readable size are shown, and the user MAY replace or analyze it (DESIGN.md §4.2)

#### Scenario: Client rejects an oversized or unsupported file before calling the API
- GIVEN the user selects a file over 10 MB or of an unsupported type
- WHEN validation runs
- THEN the client MUST NOT call `POST /v1/receipts/analyze`, and MUST show a message consistent with the server's `FILE_TOO_LARGE`/`UNSUPPORTED_IMAGE` codes (docs/API.md §5)

### Requirement: Uploading/processing state
The client MUST show an ARIA-live processing state while the request is in flight (DESIGN.md §4.3, NFR-004).

#### Scenario: Processing state is announced
- GIVEN the user starts analysis on a valid file
- WHEN the request is sent
- THEN honest coarse stages (not fabricated percentages) are shown, and the state is exposed through the ARIA live region

### Requirement: Successful result display
On a `200` response, the client MUST render the full `AnalyzeResponse` per DESIGN.md §4.4's visual priority.

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

### Requirement: Validation error states
The client MUST map documented `ProblemDetails` error codes to actionable, non-technical messages (docs/API.md §5).

#### Scenario: Server-side validation error is explained
- GIVEN the API returns `400 MISSING_FILE`, `413 FILE_TOO_LARGE`, `415 UNSUPPORTED_IMAGE`, or `422 IMAGE_DIMENSIONS_EXCEEDED`
- WHEN the client receives the `ProblemDetails` body
- THEN it shows an error message derived from `code`/`detail` without a raw stack trace or tool error (DESIGN.md §4.5), and the selected file is preserved in memory for retry

#### Scenario: Analysis timeout is distinguished from a validation error
- GIVEN the API returns `504 ANALYSIS_TIMEOUT`
- WHEN the client receives the response
- THEN it shows a distinct timeout message (not a generic validation error) and offers retry

### Requirement: Service-unavailable / connectivity error state
The client MUST render connectivity failures as a distinct state, never as an analysis result, because the API never judged the receipt when it never ran.

#### Scenario: Network failure shows a connectivity state, not a result
- GIVEN the request fails before any HTTP response is received (network error, DNS failure, CORS rejection, or the API process being unreachable)
- WHEN the client handles the failure
- THEN it renders a distinct "service unavailable" state — never the result state, never implying any classification, risk score, or evidence exists — and offers retry with the file preserved

### Requirement: Rate-limit (429) handling
The client MUST handle `429 RATE_LIMITED` responses per the documented `Retry-After` contract (docs/API.md §5b) without discarding the user's work.

#### Scenario: Rate limit preserves the file and surfaces retry timing
- GIVEN the API returns `429` with a `Retry-After` header and `RATE_LIMITED` `ProblemDetails`
- WHEN the client receives the response
- THEN the selected file remains available for retry, the UI communicates the wait derived from `Retry-After`, and the client MUST NOT auto-resubmit before that interval elapses

### Requirement: No client-side persistence
The client MUST NOT persist uploaded images or results beyond the page session (PRD FR-011, PRD non-goals: no history).

#### Scenario: No storage after analysis
- GIVEN an analysis completes (success or error)
- WHEN storage is inspected
- THEN no image bytes or `AnalyzeResponse` data exist in `localStorage`, `sessionStorage`, IndexedDB, or cookies

## Key Learnings

1. The connectivity/service-unavailable state is intentionally distinct from every documented `ProblemDetails` error, because a network failure means the API never ran and must never imply a judgment occurred.
2. `INCONCLUSIVE` classification suppresses forced risk-tier coloring per DESIGN.md §7, distinguishing it from the four scored classifications.
3. Client-side validation (file type/size) must short-circuit before any API call to avoid consuming rate-limit budget on requests the server would reject anyway.
