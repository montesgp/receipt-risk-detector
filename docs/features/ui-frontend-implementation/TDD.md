# TDD: UI Frontend Implementation

> OpenSpec is the source of truth for task tracking. This file is an `AGENTS.md`-required mirror for
> discoverability; it summarizes and links rather than duplicates. Do not edit task text here — edit
> `openspec/changes/ui-frontend-implementation/tasks.md` instead.

## Test strategy (see `design.md` "Testing Strategy" for the full table)

Strict TDD (RED → GREEN → REFACTOR) is enforced for every behavior. Test layout under
`apps/web/tests/`:

| Layer | Location | What it proves |
| --- | --- | --- |
| Unit — API client | `tests/unit/client.test.ts` | `analyzeReceipt` maps every documented status (200/400/413/415/422/429/504) to the right `AnalyzeResult`; `fetch` rejection → `network`; unparseable body → `malformed`; `Retry-After` parsing; client-side pre-validation short-circuits before any `fetch` call |
| Unit — state machine | `tests/unit/workspace.test.ts` | `idle→selected→uploading→(result\|error)` transitions; which failures retain the `File` vs. clear it back to `idle` |
| Component | `tests/unit/{DropZone,FilePreview,ProcessingStages,ErrorPanel,ReconciliationNotice}.test.ts` | Keyboard operability, ARIA-live processing state, no fabricated percentages, code-derived error copy (never raw `detail`/stack), the disclaimer's unconditional presence |
| Smoke | `tests/unit/page.smoke.test.ts` | Full `+page.svelte` wiring: idle→selected→uploading→result against a mocked `fetch`, every documented error variant, and that `ReconciliationNotice` renders in **every** one of those states |
| E2E | `tests/e2e/smoke.spec.ts` (Playwright) | **Deferred to slice 4** — see "Known deviations" below |

## Traceability (Phase → spec scenario)

| Task range | Spec scenario / locked decision |
| --- | --- |
| Phase 2 (2.1–2.8) | "Server-side validation error is explained", "Analysis timeout is distinguished...", "Rate limit preserves the file and surfaces retry timing", "Network failure shows a connectivity state, not a result" |
| Phase 3 (3.1–3.3) | design.md "Workspace state machine" table (DD1) |
| Phase 4 (4.1–4.10) | "Idle state shows constraints and disclaimer", "Valid file moves to preview", "Processing state is announced", "Server-side validation error is explained", DD7 |
| Phase 5.1 | Composition of all of the above into the single reachable route |

## Known deviations from the literal task list

- **5.2 (Playwright `smoke.spec.ts`) is deferred to slice 4.** Slice 4's task list (Phase 2) already
  owns standing up `playwright.config.ts` and the full e2e spec set
  (`upload-to-result`, `theme-persistence`, `locale-switch`). Rather than create the Playwright
  harness twice, slice 1a substitutes a Vitest component-level smoke test
  (`tests/unit/page.smoke.test.ts`) that exercises the identical idle→upload→result loop plus every
  error variant against a mocked `fetch`, and asserts the disclaimer's unconditional presence — the
  one invariant `design.md`'s "smoke e2e valuable in 1a" note called out as worth proving early.
  `@playwright/test` remains an installed devDependency from Phase 1.2 so slice 4 only needs to add
  configuration and specs, not the toolchain.
- The component test suite added `tests/unit/{DropZone,FilePreview,ProcessingStages,ErrorPanel,
  ReconciliationNotice}.test.ts`, one file beyond the literal per-component RED/GREEN pairs in
  `tasks.md`, because `@testing-library/svelte`'s `render()`/`cleanup()` needed an explicit
  `afterEach(cleanup)` (not automatic under this Vitest+Svelte 5 setup) and `vite.config.ts` needed a
  `resolve.conditions: ['browser']` fix under `mode === 'test'` so Svelte's client build (not the SSR
  build) is what Vitest mounts — both fixes are shared infrastructure the component tests depend on.
