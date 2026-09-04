# SDD: UI Frontend Implementation

> OpenSpec is the source of truth for this change. This file is an `AGENTS.md`-required mirror for
> discoverability; it summarizes and links rather than duplicates. Do not edit requirement text here —
> edit `openspec/changes/ui-frontend-implementation/` instead. See
> `openspec/changes/ui-frontend-implementation/{proposal.md,design.md}` for full content.

## Summary

Implements PRD FR-008 (Results UI): a SvelteKit 5 + TypeScript web client under `apps/web/` for the
browser-side upload → analyze → result journey (PRD §7), delivered as six chained PRs into `dev`
(slices 1a, 1b, 2, 3a, 3b, 4). This mirror covers **slice 1a**: scaffold, real API client, workspace
state machine, idle/upload/processing/error components, and CORS/env docs.

## Capability specs (source of truth)

| Capability | Spec | Covers |
| --- | --- | --- |
| `receipt-analysis-web-client` | `openspec/changes/ui-frontend-implementation/specs/receipt-analysis-web-client/spec.md` | PRD FR-008, the 15 GWT scenarios (idle, upload, processing, result, error/connectivity/rate-limit states, no client persistence) |
| `ui-localization-and-theming` | `openspec/changes/mvp-init-foundation/specs/ui-localization-and-theming/spec.md` | FR-012 — implemented as-is in slices 2–4, not slice 1a |

## Design decisions relevant to slice 1a (see `design.md` for full rationale and alternatives)

| Decision | Where documented |
| --- | --- |
| DD1 — One `AnalysisWorkspace` rune class (`$state`/`$derived`), per-page-instance | `design.md` "Architecture Decisions" |
| DD2 — Discriminated `AnalyzeFailure` union (`problem` / `network` / `malformed` / `client-validation`) | `design.md` "Architecture Decisions"; `lib/api/errors.ts` |
| DD6 — `PUBLIC_API_BASE_URL` via `$env/static/public` with a committed `.env` | `design.md` "Architecture Decisions" |
| DD7 — `ReconciliationNotice` mounted unconditionally, never behind a state branch | `design.md` "Architecture Decisions"; `+page.svelte` |

## Architecture constraints respected

Per `design.md` "Technical Approach": three layers — `lib/api` (the only module that knows HTTP),
`lib/features/receipt-analysis` (the runes state machine), `lib/components` (dumb presentational
components with no `fetch` calls). `+page.svelte` is the sole composition point that owns the
`AnalysisWorkspace` instance and reads its state to choose which component renders.

## Slice 1a file map

| File | Role |
| --- | --- |
| `lib/api/{types,errors,client}.ts` | Wire contract, failure taxonomy, `analyzeReceipt()` |
| `lib/features/receipt-analysis/workspace.svelte.ts` | `AnalysisWorkspace` state machine |
| `lib/components/{DropZone,FilePreview,ProcessingStages,ErrorPanel,ReconciliationNotice}.svelte` | Idle/upload/processing/error presentational components |
| `routes/+page.svelte` | Wires the workspace to the components above |

## Deviation note

`5.1` wires components directly through `+page.svelte`'s local `workspace` binding rather than
`setContext(workspace)`, because slice 1a has exactly one consumer of the workspace. `setContext` is
introduced when a second consumer (layout-level `ThemeSwitcher`/`LanguageSwitcher` in slices 2/3a)
needs the same instance. See `tasks.md` Phase 5.1 for the full note.
