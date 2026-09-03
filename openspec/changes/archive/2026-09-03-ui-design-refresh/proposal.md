# Proposal: UI Design Refresh

Implements GitHub issue [#19](https://github.com/montesgp/receipt-risk-detector/issues/19), already labelled `status:approved`.

## Intent

`apps/web/` is functionally complete but visually unfinished. Three primary-action buttons render as bare browser defaults, several content blocks are spaced at the smallest tokens of the DESIGN.md grid, and there is no shared styling primitive anywhere — every `<button>` is styled ad hoc or not at all. A first-time visitor evaluating a suspicious transfer receipt is being asked to trust a fraud-risk verdict from an interface that looks unmaintained. Perceived credibility is part of this product's value, not decoration.

Why now: the API contract and the `receipt-analysis-web-client` spec are frozen, the token system in `docs/DESIGN.md` is stable and correctly used (no magic-number padding exists anywhere), and no feature work is in flight touching `apps/web/src/lib/components/`. The styling layer can be rebuilt without contending with behavioral change. Two further gaps are cheap to close in the same pass: the theme switcher exposes a three-option control where users only ever want two, and the idle state explains constraints but never explains what the tool actually does before asking for an upload.

## Visual defect audit (source of record for this change)

| Component | Defect | Evidence |
|---|---|---|
| `FilePreview.svelte` | "Analyze" and "Replace" `<button>` elements have **zero** button CSS — no class, padding, border, radius, background, or hover/active state. Renders at the UA default (~`padding: 1px 6px`). | Root cause of the "hyper-old buttons" report |
| `+page.svelte` | Reset button ("Analizar otro comprobante") — same bare `<button>`, no styling | Same pattern |
| `ErrorPanel.svelte` | Retry button — same bare `<button>`, no styling | Same pattern |
| Codebase-wide | **No shared button component or utility class exists.** Only `LanguageSwitcher`/`ThemeSwitcher` have any button styling, because they are segmented controls, not primary actions | Structural gap, not a per-file oversight |
| `EvidenceItem.svelte` | `gap: var(--space-1)` (4px) between severity, description and meta; `padding: var(--space-3) 0` (12px vertical, 0 horizontal) for a row with three stacked text blocks plus a definition list — tightest spacing in the component set | Concrete cause of the "compressed" report |
| `ScoreSummary.svelte` | 2rem risk number and 1.25rem classification separated only by `gap: var(--space-2)` (8px) — no vertical rhythm for a headline figure | |
| `+layout.svelte` header | `padding: var(--space-3) var(--space-4)` (12px/16px) for a bar holding brand plus two switchers | |
| Codebase-wide | No hover/active affordance anywhere except color changes; interaction feedback is limited to the global `:focus-visible` outline | |
| `docs/DESIGN.md` §12 | Documents a tri-state switcher ("System · Light · Dark", default `system`) that this change makes binary | Stale after slice 3 |
| `docs/DESIGN.md` §4.1 | Idle-state ordering (headline → drop zone → privacy line) has no slot for the pipeline explainer | Stale after slice 4 |

Explicitly **not** defects: absent shadows/elevation (DESIGN.md §6.5 rejects heavy shadows by design), and token usage itself — every component already consumes `--space-*`/`--color-*` correctly.

## Scope

### In Scope
- Tailwind CSS v4 adoption for `apps/web/` via `@tailwindcss/vite`, bridged to the existing DESIGN.md tokens.
- A shared primary/secondary button style, applied to the three unstyled buttons.
- Spacing and rhythm corrections for `EvidenceItem`, `ScoreSummary`, the header, and peer components; hover/active/focus-visible states.
- Binary Light/Dark theme switcher UI, plus its unit and e2e test updates and the DESIGN.md §12 rewrite.
- A new idle-state pipeline explainer component (bilingual ES/EN), a new PRD **FR-013**, a delta scenario on the frozen `receipt-analysis-web-client` spec, and a DESIGN.md §4.1 amendment.
- UI-side docs cleanup: DESIGN.md §12 and §4.1, README stack table (add Tailwind).

### Out of Scope
- **All API-side punch-list items — deferred to a separate, smaller change**: `request_id` hardcoding in `errors.py`/`middleware/rate_limit.py`, and the `extracted_data`/`analyzer_statuses` shape drift in `docs/API.md`. Bundling backend correctness fixes into a UI-named change breaks single-responsibility slicing.
- NFR-002/NFR-005 spec-coverage gaps and PRD NFR cross-link annotations (API-side, same deferral).
- Any change to `apps/api/` behavior, to `ThemeController`'s resolution logic, or to the API client and workspace state machine.
- Replacing the DESIGN.md token system with Tailwind's default palette or spacing scale. Tokens stay authoritative; Tailwind is an adapter.
- New product behavior beyond the explainer: no accounts, history, batch upload, or absolute authenticity verdicts.
- `ProcessingStages.svelte` redesign — it is a live uploading-state widget, out of this change's idle-state work.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `receipt-analysis-web-client`: the **Idle/upload state** requirement gains one scenario — a static, non-interactive pipeline summary rendered below the drop zone in the idle state, describing the real analysis steps in the active locale. Delta type: `MODIFIED` (the full requirement block, preserving the existing "Idle state shows constraints and disclaimer" scenario).
- `ui-localization-and-theming` is **consumed, not changed**: `sdd-spec` must confirm whether the binary switcher contradicts any frozen scenario there before authoring a delta. If a frozen scenario asserts three options, a `MODIFIED` delta is required; otherwise none.

## Approach

Tailwind-first, five sequential slices, each one PR merged to `dev` before the next starts. Tailwind leads because every later slice consumes it: shipping the visual refresh in hand-written CSS and then migrating would mean styling the same components twice.

1. **Tailwind foundation, zero visual diff.** Install `tailwindcss` + `@tailwindcss/vite`, add the plugin to `vite.config.ts`, `@import "tailwindcss"` in `app.css`, register the token bridge and the dark variant. No component `<style>` block is touched. Acceptance is that build, dev, `check`, unit and e2e all stay green and rendered output is unchanged.
2. **Component visual refresh.** Shared button style, spacing corrections, interaction states. Expected to sub-split across ~15 components — **2a: upload-flow components** (`DropZone`, `FilePreview`, `ErrorPanel`, `+page` reset, header); **2b: result-view components** (`ScoreSummary`, `EvidenceItem`, extracted-data, checklist, technical detail).
3. **Theme switcher binary simplification.** Confined to `ThemeSwitcher.svelte` markup plus test and doc updates. Sequenced after slice 2 so the switcher is not restyled twice.
4. **Pipeline explainer.** New component + i18n keys + PRD FR-013 + spec delta + DESIGN.md §4.1. Placed after slices 1–2 so it is authored in the refreshed visual language rather than retrofitted.
5. **UI docs cleanup.** Remaining stale UI-side passages.

### Locked technical decisions (not open questions)

| Decision | Choice | Rationale |
|---|---|---|
| CSS framework | **Tailwind CSS v4 via `@tailwindcss/vite`.** No `tailwind.config.js`, no PostCSS config, no `npx tailwindcss init`. | v4's Vite-native plugin replaces all of that. Compatible with the repo's Vite 5.4.11 / SvelteKit 5. |
| Token ownership | `app.css`'s `:root` / `[data-theme='dark']` custom properties stay the **single source of truth**; Tailwind's `@theme` block references them so utilities compile to `var()` reads. | Prevents two parallel token systems drifting. DESIGN.md remains authoritative; Tailwind is a thin adapter, not a replacement palette. |
| Dark mode strategy | `@custom-variant dark (&:where([data-theme='dark'], [data-theme='dark'] *));` — **not** Tailwind's default `.dark` class or `prefers-color-scheme` media strategy. | Exactly matches the attribute strategy already set by `theme.svelte.ts` and the `app.html` blocking script. **Zero changes to the anti-flash script.** |
| Theme switcher | Rendered UI becomes strictly binary (Light/Dark). `ThemeMode`'s internal `'system'` concept and `ThemeController`'s `matchMedia` resolution are **kept untouched** — `'system'` stays the silent first-load default and is already never persisted. | The controller already only restores `'light'`/`'dark'` from storage, so the change is confined to `ThemeSwitcher.svelte`'s options array and its 2-state cycle. |
| Pipeline explainer scope | New **PRD FR-013**, not a reuse of FR-008. | FR-008 governs the *result* UI and the *live* processing state; this is a static idle-state pre-upload explainer. A distinct requirement keeps both traceable. |
| Explainer placement | Directly below the drop zone in the idle state, above/alongside the privacy-disclaimer line. | Per DESIGN.md §4.1 ordering, and it must not displace the reconciliation-limitation statement. |
| Explainer content | Six steps mirroring the real pipeline (PRD FR-001…FR-007): upload → file validation → metadata/C2PA provenance → local OCR extraction → CBU/CVU + CUIT/CUIL validation → risk and confidence scoring. Bilingual ES/EN. | It must describe what the system actually does; overstating capability would itself be a credibility defect. |
| Explainer semantics | Static, non-interactive, not a live status region. Distinct from `ProcessingStages.svelte`. | `ProcessingStages` is `role="status" aria-live="polite"` and only mounts during `uploading`. Duplicating live semantics in the idle state would create a false progress signal. |

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `apps/web/package.json`, `vite.config.ts` | Modified | Tailwind v4 dependency + Vite plugin (slice 1) |
| `apps/web/src/app.css` | Modified | `@import "tailwindcss"`, `@theme` token bridge, `@custom-variant dark` (slice 1) |
| `apps/web/src/lib/components/*.svelte` | Modified | Button style, spacing, interaction states (slice 2a/2b) |
| `apps/web/src/routes/+page.svelte`, `+layout.svelte` | Modified | Reset button, header padding (slice 2a) |
| `apps/web/src/lib/components/ThemeSwitcher.svelte` | Modified | Binary options array and 2-state cycle (slice 3) |
| `apps/web/tests/unit/ThemeSwitcher.test.ts` | Modified | 3 tests assert a tri-state radiogroup (slice 3) |
| `apps/web/tests/e2e/theme-persistence.spec.ts` | Modified | Drops "Sistema" from the cycle assertion; radio count 3 → 2 (slice 3) |
| `apps/web/src/lib/components/` (new explainer) | New | Idle-state pipeline explainer (slice 4) |
| `apps/web/src/lib/i18n/messages/{es,en}.json` | Modified | New explainer keys, identical in both files (slice 4) |
| `openspec/specs/receipt-analysis-web-client/spec.md` | Modified (delta) | New idle-state scenario (slice 4) |
| `docs/PRD.md` | Modified | New FR-013 (slice 4) |
| `docs/DESIGN.md` §4.1, §12 | Modified | Explainer placement; binary switcher table (slices 4–5) |
| `README.md` stack table | Modified | "custom CSS" → Tailwind v4 + DESIGN.md tokens (slice 5) |

Not touched: `theme.svelte.ts`, `app.html`, the API client, `apps/api/`, `docs/API.md`.

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| `@theme` token bridge silently produces a second, divergent palette instead of reading the live custom properties | Med | Slice 1's acceptance is an explicit zero-visual-diff check in both themes; the bridge maps names only, never literal color values. |
| Slice 2 exceeds the 400-line review budget across ~15 components | High | Pre-agreed sub-split into 2a (upload flow) and 2b (result view). `sdd-tasks` must forecast this explicitly. |
| Tailwind's preflight reset alters existing component appearance in slice 1, breaking the "no visual diff" contract | Med | Verify preflight impact during slice 1; if it perturbs rendering, absorb the reset diff in slice 1 with an explicit before/after review rather than letting it leak into slice 2. |
| Theme flash regression from the dark-variant change | Low | The `@custom-variant` targets the same `[data-theme='dark']` attribute; the blocking script is not modified. Existing Playwright first-paint check covers it. |
| Pipeline explainer overstates what the system does, conflicting with the reconciliation-limitation statement | Med | Steps are derived from FR-001…FR-007 wording; the explainer must not use `real`, `fake`, `authentic`, or "verified transfer", and must not displace the DESIGN.md §5 limitation statement. |
| `key-parity.test.ts` fails on partially added explainer keys | Low | ES and EN keys are added in the same commit; parity is CI-enforced. |
| Deferred API-side items get forgotten | Med | Recorded here as an explicit out-of-scope list; a follow-up change must be opened when this one archives. |

## Rollback Plan

Each slice is one PR into `dev` and reverts independently. Slice 1 is pure plumbing: reverting it removes the Tailwind dependency, the plugin line, and three `app.css` directives, restoring the hand-written CSS untouched. Slices 2a/2b are style-only and revert to the current appearance with no behavioral impact. Slice 3 reverts to the tri-state switcher along with its tests, since `ThemeController` was never modified. Slice 4 reverts by removing the new component, its i18n keys, the FR-013 block, and the spec delta — nothing depends on it. Slice 5 is docs-only. No API code, deploy config, persisted data, or client-side storage behavior is touched by any slice.

## Dependencies

- Node toolchain and the existing `apps/web` Vitest/Playwright suites (already in CI).
- `@tailwindcss/vite` compatible with Vite 5.4.11 (confirmed: v4 supports Vite 5+).
- Slices are strictly ordered; slices 2, 3, and 4 each require slice 1 merged to `dev`.
- Slice 4 requires the `receipt-analysis-web-client` delta to be authored by `sdd-spec` before apply.

## Success Criteria

- [ ] Every primary-action button (`FilePreview` analyze/replace, `+page` reset, `ErrorPanel` retry) renders a shared, token-driven style with hover, active, and visible focus states — no bare browser-default button remains.
- [ ] `EvidenceItem`, `ScoreSummary`, and the header use spacing appropriate to their content hierarchy rather than defaulting to `--space-1`/`--space-2`.
- [ ] Tailwind utilities resolve to the existing DESIGN.md tokens; no second color or spacing scale exists in `app.css`.
- [ ] Dark mode works through `[data-theme='dark']` with no change to `app.html`'s blocking script and no first-paint flash.
- [ ] The theme switcher exposes exactly two options; `ThemeController` still resolves `prefers-color-scheme` on first load and still never persists `'system'`.
- [ ] The idle state renders a six-step pipeline explainer below the drop zone in both ES and EN, without displacing the reconciliation-limitation statement.
- [ ] `es.json` and `en.json` remain key-identical (CI-enforced).
- [ ] PRD FR-013 exists and the `receipt-analysis-web-client` delta scenario has a passing automated test.
- [ ] DESIGN.md §12 and §4.1 and the README stack table describe the shipped behavior.
- [ ] No rendered copy contains `is_real`, `is_fake`, `authentic`, or "verified transfer"; no client-side persistence of images or results is introduced.
