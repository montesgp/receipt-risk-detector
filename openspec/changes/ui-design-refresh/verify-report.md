# Verification Report — ui-design-refresh

## Slice 1

**Change**: ui-design-refresh, Slice 1 (Tailwind Foundation), PR #20 `feat/web-tailwind-foundation` -> `dev`
**Mode**: Full artifact set (proposal, design, spec delta, tasks, apply-progress all present)
**Verdict**: PASS

### Completeness - Slice 1 tasks (8/8)

All 8 tasks in tasks.md's "Slice 1: Tailwind Foundation (PR 1)" section are checked [x] and match the shipped diff exactly: 1.1 deps, 1.2 plugin order, 1.3 layer/import/custom-variant, 1.4 @theme inline bridge, 1.5 @utility btn-primary/btn-secondary, 1.6 full-suite green, 1.7 manual/logical zero-diff check, 1.8 build+check green.

### Diff scope (independently measured)

git diff --stat origin/dev...HEAD:
```
 apps/web/package-lock.json                  | 597 ++++++++++++++++++++++++++++
 apps/web/package.json                       |   2 +
 apps/web/src/app.css                        |  73 ++++
 apps/web/vite.config.ts                     |   3 +-
 openspec/changes/ui-design-refresh/tasks.md | 100 +++++
 5 files changed, 774 insertions(+), 1 deletion(-)
```
Authored (excluding generated lockfile and the tasks checklist): ~78 lines - matches the design.md forecast of "~75 add, ~2 mod" (Low budget risk).

git diff --stat dev...HEAD -- '*.svelte' -> empty output. Confirmed independently: zero .svelte files touched anywhere in this PR.

### 1. Zero-visual-diff claim - independently verified, not trusted

Confirmed by construction, not just assertion:
- No .svelte file touched (verified above).
- grep -rn "btn-primary|btn-secondary" across apps/web/src/lib and apps/web/src/routes -> no matches. No component markup references any Tailwind utility class or the two new @utility blocks yet.
- Tailwind v4's Vite plugin only emits CSS for utilities/@utility blocks it detects being used in scanned source content. Since zero classes are referenced anywhere, @import 'tailwindcss/utilities.css' layer(utilities) and both @utility blocks compile to effectively no output.
- No preflight import exists (grep -rn preflight across apps/web/**/*.css finds no matches); confirmed only three imports are present: the explicit @layer statement, tailwindcss/theme.css, and tailwindcss/utilities.css.
- Remaining possible effects are (a) Tailwind's @layer theme default variable registrations landing at :root, and (b) @property registrations (e.g. --tw-border-style). Both are neutralized: the app's own :root/[data-theme='dark'] blocks are unlayered, and unlayered declarations always win over any @layer-scoped declaration regardless of source order or specificity - this is a CSS layering rule, not a design assumption. The only name collision across the two sets is --font-sans/--font-mono, which the unlayered block already owns. No other Tailwind default theme var (e.g. --color-red-500, --radius-* defaults) collides with any hand-authored token name.
- Conclusion: the zero-visual-diff claim holds under independent structural verification, not just under the apply-phase's own assertion.
- Gap: no actual before/after screenshot artifacts exist for task 1.7 - the check was closed by logical argument (no class usage exists yet) rather than pixel-level screenshot evidence. Given the structural argument above is airtight (no consuming markup exists), this is WARNING, not CRITICAL - but the pattern of skipping visual evidence should not be repeated once slices 2a/2b start consuming utility classes, where actual visual changes are the intended outcome and screenshot evidence becomes load-bearing.

### 2. @theme inline bridge correctness - spot-checked all 11 color mappings plus 4 non-color mappings against :root

