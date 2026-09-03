# Design: UI Design Refresh

## Technical Approach

Tailwind v4 is adopted as a **utility adapter over the existing DESIGN.md token system**, not as a replacement design system. `app.css`'s unlayered `:root` / `[data-theme='dark']` blocks stay the single source of truth; a `@theme inline` bridge registers Tailwind-facing names whose values are `var()` reads of those tokens, so every generated utility resolves through the live custom property and therefore theme-flips for free.

Slices 2a/2b **replace** each touched component's Svelte `<style>` block with utility classes rather than mixing both. Half-migrated components are the worst end state, and full conversion is net line-negative (style blocks are larger than the class strings that replace them), which keeps both slices inside the 400-line budget.

Svelte 5 runes conventions (`$props`, `$derived`, `$state`, `$effect`, context-provided i18n/theme) are preserved everywhere. No component gains or loses a prop, and no state machine changes.

## Architecture Decisions

### Decision: Tailwind v4 installation shape

**Choice**: Manual `npm install -D tailwindcss @tailwindcss/vite`, then register the plugin in `apps/web/vite.config.ts`:

```ts
import tailwindcss from '@tailwindcss/vite';
plugins: [tailwindcss(), sveltekit()]
```

and `@import "tailwindcss";` at the top of `app.css`. **No `tailwind.config.js`, no PostCSS config, no `npx tailwindcss init`.**

**Alternatives considered**: `npx sv add tailwindcss` (the SvelteKit CLI add-on).
**Rationale**: `sv add` also rewrites `svelte.config.js`, may install `prettier-plugin-tailwindcss`, and can scaffold a `src/app.css` it assumes it owns — this repo's `app.css` is hand-authored and load-bearing. The manual path is three reviewable lines. **Uncertainty flag for apply**: `sv add tailwindcss` does exist and is the officially documented route; the plugin-order detail (`tailwindcss()` before `sveltekit()`) and the exact `@tailwindcss/vite` version resolving against Vite 5.4.11 must be confirmed against current docs at apply time.

### Decision: Prefixed Tailwind color namespace (`--color-ui-*`)

**Choice**: The bridge uses `--color-ui-canvas: var(--color-canvas)` etc., **not** `--color-canvas: var(--color-canvas)`.
**Alternatives considered**: same-name bridging; moving token definitions into `@theme`.
**Rationale**: Tailwind's color namespace is literally `--color-*`, so a same-name bridge is a self-referential cycle (`--color-canvas: var(--color-canvas)`), and moving definitions into `@theme` loses the `[data-theme='dark']` override. The `ui-` prefix is collision-proof and greppable. `@theme` cannot express a dark override, so the token blocks must stay in `:root`.

### Decision: Preflight is NOT imported

**Choice**: Import Tailwind without preflight:

```css
@layer theme, base, components, utilities;
@import 'tailwindcss/theme.css' layer(theme);
@import 'tailwindcss/utilities.css' layer(utilities);
```

**Alternatives considered**: full `@import "tailwindcss"` and absorbing the reset diff in slice 1.
**Rationale**: Preflight is a **competing base layer** to DESIGN.md §6.2 — it resets `h1`–`h3` to `font-size: inherit; font-weight: inherit`, strips `p`/`dl`/`dd` margins, unstyles lists and tables. Absorbing it would force slice 1 to re-author the entire typographic scale, converting a pure-plumbing slice into a visual one and breaking its zero-visual-diff acceptance. The repo already sets `* { box-sizing: border-box }` and `html, body { margin: 0 }`, which is the part of preflight that Tailwind actually needs. **Slice 1 verification item**: confirm `border`/`divide` utilities still render (v4 supplies `--tw-border-style: solid` via `@property`, independent of preflight).

### Decision: `dark:` is an escape hatch, not the mechanism

**Choice**: Register `@custom-variant dark (&:where([data-theme='dark'], [data-theme='dark'] *));` but expect **zero `dark:` utilities** in slices 2a–4.
**Rationale**: Because every bridged color is a `var()` read of a token that already flips under `[data-theme='dark']`, `bg-ui-surface` is already theme-correct. The variant exists only for a future one-off. `app.html`'s blocking script is untouched.

### Decision: Shared button style as `@utility`, not a `Button.svelte`

