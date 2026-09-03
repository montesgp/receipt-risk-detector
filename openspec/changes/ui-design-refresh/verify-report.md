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