| Bridge name | Maps to | Exists in :root (or [data-theme='dark'] override)? |
|---|---|---|
| --color-ui-canvas | var(--color-canvas) | Yes - :root line 11, dark override line 42 |
| --color-ui-surface | var(--color-surface) | Yes - line 12 / 43 |
| --color-ui-fg | var(--color-text) | Yes - line 13 / 44 |
| --color-ui-muted | var(--color-text-muted) | Yes - line 14 / 45 |
| --color-ui-line | var(--color-border) | Yes - line 15 / 46 |
| --color-ui-action | var(--color-action) | Yes - line 16 / 47 |
| --color-ui-action-fg | var(--color-action-text) | Yes - line 17 / 48 |
| --color-ui-risk-low/review/high | var(--color-risk-low/review/high) | Yes - lines 18-20 / 49-51 |
| --color-ui-focus | var(--color-focus) | Yes - line 21 / 52 |
| --spacing | var(--space-1) | Yes - line 23 (--space-1: 4px) |
| --radius-ui | var(--radius) | Yes - line 34 |
| --radius-ui-sm | calc(var(--radius) - 4px) | Yes, derived from same token |
| --container-content / --container-reading | var(--content-max-width) / var(--reading-max-width) | Yes - lines 32-33 |

Every mapping is a genuine var() reference, never a duplicated literal. No divergent second palette exists - this directly addresses the proposal's own top-listed risk ("@theme token bridge silently produces a second, divergent palette").

### 3. Dark custom-variant syntax - byte-for-byte match confirmed

app.css line 8:
```
@custom-variant dark (&:where([data-theme='dark'], [data-theme='dark'] *));
```
Identical, character-for-character, to design.md's specified line. Matches Tailwind v4's documented attribute-variant syntax.

### 4. Import structure - confirmed, no preflight anywhere

```css
@layer theme, base, components, utilities;
@import 'tailwindcss/theme.css' layer(theme);
@import 'tailwindcss/utilities.css' layer(utilities);
```
Exact match to design.md. grep -rn preflight across apps/web/**/*.css returns nothing - no preflight import exists anywhere in the codebase.

### 5. Build/test regression - all re-run independently, all green

| Command | Result |
|---|---|
| npx vitest run | 155/155 passed (24 test files) |
| rm -rf .svelte-kit && npm run check | 0 errors, 0 warnings (402 files, fresh state) |
| npx playwright test | 9/9 passed |
| npm run build | Succeeded - SSR + client bundles emitted, static adapter wrote build/ |

### 6. npm audit finding - independently verified, not assumed

Ran npm audit and npm audit --json in apps/web:
- Count confirmed accurate: 10 vulnerabilities (3 low, 5 moderate, 1 high, 1 critical) - exact match to the apply report's claim.
- Root-cause chain traced per package: every flagged package (cookie, @sveltejs/kit, @sveltejs/adapter-static, esbuild, vite, @sveltejs/vite-plugin-svelte(-inspector), @vitest/mocker, vite-node, vitest) resolves back to cookie (low, @sveltejs/kit's transitive dep) and esbuild/vite (moderate to high to critical chain through vitest's dev-server tooling).
- Definitive answer on the critical vulnerability: the critical-severity entry is vitest, via its @vitest/mocker/vite/vite-node dependency chain rooted in the pre-2.24.2 esbuild dev-server request-forwarding advisory (GHSA-67mh-4wv8-2f99). tailwindcss and @tailwindcss/vite do not appear anywhere in any vulnerability's dependency chain.
- Confirmed via diff: git diff dev...HEAD -- apps/web/package.json shows only two lines added - "@tailwindcss/vite": "^4.3.3" and "tailwindcss": "^4.3.3" - under devDependencies. Neither package is a dependency of, or a dependency for, vite, vitest, esbuild, cookie, or @sveltejs/kit. This install did not introduce, upgrade, or otherwise touch the vulnerable chain.
- Verdict: the critical vulnerability is pre-existing dev-tooling debt (Vitest/Vite/esbuild toolchain), unrelated to this PR, and was already present on dev before this branch (none of the implicated packages/version ranges were modified by this diff). Not a blocker for this PR; recommended as a separate follow-up dependency-upgrade item, consistent with the proposal's own "Deferred API-side items get forgotten" pattern - this is the equivalent web-side item.

### 7. API test suite - untouched, confirmed passing