**Choice**: Two self-contained custom utilities in `app.css` — `btn-primary` and `btn-secondary`. Usage is `class="btn-primary"` (single class, no composition).
**Alternatives considered**: a `Button.svelte` component; composed `btn btn-primary`.
**Rationale**: A component adds a props surface and test churn for a purely presentational concern. Composed classes would depend on Tailwind's intra-layer utility sort order, which is not a contract; self-contained utilities are order-independent.

### Decision: the reset button stays in `+page.svelte`

**Choice**: `page.analyzeAnother` stays where it is; it only gains `btn-secondary` and a wrapper.
**Rationale**: Moving it into `ResultView` requires a new `onreset` prop, i.e. a behavioral/API change inside a style-only slice.

### Decision: binary switcher keys off `controller.resolved`

**Choice**: `aria-checked` / `tabindex` / cycle index derive from `controller.resolved`, not `controller.mode`.
**Rationale**: `mode` is still `'system'` on first load (locked decision: `ThemeController` untouched). The current `?? OPTIONS[0]` fallback would then show **Light** checked while the page renders **dark** — a real bug the tri-state UI hid. `resolved` is always `'light' | 'dark'`, so it maps exactly onto a binary control. Clicking still calls `setTheme('light'|'dark')`, which persists, so `mode` and `resolved` converge after the first interaction.

## Data Flow

    app.css :root / [data-theme='dark']   ← single source of truth (unlayered)
            │  var()
            ▼
    @theme inline  --color-ui-*, --spacing, --radius-ui, --container-*
            │  compiles to
            ▼
    Tailwind utilities  bg-ui-surface, p-4, rounded-ui  ──→ components
            ▲
    ThemeController.apply() → <html data-theme> ────────────┘ (flips the var, no re-render)

## Slice 1 — Tailwind foundation

### `apps/web/src/app.css` (prepend, above the existing `:root` block)

```css
@layer theme, base, components, utilities;
@import 'tailwindcss/theme.css' layer(theme);
@import 'tailwindcss/utilities.css' layer(utilities);

@custom-variant dark (&:where([data-theme='dark'], [data-theme='dark'] *));
```

### Token bridge (append, below the existing `[data-theme='dark']` block)

```css
/* Adapter only. Values are var() reads — never literals. app.css's :root and
   [data-theme='dark'] blocks above stay the single source of truth (DESIGN.md §6.3). */
@theme inline {
  --color-ui-canvas: var(--color-canvas);
  --color-ui-surface: var(--color-surface);
  --color-ui-fg: var(--color-text);
  --color-ui-muted: var(--color-text-muted);
  --color-ui-line: var(--color-border);
  --color-ui-action: var(--color-action);
  --color-ui-action-fg: var(--color-action-text);
  --color-ui-risk-low: var(--color-risk-low);
  --color-ui-risk-review: var(--color-risk-review);
  --color-ui-risk-high: var(--color-risk-high);
  --color-ui-focus: var(--color-focus);

  /* 4px grid (DESIGN.md §6.4): p-1=4px, p-2=8px, p-3=12px, p-4=16px,
     p-6=24px, p-8=32px, p-12=48px, p-16=64px — exactly the --space-* names. */
  --spacing: var(--space-1);

  --radius-ui: var(--radius);
  --radius-ui-sm: calc(var(--radius) - 4px);

  --container-content: var(--content-max-width);
  --container-reading: var(--reading-max-width);
}
```

`--font-sans` / `--font-mono` need **no** bridge: Tailwind's default theme already declares those exact names in `@layer theme`, and app.css's unlayered `:root` beats any layered declaration, so `font-sans` / `font-mono` utilities already resolve to the DESIGN.md stacks.

### Shared button utilities (append)

```css
@utility btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  min-height: 44px;
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-action);
  border-radius: var(--radius);
  background: var(--color-action);
  color: var(--color-action-text);
  font: inherit;
  font-weight: 600;
  line-height: 1.2;
  cursor: pointer;
  transition: background-color 140ms ease, border-color 140ms ease;
  &:hover:not(:disabled) {
    background: color-mix(in srgb, var(--color-action) 86%, var(--color-canvas));
  }
  &:active:not(:disabled) {
    background: color-mix(in srgb, var(--color-action) 74%, var(--color-canvas));
  }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
}

@utility btn-secondary {
  /* identical box metrics */
  display: inline-flex; align-items: center; justify-content: center;
  gap: var(--space-2); min-height: 44px;
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  background: var(--color-surface);
  color: var(--color-text);
  font: inherit; font-weight: 600; line-height: 1.2; cursor: pointer;
  transition: background-color 140ms ease, border-color 140ms ease;
  &:hover:not(:disabled) { background: var(--color-canvas); border-color: var(--color-text-muted); }
  &:active:not(:disabled) { background: color-mix(in srgb, var(--color-canvas) 88%, var(--color-text)); }
  &:disabled { opacity: 0.5; cursor: not-allowed; }
}
```

