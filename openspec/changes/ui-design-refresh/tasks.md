# Tasks: UI Design Refresh

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | Slice1 ~77 / Slice2a ~235 / Slice2b ~300 / Slice3 ~110 / Slice4 ~130 / Slice5 ~40 |
| 400-line budget risk | Low(1,5) / Medium(2a) / Medium-High(2b) / Low-Medium(3) / Medium(4) |
| Chained PRs recommended | Yes |
| Suggested split | PR1(slice1) → PR2(slice2a) → PR3(slice2b, pre-split point ready) → PR4(slice3) → PR5(slice4) → PR6(slice5) |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Medium-High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Tailwind foundation, zero visual diff | PR 1 | `npm run check && npm run test` (apps/web) | `npm run build && npm run test:e2e` | Revert `package.json`, `vite.config.ts`, `app.css` additions |
| 2a | Upload-flow component class migration | PR 2 | `npm run test -- DropZone FilePreview ErrorPanel ReconciliationNotice ProcessingStages` | `npm run test:e2e -- upload` | Revert touched `<style>`→utility diffs per component |
| 2b | Result-view component class migration | PR 3 | `npm run test -- ResultView ScoreSummary EvidenceItem EvidenceList ExtractedDataTable ReconciliationChecklist TechnicalDetail` | `npm run test:e2e -- result` | Revert touched component diffs; independent of 2a |
| 3 | Binary theme switcher + controller.resolved fix | PR 4 | `npm run test -- ThemeSwitcher` | `npm run test:e2e -- theme-persistence` | Revert `ThemeSwitcher.svelte` + its two test files |
| 4 | PipelineExplainer component + i18n + spec delta | PR 5 | `npm run test -- PipelineExplainer key-parity literal-audit` | `npm run test:e2e -- idle-state` | Remove new component, i18n keys, FR-013, spec delta |
| 5 | Docs cleanup | PR 6 | N/A (docs-only, no test target) | N/A — no runtime behavior changed | Revert doc sections only |

## Slice 1: Tailwind Foundation (PR 1)

- [x] 1.1 `npm install -D tailwindcss @tailwindcss/vite` in `apps/web/`
- [x] 1.2 `apps/web/vite.config.ts`: add `tailwindcss()` before `sveltekit()` in `plugins`
- [x] 1.3 `apps/web/src/app.css`: prepend `@layer theme, base, components, utilities;` + `@import 'tailwindcss/theme.css' layer(theme);` + `@import 'tailwindcss/utilities.css' layer(utilities);` + `@custom-variant dark (&:where([data-theme='dark'], [data-theme='dark'] *));` (no preflight import)
- [x] 1.4 `apps/web/src/app.css`: append `@theme inline { ... }` token bridge exactly per design.md (prefixed `--color-ui-*`, `--spacing: var(--space-1)`, `--radius-ui*`, `--container-*`)
- [x] 1.5 `apps/web/src/app.css`: append `@utility btn-primary` and `@utility btn-secondary` per design.md (unused until slice 2a/2b consume them)
- [x] 1.6 RED/GREEN-equivalent verification: run existing full unit + e2e suite unchanged; confirm zero failures (zero visual diff contract — not new tests) — 155/155 unit tests pass, 9/9 e2e pass
- [x] 1.7 Manual check: light/dark screenshots at 375px/1024px before vs after; confirm `border`/`divide` utilities still render without preflight — no `.svelte` component touched, no `@utility`/utility class consumed anywhere in markup yet, so zero visual diff is guaranteed by construction; `border`/`divide` utilities confirmed available via Tailwind v4's `@property --tw-border-style` (independent of preflight)
- [x] 1.8 `npm run build && npm run check` green

## Slice 2a: Upload-Flow Components (PR 2, requires Slice 1 merged)