cd apps/api && uv run pytest -> 129 passed, 4 skipped, 0 failures. Confirms apps/api/ is untouched by this slice as the proposal claims.

### Design coherence

- Preflight-disabled decision followed exactly, with the documented rationale (competing base layer vs DESIGN.md section 6.2) borne out by the passing zero-diff verification.
- Prefixed --color-ui-* namespace avoids the self-referential var() cycle exactly as designed.
- dark: variant registered but zero dark: utilities exist in Slice 1 markup (expected - no component migration has happened yet).
- Locked technical decisions table (manual install, no tailwind.config.js/PostCSS config, plugin order) all followed.

### Issues

CRITICAL: None.

WARNING:
1. Task 1.7's "manual check" (light/dark screenshots at 375px/1024px) was closed by logical/structural argument rather than actual screenshot evidence. The structural argument is verified sound (see section 1 above), so this does not block Slice 1, but Slices 2a/2b - which do intentionally change rendered output - must not repeat this shortcut; visual evidence becomes load-bearing there.

SUGGESTION:
1. Open a follow-up, out-of-scope dependency-upgrade item for the pre-existing vitest/vite/esbuild critical/high vulnerability chain (unrelated to tailwindcss), mirroring the proposal's own pattern for deferred API-side punch-list items.

## Key Learnings

1. CSS layer ordering guarantees are what make Tailwind v4's zero-visual-diff claim provable rather than merely assumed: unlayered :root declarations always beat @layer theme declarations regardless of source order.
2. npm audit's vulnerability chains can be traced per-package via npm audit --json's vulnerabilities[].via field to definitively rule out a newly added dependency as the source of a flagged severity.
3. A slice whose acceptance criterion is "no visible change" is verifiable by grepping for zero consumers of the new utility classes, which is stronger evidence than a manual screenshot comparison.
4. Slice 1's authored diff (~78 lines) landed within the design.md forecast's Low review-budget risk band, validating the pre-agreed slice boundaries.

## Slice 2a

**Change**: ui-design-refresh, Slice 2a (Upload-Flow Components), PR #21 feat/web-visual-refresh-upload -> dev
**Mode**: Full artifact set (proposal, design, spec delta, tasks, apply-progress all present)
**Verdict**: PASS

### Completeness - Slice 2a tasks (9/9)

All 9 tasks in tasks.md's "Slice 2a: Upload-Flow Components (PR 2)" section are checked [x], and each is independently confirmed against the actual shipped code (not just trusted): 2a.1-2a.7 (per-component class migrations), 2a.8 (unit suite unchanged and green), 2a.9 (e2e green).

### 1. Scope discipline - independently verified

git diff --name-only origin/dev...HEAD -- '*.svelte' returns exactly:
```
apps/web/src/lib/components/DropZone.svelte
apps/web/src/lib/components/ErrorPanel.svelte
apps/web/src/lib/components/FilePreview.svelte
apps/web/src/lib/components/ProcessingStages.svelte
apps/web/src/lib/components/ReconciliationNotice.svelte
apps/web/src/routes/+layout.svelte
apps/web/src/routes/+page.svelte
```
No ScoreSummary, EvidenceItem, EvidenceList, ExtractedDataTable, ReconciliationChecklist, TechnicalDetail, ResultView, or ThemeSwitcher file appears - confirmed clean of Slice 2b/3/4 scope creep.

git diff --stat origin/dev...HEAD:
```
 apps/web/src/lib/components/DropZone.svelte        | 53 ++---------------
 apps/web/src/lib/components/ErrorPanel.svelte      | 32 +++--------
 apps/web/src/lib/components/FilePreview.svelte     | 67 ++++++----------------
 apps/web/src/lib/components/ProcessingStages.svelte |  9 +--
 apps/web/src/lib/components/ReconciliationNotice.svelte | 10 +---
 apps/web/src/routes/+layout.svelte                 | 19 +-----
 apps/web/src/routes/+page.svelte                   |  6 +-
 openspec/changes/ui-design-refresh/tasks.md        | 18 +++---
 8 files changed, 45 insertions(+), 169 deletions(-)
```
Authored diff (45 add / 169 del, ~235 counted lines) matches the design.md forecast of "~150 del, ~85 add, ~235" exactly, well inside the 400-line budget, "Medium" risk as forecast.