No focus rule is needed — the existing global `:focus-visible { outline: 2px solid var(--color-focus) }` already covers both. Transitions stay inside DESIGN.md §9's 120–220 ms band and touch only color properties.

**Slice 1 acceptance (zero visual diff)**: `@utility` blocks are unused (Tailwind only emits utilities it sees in markup), no component `<style>` is touched, and no preflight is imported. Only two rendered-CSS effects are possible: Tailwind's `@layer theme` default variables landing at `:root` (overridden by the app's unlayered block wherever names collide) and the `@property` registrations. Verify with `npm run build`, `check`, `test`, `test:e2e` plus a manual light/dark before/after in the browser.

## Slice 2a — Upload-flow components

Pattern for every component below: delete the `<style>` block, move the declarations to utilities on the same elements. `motion-reduce:` is used where a transition survives.

| Element | Class string |
|---|---|
| `DropZone` root | `flex flex-col items-center gap-2 rounded-ui border-2 border-dashed border-ui-line bg-ui-surface px-4 py-8 text-center cursor-pointer transition-colors duration-150 hover:border-ui-muted aria-disabled:cursor-not-allowed aria-disabled:opacity-60` |
| `DropZone` drag state | keep `class:` directive → `class:border-ui-focus={isDragOver}` (replaces `.drop-zone--drag`) |
| `DropZone` heading | `m-0 text-lg font-semibold` (§6.2 card title, was inheriting body size) |
| `DropZone` constraints | `m-0 text-ui-muted` |
| `DropZone` file input | `sr-only` (Tailwind's own visually-hidden utility; replaces the hand-written clip rule) |
| `FilePreview` root | `flex flex-col gap-4 rounded-ui border border-ui-line bg-ui-surface p-6` (was `gap-3 p-4`) |
| `FilePreview` image | `max-h-80 max-w-full rounded-ui object-contain` |
| `FilePreview` `<dl>` | `m-0 grid grid-cols-[auto_1fr] gap-x-2 gap-y-1` |
| `FilePreview` `<dt>` | `text-ui-muted` · `<dd>` | `m-0` |
| `FilePreview` actions row | `flex flex-wrap gap-3 pt-1` |
| `FilePreview` **Analyze** | `btn-primary` |
| `FilePreview` **Replace** | `btn-secondary` |
| `ErrorPanel` root | `flex flex-col items-start gap-4 rounded-ui border border-ui-risk-high bg-ui-surface p-6` |
| `ErrorPanel` message | `m-0` |
| `ErrorPanel` **Retry** | `btn-primary` |
| `ReconciliationNotice` | `m-0 max-w-reading text-sm text-ui-muted` |
| `ProcessingStages` wrapper | `flex flex-col gap-3 p-6` — *style block is otherwise kept*: the `@keyframes processing-sweep` gradient bar is not expressible as a utility and the proposal puts a `ProcessingStages` redesign out of scope |
| `+layout` header inner | `mx-auto flex max-w-content items-center justify-between gap-4 px-4 py-4` (was `py-3`) |
| `+layout` header root | `border-b border-ui-line bg-ui-surface` |
| `+page` `<main>` | keeps `class="page"` (the `.page` rule stays in app.css) plus `flex flex-col gap-6` |
| `+page` `<h1>` | `m-0 text-3xl font-semibold tracking-tight` (§6.2 page title 32–40 px) |
| `+page` `<p>` intro | `m-0 max-w-reading text-ui-muted` |

## Slice 2b — Result-view components

| Element | Class string |
|---|---|
| `ResultView` root | `flex flex-col gap-8` (was `gap-6`) |
| `ResultView` `<h2>` | `m-0 text-2xl font-semibold` |
| `ResultView` `<h3>` (×3) | `m-0 mb-3 text-lg font-semibold` |
| `ResultView` limitations | `max-w-reading text-sm text-ui-muted` (inner `<p class="m-0">`) |
| `ScoreSummary` root | `flex flex-col gap-3 rounded-ui border border-ui-line bg-ui-surface p-6` + `class:border-ui-risk-low/review/high` directives replacing the three modifier classes |
| `ScoreSummary` classification | `m-0 text-xl font-semibold` |
| `ScoreSummary` risk figure | `m-0 mt-1 text-[2.5rem] font-bold leading-none tabular-nums` (headline gets its own rhythm — the §-audit defect) |
| `ScoreSummary` confidence / action / note | `m-0 text-ui-muted` |
| `EvidenceItem` root `<li>` | `flex flex-col gap-2 border-b border-ui-line px-1 py-4 last:border-b-0` (was `gap-1`, `py-3 px-0`) |
| `EvidenceItem` severity | `m-0 text-[0.8125rem] font-semibold uppercase tracking-wide text-ui-muted` |
| `EvidenceItem` description | `m-0 max-w-reading` |
| `EvidenceItem` meta `<dl>` | `m-0 mt-1 flex flex-wrap gap-x-6 gap-y-1` · `<dt>` `text-ui-muted` |
| `EvidenceList` `<ul>` | `m-0 list-none p-0` · empty `<p>` | `m-0 text-ui-muted` |
| `ExtractedDataTable` `<table>` | `w-full border-collapse` |
| `ExtractedDataTable` `th`/`td` | `border-b border-ui-line px-3 py-3 text-left` (`py-2` → `py-3`) |
| `ExtractedDataTable` `th` | `+ font-medium text-ui-muted` |
| `ExtractedDataTable` confidence/checksum `td` | `+ font-mono text-sm text-ui-muted` |
| `ReconciliationChecklist` `<ul>` | `m-0 flex list-none flex-col gap-4 p-0` (was `gap-2`) |
| `ReconciliationChecklist` `<li>` | `flex flex-col gap-1` · label `font-semibold` · status `text-sm text-ui-muted` |
| `TechnicalDetail` `<details>` | `rounded-ui border border-ui-line px-4 py-3` |
| `TechnicalDetail` `<summary>` | `cursor-pointer font-medium select-none` |
| `TechnicalDetail` versions `<dl>` | `my-3 grid grid-cols-[auto_1fr] gap-x-2 gap-y-1` · `dt` `text-ui-muted` · `dd` `m-0 font-mono text-sm` |
| `TechnicalDetail` analyzer table | `w-full border-collapse text-sm`; `th`/`td` `border-b border-ui-line px-2 py-1 text-left` |
| `+page` reset button | `class="btn-secondary self-start"`, wrapped so it is the last child of the `result` branch (stays in `+page.svelte`) |

`ResultView`'s `h2:focus-visible` rule is dropped — the global `:focus-visible` rule already produces the identical ring.

## Slice 3 — Binary theme switcher

`ThemeSwitcher.svelte` script changes only:

```ts
const OPTIONS: { mode: 'light' | 'dark'; labelKey: string; icon: string }[] = [
  { mode: 'light', labelKey: 'theme.light', icon: '☀' },
  { mode: 'dark', labelKey: 'theme.dark', icon: '🌙' }
];

// `controller.mode` is still 'system' before the first explicit choice
// (ThemeController is untouched), so a binary control must key off the
// resolved theme or it would show "Light" checked on a dark first paint.
const active = $derived(controller.resolved);
const currentOption = $derived(OPTIONS.find((o) => o.mode === active) ?? OPTIONS[0]);
function cycle(): void {
  select(active === 'light' ? 'dark' : 'light');
}
```

Markup: `aria-checked={active === option.mode}` and `tabindex={active === option.mode ? 0 : -1}`. `handleKeydown` is unchanged (modulo 2 wraps correctly). `select()`, `LiveRegion`, and the segmented/cycle dual-variant CSS are unchanged; the `<style>` block is converted to utilities in the same pass only if slice 2 has not already done so (it has not — `ThemeSwitcher` is in neither 2a nor 2b, so **its `<style>` block stays as-is** and slice 3 is markup+logic only). `theme.system` stays in both message files — `ThemeMode` still has the value and removing the key would break key parity for no gain.

### Required test changes

`apps/web/tests/unit/ThemeSwitcher.test.ts`:

| Test | Change |
|---|---|
| "exposes a tri-state radiogroup…" | rename to "binary"; `toHaveLength(3)` → `2`; checked label `es['theme.system']` → `es['theme.light']` (the `stubMatchMedia` mock returns `matches: false` ⇒ resolved `'light'`) |
| "…in English when locale is en" | same rename; `en['theme.system']` → `en['theme.light']` |
| "selects a theme on click…" | unchanged (still passes) |
| "announces the new state…" | unchanged |
| "ArrowRight moves selection…" | queries the **system** radio — retarget to the light radio; expectation `'light'` → `'dark'` |
| "renders both … variants" | unchanged |
| "…44px-touch-target class" | `toHaveLength(3)` → `2` |
| "cycling button advances mode (system→light→dark→system)" | rewrite to a 2-state cycle: first click ⇒ `'dark'`, second ⇒ `'light'` |
| **new** | "a dark system preference shows Dark checked before any explicit choice" — `stubMatchMedia` with `matches: true`, assert checked label is `theme.dark` while `controller.mode === 'system'` |

`apps/web/tests/e2e/theme-persistence.spec.ts`:

| Test | Change |
|---|---|
| first-paint / OS-fallback tests | unchanged |
| ">=768px segmented control" | `toHaveCount(3)` → `2` |
| "<768px cycling button" | text regex `/Sistema\|Claro\|Oscuro/i` → `/Claro\|Oscuro/i` |

## Slice 4 — `PipelineExplainer.svelte`

New file `apps/web/src/lib/components/PipelineExplainer.svelte`. Static, non-interactive, **no** `role="status"` / `aria-live` (spec scenario 2).

```svelte
<script lang="ts">
  import { getI18nContext } from '$lib/i18n/i18n.svelte';
  const i18n = getI18nContext();
  const STEPS = ['upload', 'validation', 'provenance', 'extraction', 'identifiers', 'scoring'] as const;
</script>

<section class="max-w-reading" aria-labelledby="pipeline-heading">
  <h2 id="pipeline-heading" class="m-0 mb-4 text-lg font-semibold">
    {i18n.t('upload.pipeline.heading')}
  </h2>
  <ol class="m-0 grid list-none grid-cols-1 gap-4 p-0 sm:grid-cols-2 lg:grid-cols-3">
    {#each STEPS as step, index (step)}
      <li class="flex gap-3 rounded-ui border border-ui-line bg-ui-surface p-4">
        <span
          aria-hidden="true"
          class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-ui-line font-mono text-sm text-ui-muted tabular-nums"
        >{index + 1}</span>
        <div class="flex flex-col gap-1">
          <p class="m-0 font-semibold">{i18n.t(`upload.pipeline.step.${step}.title`)}</p>
          <p class="m-0 text-sm text-ui-muted">{i18n.t(`upload.pipeline.step.${step}.detail`)}</p>
        </div>
      </li>
    {/each}
  </ol>
</section>
```

Wiring in `+page.svelte` — inside the existing idle branch, directly after `<DropZone />`:

```svelte
{#if workspace.status === 'idle'}
  <DropZone disabled={false} onselect={(file) => workspace.selectFile(file)} />
  <PipelineExplainer />
{:else if …}
```

`ReconciliationNotice` is untouched and stays mounted above the status region, so the limitation statement is not displaced.

### New i18n keys (13, identical key set in `es.json` and `en.json`)

Namespace is `upload.pipeline.*` — reuses the existing `upload.*` namespace, so DESIGN.md §13's namespace list needs no edit.

| Key | ES | EN |
|---|---|---|
| `upload.pipeline.heading` | Qué hace este análisis | What this analysis does |
| `…step.upload.title` | Subís el comprobante | You upload the receipt |
| `…step.upload.detail` | Arrastrás o elegís una imagen del comprobante en PNG, JPG o WebP, hasta 10 MB. | You drag or pick a receipt image in PNG, JPG or WebP, up to 10 MB. |
| `…step.validation.title` | Validamos el archivo | We validate the file |
| `…step.validation.detail` | Revisamos formato, tamaño y dimensiones antes de analizar el contenido. | We check format, size and dimensions before analysing the content. |
| `…step.provenance.title` | Inspeccionamos metadata y procedencia | We inspect metadata and provenance |
| `…step.provenance.detail` | Leemos la metadata del archivo y las credenciales de contenido C2PA cuando están presentes. | We read the file metadata and C2PA content credentials when they are present. |
| `…step.extraction.title` | Extraemos los datos con OCR | We extract the data with OCR |
| `…step.extraction.detail` | El servicio lee monto, fecha, CBU/CVU y CUIT/CUIL del comprobante con OCR propio. | The service reads amount, date, CBU/CVU and CUIT/CUIL from the receipt with its own OCR. |
| `…step.identifiers.title` | Validamos los identificadores | We validate the identifiers |
| `…step.identifiers.detail` | Comprobamos los dígitos verificadores de CBU/CVU y CUIT/CUIL extraídos. | We check the verification digits of the extracted CBU/CVU and CUIT/CUIL. |
| `…step.scoring.title` | Calculamos riesgo y confianza | We compute risk and confidence |
| `…step.scoring.detail` | Combinamos las señales en un puntaje de riesgo y una confianza del análisis. | We combine the signals into a risk score and an analysis confidence value. |

No string contains `real`, `fake`, `authentic`, `auténtico`, `verificado` or "verified transfer" (spec scenario 3, DESIGN.md §5).

Also in slice 4: `docs/PRD.md` gains **FR-013** (static idle-state pipeline explainer, bilingual, non-live, six steps derived from FR-001…FR-007) and the DESIGN.md §4.1 amendment below.

## Slice 5 — Docs replacement text

**`docs/DESIGN.md` §4.1** — replace the bullet list with:

```text
- Headline explains artifact-level risk analysis.
- Large drop zone is immediately visible.
- Supported formats and 10 MB limit are visible.
- A static six-step pipeline explainer sits directly below the drop zone. It
  describes the real steps (upload → file validation → metadata/C2PA
  provenance → OCR extraction → CBU/CVU and CUIT/CUIL validation → risk and
  confidence scoring), is non-interactive, and carries no live-region
  semantics — it is not `ProcessingStages` (§4.3). PRD FR-013.
- Privacy line appears adjacent to the upload action; the explainer never
  displaces the reconciliation-limitation statement (§5).
- No large marketing section delays the tool.
```

**`docs/DESIGN.md` §12** — two table rows plus the closing paragraph:

```text
| Control | Binary segmented control (Light · Dark) at ≥768 px; a cycling icon button with a visible current-state label below 768 px. Touch target ≥ 44 × 44 px. |
| Default | First paint follows `prefers-color-scheme`; the control reflects the *resolved* theme, so no third "System" option is exposed. |
```

closing paragraph replacement:

```text
Stored value: `rrd.theme ∈ {light, dark}`, applied by setting `data-theme` and
`color-scheme` on `<html>` (design.md DD3). Nothing is stored until the user
makes an explicit choice, so an untouched install keeps following the OS
preference live via `matchMedia`. `ThemeMode` retains an internal `'system'`
value as that pre-choice default; it is never persisted and never rendered as
an option. Cookie + SSR was rejected because it needs server state,
contradicting the static-deployable web service; CSS-only `@media` was
rejected for giving the user no override. A visible third "System" control was
removed in the ui-design-refresh change: it duplicated the already-automatic
default while costing a third of the control's width.
```

**`README.md`** stack table: `custom CSS` → `Tailwind CSS v4 (@tailwindcss/vite) over DESIGN.md tokens`.

## File Changes

| Slice | File | Action |
|---|---|---|
| 1 | `apps/web/package.json`, `package-lock.json` | Modify (add `tailwindcss`, `@tailwindcss/vite`) |
| 1 | `apps/web/vite.config.ts` | Modify (plugin) |
| 1 | `apps/web/src/app.css` | Modify (imports, variant, `@theme inline`, 2 `@utility`) |
| 2a | `DropZone`, `FilePreview`, `ErrorPanel`, `ReconciliationNotice`, `ProcessingStages` (wrapper only), `+layout.svelte`, `+page.svelte` | Modify |
| 2b | `ResultView`, `ScoreSummary`, `EvidenceItem`, `EvidenceList`, `ExtractedDataTable`, `ReconciliationChecklist`, `TechnicalDetail`, `+page.svelte` (reset button) | Modify |
| 3 | `ThemeSwitcher.svelte`, `tests/unit/ThemeSwitcher.test.ts`, `tests/e2e/theme-persistence.spec.ts` | Modify |
| 4 | `lib/components/PipelineExplainer.svelte` | Create |
| 4 | `+page.svelte`, `i18n/messages/{es,en}.json`, `docs/PRD.md`, `docs/DESIGN.md` §4.1, new `tests/unit/PipelineExplainer.test.ts` | Modify / Create |
| 5 | `docs/DESIGN.md` §12, `README.md` | Modify |

Untouched in every slice: `theme.svelte.ts`, `app.html`, `LanguageSwitcher.svelte`, `LiveRegion.svelte`, the API client, `workspace.svelte.ts`, `apps/api/`, `docs/API.md`.

## Review Workload Forecast

| Slice | Authored ± lines (est.) | 400-line budget risk | Note |
|---|---|---|---|
| 1 | ~75 add, ~2 mod | **Low** | `package-lock.json` is generated — excluded from authored count |
| 2a | ~150 del, ~85 add ≈ **235** | **Medium** | Style-block deletion dominates; splitting further would fragment one visual language |
| 2b | ~205 del, ~95 add ≈ **300** | **Medium-High** | Closest to budget. If apply-time counting exceeds 400, split at `ResultView`+`ScoreSummary`+`EvidenceItem/List` vs `ExtractedDataTable`+`ReconciliationChecklist`+`TechnicalDetail` |
| 3 | ~40 component, ~70 test ≈ **110** | **Low-Medium** | |
| 4 | ~35 component, ~30 i18n, ~40 test, ~25 docs ≈ **130** | **Medium** | |
| 5 | ~40 | **Low** | Docs only |

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit | Existing 15-component suite must stay green through 2a/2b | Assertions target roles/text, not classes — style-only conversion should require **zero** test edits. Any test that breaks reveals a markup change that should not have happened. |
| Unit | Binary switcher | Edits listed in slice 3, plus the new dark-first-paint test |
| Unit | `PipelineExplainer` | Renders 6 `<li>`, ES and EN, no `role="status"`/`aria-live` attribute, and a forbidden-word scan over both locales' `upload.pipeline.*` values |
| Unit | i18n key parity | Existing `key-parity.test.ts` covers the 13 new keys; ES+EN land in one commit |
| E2E | Theme cycle and 44 px targets | Edits listed in slice 3 |
| E2E | Idle state | New assertion that the explainer is visible below the drop zone and the disclaimer is still present |
| Manual | Slice 1 zero-diff | Before/after screenshots in light and dark at 375 px and 1024 px |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary. All changes are client-side styling, markup, i18n strings and documentation.

## Migration / Rollout

No migration required. No persisted data, storage key, or API contract changes. Each slice is one PR into `dev` and reverts independently per the proposal's rollback plan.

## Open Questions

- [ ] Confirm at apply time that `@tailwindcss/vite` resolves cleanly against Vite 5.4.11 and that `tailwindcss()` must precede `sveltekit()` in the plugin array.
- [ ] Confirm the no-preflight import triple (`tailwindcss/theme.css` + `tailwindcss/utilities.css` with an explicit `@layer` statement) matches the currently shipped v4 file layout.
- [ ] Confirm `border`/`divide` utilities render correctly without preflight (expected: yes, via `@property --tw-border-style`).
- [ ] `color-mix()` in the button hover states assumes no support target below Chrome 111 / Safari 16.2 / Firefox 113 — confirm against the project's browser baseline, otherwise substitute `opacity: 0.88`.

## Key Learnings

1. Tailwind v4's `--color-*` namespace collides head-on with the DESIGN.md token names, so the bridge must use prefixed Tailwind-facing names to avoid a self-referential `var()` cycle.
2. Setting `--spacing: var(--space-1)` makes Tailwind's numeric spacing utilities land exactly on the existing 4 px grid token names with no per-step mapping.
3. Preflight is a competing base layer to DESIGN.md §6.2, so omitting it is what actually preserves slice 1's zero-visual-diff contract.
4. A binary theme control must derive its checked state from `ThemeController.resolved`, not `mode`, because `mode` stays `'system'` until the first explicit choice.
5. Unlayered `:root` declarations in `app.css` outrank Tailwind's `@layer theme` defaults, which is why `--font-sans` and `--font-mono` need no bridge entry at all.
