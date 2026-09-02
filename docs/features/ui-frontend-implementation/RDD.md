# RDD: UI Frontend Implementation

> OpenSpec is the source of truth for requirements. This file is an `AGENTS.md`-required mirror for
> discoverability; it summarizes and links rather than duplicates. Do not edit requirement text here —
> edit `openspec/changes/ui-frontend-implementation/specs/receipt-analysis-web-client/spec.md` instead.

## Requirements covered by slice 1a

| Requirement | Spec scenario | Status |
| --- | --- | --- |
| Idle/upload state | "Idle state shows constraints and disclaimer" | Done — `DropZone` + `ReconciliationNotice` |
| File selection and validation | "Valid file moves to preview", "Client rejects an oversized or unsupported file before calling the API" | Done — `lib/api/client.ts::validateFileForUpload`, `FilePreview` |
| Uploading/processing state | "Processing state is announced" | Done — `ProcessingStages` (ARIA-live, no fabricated percentage) |
| Validation error states | "Server-side validation error is explained", "Analysis timeout is distinguished..." | Done — `ErrorPanel` code-derived copy |
| Service-unavailable / connectivity error | "Network failure shows a connectivity state, not a result" | Done — `ErrorPanel variant="network"`, never renders as a result |
| Rate-limit (429) handling | "Rate limit preserves the file and surfaces retry timing" | Done — file retained, `Retry-After` shown, retry action disabled until the wait elapses |
| No client-side persistence | "No storage after analysis" | Held — no `localStorage`/`sessionStorage`/IndexedDB/cookie write anywhere in slice 1a's code |

Deferred to slice 1b: "Successful result display" (full `AnalyzeResponse` rendering — evidence list,
extracted-data table, reconciliation checklist, analyzer/version detail). Slice 1a's result state
renders only classification and risk score as a minimal placeholder.

## Product invariant carried through this slice

The disclaimer (DESIGN.md §5's mandatory limitation sentence) MUST render in every reachable state
(AGENTS.md MVP1 invariant; DD7). Enforced structurally: `ReconciliationNotice` is mounted
unconditionally at the top of `+page.svelte`, outside every `{#if}` branch, and
`tests/unit/page.smoke.test.ts` asserts its presence across idle, selected, uploading, result,
network error, timeout, rate-limited, server-rejected-file, and client-validation states.

## Forbidden-language check

DESIGN.md §5's forbidden words ("real", "fake", "authentic", "verified transfer") never appear in
`ReconciliationNotice`'s copy (`tests/unit/ReconciliationNotice.test.ts`). Slice 1a's result state
does not yet render evidence/classification copy beyond `AnalyzeResponse.classification`, so the
full-result forbidden-word audit is the responsibility of slice 1b's `ResultView.svelte`.

## Success criteria status (proposal.md)

Slice 1a satisfies: real API integration with documented failure-taxonomy mapping, a working
state machine, and 5 presentational components covering every non-result state. Full result
presentation, theming, i18n, and accessibility polish remain in slices 1b–4 per the proposal's
slice boundaries.