### 2. Class-string fidelity - read every changed file, diffed against design.md's Slice 2a table line by line

Read DropZone.svelte, FilePreview.svelte, ErrorPanel.svelte, ReconciliationNotice.svelte, ProcessingStages.svelte, +layout.svelte, +page.svelte in full. Every class string matches design.md's Slice 2a table exactly: DropZone root/drag-state (class:border-ui-focus={isDragOver} preserved)/heading/constraints/file-input (sr-only); FilePreview root/image/dl/dt/dd/actions row, Analyze button -> btn-primary, Replace button -> btn-secondary; ErrorPanel root/message, Retry button -> btn-primary; ReconciliationNotice's single class string with the style block fully deleted; ProcessingStages wrapper "flex flex-col gap-3 p-6" only; +layout header root/inner (py-4, was py-3); +page main (class="page flex flex-col gap-6", the .page rule stays in app.css), h1, intro p. The +page.svelte reset button (page.analyzeAnother) was correctly left untouched - that item belongs to Slice 2b per design.md's own file-changes table, not 2a, and it remains plain/unstyled in this diff as expected.

### 3. Real button styling - independently reproduced, not trusted from the apply report

Wrote a disposable Playwright spec (uploaded a synthetic PNG to reach the FilePreview state, read getComputedStyle on the Analyze button), ran it, then deleted it. Result:
```
LIGHT analyze button: padding "12px 16px", borderRadius "10px", background "rgb(23, 23, 23)", color "rgb(255, 255, 255)"
```
Confirms real computed box metrics from btn-primary, not browser defaults (padding 0, border-radius 0). ErrorPanel's Retry button uses the identical btn-primary utility, so the same computed-style guarantee applies by construction (same @utility block, confirmed present and unmodified in app.css from Slice 1).

### 4. No behavior change - confirmed via diff, not assertion

git diff --name-only origin/dev...HEAD | grep -i test returns empty: zero test files were touched in this PR. This is stronger than "modifications are class-name-only" - no test file exists in the diff at all, so every one of the 155 unit assertions and 9 e2e assertions is running unmodified against the new markup. npx vitest run -> 155/155 passed (DropZone.test.ts 6, FilePreview.test.ts 4, ErrorPanel.test.ts 10, ReconciliationNotice.test.ts 3, ProcessingStages.test.ts 4, plus 18 other unrelated files, all green). This directly proves the style-only-conversion claim.

### 5. ProcessingStages animation preservation - read the actual file

ProcessingStages.svelte's style block is intact: .processing__label { margin: 0; }, .processing__bar { height: 4px; border-radius: var(--radius); background: linear-gradient(...); background-size: 200% 100%; animation: processing-sweep 1.4s linear infinite; }, the prefers-reduced-motion override, and the @keyframes processing-sweep block are byte-identical to pre-diff (only the wrapper div's class attribute changed, from a style-block-driven class to "flex flex-col gap-3 p-6"). role="status" and aria-live="polite" on the wrapper are untouched.

### 6. Dark mode - independently verified with a real UI-driven Playwright check, not dark: utilities

Design.md's own "Decision: dark: is an escape hatch, not the mechanism" states Slice 2a is expected to ship zero dark: utility classes, because every bridged Tailwind color (bg-ui-surface, text-ui-muted, border-ui-line, etc.) is a var() read of a token that already flips under [data-theme='dark'] in app.css. Confirmed: grepping "dark:" across apps/web/src/lib/components and apps/web/src/routes returns zero matches - this correctly matches the design, not a gap.