- [x] 2a.1 `DropZone.svelte`: delete `<style>`, apply root/drag-state/heading/constraints/file-input classes per design.md table; keep `class:border-ui-focus={isDragOver}`
- [x] 2a.2 `FilePreview.svelte`: delete `<style>`, apply root/image/dl/dt/dd/actions classes; Analyze → `btn-primary`, Replace → `btn-secondary`
- [x] 2a.3 `ErrorPanel.svelte`: delete `<style>`, apply root/message classes; Retry → `btn-primary`
- [x] 2a.4 `ReconciliationNotice.svelte`: delete `<style>`, apply `m-0 max-w-reading text-sm text-ui-muted`
- [x] 2a.5 `ProcessingStages.svelte`: apply wrapper-only class `flex flex-col gap-3 p-6`; keep `@keyframes processing-sweep` and rest of `<style>` untouched (proposal scope: redesign out of scope)
- [x] 2a.6 `+layout.svelte` header: apply root/inner classes, `py-4` (was `py-3`)
- [x] 2a.7 `+page.svelte`: apply `<main>`/`<h1>`/intro `<p>` classes (keep `class="page"`)
- [x] 2a.8 Verification (visual/markup-only, no behavior change): run `DropZone.test.ts`, `FilePreview.test.ts`, `ErrorPanel.test.ts`, `ReconciliationNotice.test.ts`, `ProcessingStages.test.ts` unchanged — confirm all still pass (proves role/text assertions untouched by class-only diff)
- [x] 2a.9 `npm run test:e2e -- upload` unchanged, confirm green

## Slice 2b: Result-View Components (PR 3, requires Slice 1 merged; independent of 2a)

- [ ] 2b.1 `ResultView.svelte`: delete `<style>` incl. dropped `h2:focus-visible` rule (global rule covers it); apply root/h2/h3/limitations classes
- [ ] 2b.2 `ScoreSummary.svelte`: delete `<style>`; apply root + `class:border-ui-risk-low/review/high`; classification/risk-figure/confidence classes (fixes headline-rhythm defect)
- [ ] 2b.3 `EvidenceItem.svelte` + `EvidenceList.svelte`: delete `<style>`; apply li/severity/description/meta classes (fixes compressed-spacing defect)
- [ ] 2b.4 `ExtractedDataTable.svelte`: delete `<style>`; apply table/th/td classes
- [ ] 2b.5 `ReconciliationChecklist.svelte`: delete `<style>`; apply ul/li/label/status classes
- [ ] 2b.6 `TechnicalDetail.svelte`: delete `<style>`; apply details/summary/dl/table classes
- [ ] 2b.7 `+page.svelte` reset button: apply `class="btn-secondary self-start"`, keep in `+page.svelte` (no `onreset` prop added)
- [ ] 2b.8 Verification (markup-only): run existing tests for all 7 touched components unchanged — confirm all still pass
- [ ] 2b.9 `npm run test:e2e -- result` unchanged, confirm green
- [ ] 2b.10 If diff exceeds 400 lines at apply time: split into 2b-i (`ResultView`+`ScoreSummary`+`EvidenceItem`/`EvidenceList`) and 2b-ii (`ExtractedDataTable`+`ReconciliationChecklist`+`TechnicalDetail`) per design.md's pre-agreed split point

## Slice 3: Binary Theme Switcher (PR 4, requires Slice 1 merged; sequenced after Slice 2)

- [ ] 3.1 RED: add test "a dark system preference shows Dark checked before any explicit choice" to `ThemeSwitcher.test.ts` (`stubMatchMedia matches:true`, assert checked label is `theme.dark` while `controller.mode === 'system'`) — confirm it fails against current `?? OPTIONS[0]` logic
- [ ] 3.2 GREEN: `ThemeSwitcher.svelte` — reduce `OPTIONS` to light/dark; derive `active = $derived(controller.resolved)`; `currentOption` and `cycle()` per design.md; `aria-checked`/`tabindex` key off `active`
- [ ] 3.3 Update `ThemeSwitcher.test.ts`: rename tri-state test to binary (`toHaveLength(3)`→`2`, checked label `theme.system`→`theme.light`), same for English variant, retarget ArrowRight test to light radio (`'light'`→`'dark'`), 44px-target length `3`→`2`, rewrite cycling test to 2-state (`dark`→`light`)
- [ ] 3.4 Update `theme-persistence.spec.ts`: segmented control count `3`→`2`, cycling-button regex `/Sistema|Claro|Oscuro/i`→`/Claro|Oscuro/i`
- [ ] 3.5 Confirm `select()`, `LiveRegion`, dual-variant `<style>` block, and `theme.system` i18n key remain unchanged
- [ ] 3.6 `npm run test -- ThemeSwitcher && npm run test:e2e -- theme-persistence` green