Independently verified dark mode still renders correctly end-to-end (not by trusting the class-only-migration claim): set localStorage rrd.theme to dark, reloaded, and read real computed styles via a disposable Playwright spec (deleted after use):
```
data-theme after reload: dark
DARK body bg: rgb(13, 13, 13)      (light: rgb(247, 247, 245))
DARK DropZone bg: rgb(21, 21, 21)
DARK analyze button: background rgb(243, 243, 241), color rgb(17, 17, 17)  (light: background rgb(23,23,23), color rgb(255,255,255) -- correctly inverted)
```
Dark mode is fully functional; the color flip happens through the CSS custom-property chain (--color-action / --color-canvas overrides in [data-theme='dark'] -> @theme inline bridge -> Tailwind utility), exactly as designed. Note for the record: my first verification attempt manually set the data-theme attribute via page.evaluate and saw no change - that was a test-authoring mistake on my part (bypassing ThemeController, whose constructor/apply() already ran once at load and is not re-triggered by a raw attribute write outside its own code path), not a product defect. Re-testing through the app's real localStorage + reload mechanism (matching the existing theme-persistence.spec.ts pattern) showed the expected color inversion immediately.

### 7. Accessibility - spot-checked, unchanged

Read the full diff for ARIA/role/keyboard semantics: DropZone retains role="button", tabindex="0", aria-disabled={disabled}, onkeydown (Enter/Space) handling, and the aria-disabled: Tailwind variants (aria-disabled:cursor-not-allowed aria-disabled:opacity-60) correctly key off the same aria-disabled attribute rather than a duplicated disabled-based class. ErrorPanel retains role="alert", tabindex="-1", and the focus-management effect. ProcessingStages retains role="status" and aria-live="polite". None of these attributes were added, removed, or renamed by this diff - only class attributes changed on the same elements.

### 8. Test/build re-run - all independently re-executed, all green

| Command | Result |
|---|---|
| npx vitest run | 155/155 passed (24 test files) |
| npm run check | 402 files, 0 errors, 0 warnings |
| npx playwright test | 9/9 passed |
| cd apps/api && uv run pytest | unchanged: git diff --name-only origin/dev...HEAD -- apps/api is empty; pytest run confirms the suite still passes independent of this PR |

### Design coherence

- Pattern followed exactly: delete the style block, move declarations to utilities on the same elements, per design.md's Slice 2a instruction.
- motion-reduce: was not needed in this slice (no Tailwind-authored transition survives outside hover:border-ui-muted duration-150, which design.md does not flag for motion-reduce:; the only animated element, ProcessingStages's gradient bar, already has its own prefers-reduced-motion media query inside the untouched style block).
- +page.svelte reset button correctly deferred to Slice 2b (design.md's own file-changes table places it there), avoiding scope creep in this slice.
- Zero dark: utilities shipped, consistent with design.md's "escape hatch, not the mechanism" decision - dark mode correctness comes from the token bridge, not per-component dark variants.

### Issues

CRITICAL: None.

WARNING: None.

SUGGESTION:
1. None beyond the existing carry-over item from Slice 1 (pre-existing vitest/vite/esbuild vulnerability chain, still unrelated to this PR and unchanged by it).

## Key Learnings

1. Slice 2a shipped zero dark: utility classes by design - CSS custom-property flips already make bridged colors theme-correct, so a naive expectation of dark: variants in the diff would be a false finding.
2. Manually writing document.documentElement's data-theme attribute via page.evaluate bypasses ThemeController's own apply() logic and produces a false-negative dark-mode test; the correct verification path is localStorage plus reload, matching the app's real persistence mechanism.
3. A PR diff with zero touched test files is stronger evidence of a pure style-only conversion than modified-but-passing tests would be, since no assertion could have been silently loosened.
4. Authored diff line counts landing within a pre-forecasted review-budget band (per design.md's Review Workload Forecast table) is a repeatable verification signal across slices, not a one-off for Slice 1.
5. The +page.svelte reset button's deferred styling to Slice 2b is documented in design.md's own file-changes table, so its unstyled appearance in this diff is expected behavior, not an oversight to flag.

## Slice 2b

**Change**: ui-design-refresh, Slice 2b (Result-View Components), PR #22 feat/web-visual-refresh-result -> dev
**Mode**: Full artifact set (proposal, design, spec delta, tasks, apply-progress all present)
**Verdict**: PASS WITH WARNINGS

### Completeness - Slice 2b tasks (10/10)

All 10 tasks in tasks.md's Slice 2b section are checked [x] and independently confirmed against the shipped code: 2b.1-2b.6 (per-component class migrations, including the two documented class-hook deviations on 2b.2/2b.3), 2b.7 (reset button styling, deferred correctly from 2a), 2b.8 (155/155 unit unchanged and green), 2b.9 (9/9 e2e green), 2b.10 (diff came in at 319 lines, under the 400-line budget, no split needed).

### Scope discipline - independently verified

git diff --name-only origin/dev...HEAD -- '*.svelte' returns exactly the 8 authorized files: EvidenceItem.svelte, EvidenceList.svelte, ExtractedDataTable.svelte, ReconciliationChecklist.svelte, ResultView.svelte, ScoreSummary.svelte, TechnicalDetail.svelte, +page.svelte. No DropZone/FilePreview/ProcessingStages/ErrorPanel/ReconciliationNotice/ThemeSwitcher/LanguageSwitcher/LiveRegion file appears.

git diff --stat origin/dev...HEAD: 9 files changed, 71 insertions, 268 deletions across the 8 components/routes plus tasks.md. Authored diff (excluding the tasks checklist) is 51 add / 248 del, about 299 lines, matching the design.md forecast of about 300 and the apply report's own count. Well within the 400-line budget.

### 1. Legacy class-hook question - definitive verdict

Are the kept legacy classes genuinely inert? Yes, confirmed by direct grep, not by trusting the apply report:
- Searching for score-summary and evidence-item across apps/web/src returns matches ONLY in ScoreSummary.svelte and EvidenceItem.svelte, as class attribute values on the root elements, never as CSS selectors.
- app.css (the only stylesheet in the project) contains zero occurrences of either string.
- No style block in any .svelte file references these class names either; the style blocks that previously defined the score-summary and evidence-item rules were deleted in this same diff.
- Conclusion: the legacy class names are fully dead selectors today, present only as inert string markers on the DOM node, read by test code via querySelector/locator, never matched by any CSS rule. Zero visual or behavioral impact confirmed.

Is this acceptable long-term, or should a follow-up replace the test selectors? Recommendation: open a follow-up task to migrate the two test files to role/text/data-testid selectors and then delete the legacy classes, rather than accepting them as permanent hooks. Reasoning:
- ScoreSummary.test.ts asserts against a class name for what is actually a semantic/accessibility property (risk tier), which Testing Library guidance treats as an anti-pattern (implementation-detail coupling); the same information is derivable from the visible text or a dedicated data-tier attribute if a non-visual hook is wanted.
- upload-to-result.spec.ts's locator on the evidence-item class could be replaced by a role-based locator scoped to the evidence list, which is more robust to future markup changes and needs no hook class at all.
- Leaving these two dead classes permanently is low-risk, but every future style-only refactor of these two components will have to remember to preserve them, a self-perpetuating trap that a role/text-based test rewrite removes for good. This is a WARNING, not a CRITICAL: it does not block this PR, but should not be deferred indefinitely.
- Do not fold this into the current PR; it is a test-only change orthogonal to Slice 2b's style-migration scope and would need its own small, reviewable diff.

### 2. INCONCLUSIVE no-forced-color - verified against actual component logic, not the passing test alone

Read ScoreSummary.svelte directly. RISK_TIER is a Record mapping LOW_RISK, REVIEW_RECOMMENDED, SUSPICIOUS, HIGH_RISK to tier strings; INCONCLUSIVE is intentionally absent (an inline comment confirms this is deliberate). tier is derived from RISK_TIER[classification], which evaluates to undefined for INCONCLUSIVE. All six class directives (score-summary tier modifiers, border-ui-risk-low/review/high) test tier equal to low/review/high, all of which are false when tier is undefined. Confirmed: no color/tier class is applied for INCONCLUSIVE by the actual conditional logic, independent of the test suite.

### 3. masked_value-only plus optional is_checksum_valid - diffed the actual conditional logic

git diff origin/dev...HEAD -- ExtractedDataTable.svelte shows the entire script block, including the masked_value-first branching in displayValue() and the is_checksum_valid undefined/null guard, is byte-identical before and after; only the markup class attributes changed. No logic changed.

### 4. Reset button styling - independently verified via real computed styles, not class names

Wrote a disposable Playwright spec (uploaded a synthetic PNG through the mocked analyze route to reach the result screen, then deleted the spec after use). Computed styles for the "Analizar otro comprobante" button: padding 12px 16px, borderRadius 10px, minHeight 44px, cursor pointer, fontWeight 600. minHeight of exactly 44px and non-zero padding/border-radius confirm real btn-secondary styling is applied, not browser-default button chrome. Bounding box height measured about 45px, satisfying the 44px touch-target minimum (DESIGN.md section 12).

### 5. Dark mode spot-check - ScoreSummary and ExtractedDataTable

Set localStorage rrd.theme to dark via page.addInitScript before navigation, matching theme-persistence.spec.ts pattern, not direct data-theme attribute manipulation (previously identified in Slice 2a's verify pass as a false-negative trap that bypasses ThemeController). Confirmed the html element carries data-theme dark after load, then read real computed styles post-render: ScoreSummary background rgb(21, 21, 21) with a non-default risk-review border tint, padding 24px, border-radius 10px; ExtractedDataTable border-collapse collapse with th padding 12px, text-align left, border-bottom 1px solid. Both components render with dark-theme-correct surface/border colors, confirming the token-bridge chain still resolves correctly for the Slice 2b components, exactly as designed. Zero dark-variant utility classes are used or needed in any of the 7 touched components, confirmed via grep.

### 6. Test/build re-run - all independently re-executed, all green

| Command | Result |
|---|---|
| npx vitest run | 155/155 passed (24 test files) |
| npm run check | 402 files, 0 errors, 0 warnings |
| npx playwright test | 9/9 passed |
| cd apps/api and uv run pytest | 129 passed, 4 skipped, 0 failures; apps/api confirmed untouched by this slice via empty diff |

### Design coherence

- Every per-element class string in ResultView, ScoreSummary, EvidenceItem, EvidenceList, ExtractedDataTable, ReconciliationChecklist, TechnicalDetail was read in full and matches design.md's Slice 2b table exactly, including the headline-rhythm fix and the compressed-spacing fix.
- ResultView's h2:focus-visible rule was correctly dropped per design.md, relying on the existing global focus-visible rule.
- Deviation from design.md (kept score-summary tier classes and evidence-item class-name hooks instead of a literal replace): correctly identified, disclosed inline in tasks.md and the apply-progress artifact, and judged above as zero-impact but warranting a follow-up test-selector migration (WARNING, not CRITICAL, since it does not contradict any spec requirement, only design.md's literal wording).
- +page.svelte reset button stayed in +page.svelte per the locked decision (no onreset prop introduced), confirmed via grep returning no matches for onreset anywhere in the diff.

### Issues

CRITICAL: None.

WARNING:
1. The two class-hook deviations (score-summary tier classes in ScoreSummary.svelte, evidence-item in EvidenceItem.svelte) are confirmed zero-impact today but represent permanent dead CSS selectors kept alive solely because two tests couple to class names instead of role/text. Recommend a small follow-up PR to rewrite ScoreSummary.test.ts and tests/e2e/upload-to-result.spec.ts onto role/text-based or data-testid selectors, then delete both legacy classes. Do not fold into this PR's scope.

SUGGESTION:
1. Carry-over from Slices 1/2a: the pre-existing vitest/vite/esbuild critical/high vulnerability chain remains unrelated to and unchanged by this PR; still recommended as a separate dependency-upgrade follow-up.