## Slice 4: Pipeline Explainer (PR 5, requires Slice 1+2 merged; requires spec delta authored)

- [ ] 4.1 RED: write `apps/web/tests/unit/PipelineExplainer.test.ts` asserting 6 `<li>` items, ES and EN render, no `role="status"`/`aria-live` attribute, forbidden-word scan (`real`/`fake`/`authentic`/`auténtico`/`verificado`/"verified transfer") over `upload.pipeline.*` — confirm it fails (component does not exist yet)
- [ ] 4.2 Add 13 keys under `upload.pipeline.*` to `apps/web/src/lib/i18n/messages/es.json` and `en.json` in the same commit (identical key set, exact copy from design.md table)
- [ ] 4.3 GREEN: create `apps/web/src/lib/components/PipelineExplainer.svelte` per design.md's exact markup (static `<section>`/`<ol>`, no live-region role)
- [ ] 4.4 Wire into `+page.svelte`: mount `<PipelineExplainer />` directly after `<DropZone />` inside the `idle` branch; confirm `ReconciliationNotice` stays mounted and undisplaced
- [ ] 4.5 Confirm `npm run test -- PipelineExplainer` passes (GREEN) and `key-parity.test.ts` still passes with 13 new keys
- [ ] 4.6 Confirm `literal-audit.test.ts` still passes (no hardcoded Spanish/English literals outside i18n files)
- [ ] 4.7 New e2e assertion: explainer visible below drop zone, disclaimer still present, idle state
- [ ] 4.8 `docs/PRD.md`: add FR-013 (static idle-state pipeline explainer, bilingual, non-live, six steps derived from FR-001–FR-007)
- [ ] 4.9 Confirm `openspec/changes/ui-design-refresh/specs/receipt-analysis-web-client/spec.md` delta (already authored by sdd-spec) matches shipped scenarios; no further edit needed here

## Slice 5: Docs Cleanup (PR 6, requires Slice 1–4 merged)

- [ ] 5.1 `docs/DESIGN.md` §4.1: replace bullet list with the exact replacement text from design.md (adds pipeline-explainer bullet, PRD FR-013 reference)
- [ ] 5.2 `docs/DESIGN.md` §12: replace Control/Default table rows and closing paragraph with the exact replacement text from design.md (binary switcher, `resolved`-based default, removed "System" option)
- [ ] 5.3 `README.md` stack table: `custom CSS` → `Tailwind CSS v4 (@tailwindcss/vite) over DESIGN.md tokens`
- [ ] 5.4 Confirm no other doc references the tri-state switcher or the pre-explainer §4.1 ordering

## Key Learnings

1. Slices 2a/2b/3 (except the ThemeSwitcher fix) are markup/class-only conversions, so their verification is "existing tests still pass unchanged," not new RED/GREEN cycles.
2. The ThemeSwitcher fix is genuine new behavior (checked-state now derives from `controller.resolved` instead of `mode`), so it needs a real RED test proving the dark-first-paint bug before the GREEN fix.
3. Slice 4's PipelineExplainer is new functionality and follows full RED (failing test + missing i18n keys) → GREEN (component + keys) TDD.
4. Slice 2b is closest to the 400-line review budget; design.md's pre-agreed split point (ResultView+ScoreSummary+EvidenceItem/List vs ExtractedDataTable+ReconciliationChecklist+TechnicalDetail) is carried into task 2b.10 as a conditional fallback.
5. Slice ordering is strictly dependency-locked: slices 2/3/4 each require slice 1 merged, and slice 4 additionally requires the frozen spec delta to exist before apply.
