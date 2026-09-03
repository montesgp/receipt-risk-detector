# Product design guide

## 1. Design objective

Create a calm, fast and technically credible document-analysis experience. The interface helps a beneficiary answer:

1. What did the engine find?
2. How confident is it?
3. Why did the receipt receive this score?
4. What should I verify manually now?

The interface must build trust through clarity and evidence, never through exaggerated certainty or decorative “AI” styling.

## 2. Experience principles

1. **The task leads.** Upload is the focal action in the first viewport.
2. **Evidence is visible.** A score without its strongest reasons is incomplete.
3. **Two reading speeds.** Show the assessment immediately; keep technical details available for audit.
4. **Uncertainty is designed, not hidden.** Confidence, missing evidence and analyzer failures remain visible.
5. **Privacy is stated plainly.** Explain that the image is not retained.
6. **One continuous canvas.** Prefer spacing and typography over a wall of cards.
7. **Fast perceived progress.** Acknowledge the selected file immediately and expose processing stages.

## 3. Information architecture

MVP 1 is a single-purpose application, not a dashboard.

```text
Header
└── Product identity, language switcher (§13), theme switcher (§12), API docs, GitHub

Main workspace
├── Outcome-oriented headline
├── Upload area
├── Privacy and limitation statement
├── Processing state
└── Analysis result
    ├── Risk and confidence
    ├── Strongest evidence
    ├── Extracted transfer data
    ├── Manual reconciliation checklist
    └── Full technical detail

Footer
└── Open-source, privacy and disclaimer links
```

Do not mention or reproduce any external reference product in UI copy or repository documentation.

## 4. Primary states

### 4.1 Idle

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

Suggested Spanish copy:

```text
Analizá un comprobante antes de conciliarlo

Detectamos señales de manipulación, procedencia digital e
inconsistencias para ayudarte a revisar una transferencia.

Arrastrá o seleccioná un comprobante
PNG, JPG o WebP · máximo 10 MB
```

### 4.2 File selected

- Show a constrained image preview.
- Show filename, type and human-readable size.
- Offer replace and analyze actions.
- Never expose full financial identifiers outside the preview.

### 4.3 Processing

Show real stages when the API can expose them, or honest coarse phases when it cannot:

```text
✓ Archivo validado
✓ Metadata inspeccionada
● Extrayendo datos
○ Validando información
○ Calculando evaluación
```

Do not fabricate precise progress percentages. Use indeterminate progress until measurable stage completion exists.

### 4.4 Result

The result follows this visual priority:

1. Classification and risk score.
2. Confidence and limitation.
3. Strongest evidence.
4. Manual reconciliation action.
5. Extracted data.
6. Analyzer and version details.

### 4.5 Error

Explain what the user can do next. Preserve the selected file only in browser memory when retry is safe. Never display a raw stack trace or tool error.

## 5. Result language

Allowed:

```text
Riesgo bajo
Revisión recomendada
Sospechoso
Riesgo alto
No concluyente
No detectamos evidencia suficiente
Se encontró una señal de procedencia asociada a IA
```

Forbidden as system outcomes:

```text
Transferencia real
Transferencia falsa
Comprobante auténtico
Pago verificado
Fraude confirmado
100% seguro
```

Every result must include:

> Este análisis evalúa el comprobante presentado. Confirmá la acreditación en la cuenta beneficiaria antes de entregar productos o servicios.

## 6. Visual language

### 6.1 Overall tone

- Precise, restrained and engineering-led.
- Mostly neutral surfaces.
- No gradients, glows, glassmorphism, decorative grids or AI-themed imagery.
- Use color sparingly for semantic state and always pair it with text/iconography.
- Support light and dark themes from the same semantic tokens.

### 6.2 Typography

Use a variable sans family with excellent UI legibility; recommended default: `Geist Sans` or a system fallback stack. Use a monospaced family only for request IDs, hashes, versions, code and raw identifiers.

Suggested roles:

```text
Display       48–64 px desktop / 36–44 px mobile
Page title    32–40 px
Section title 24–28 px
Card title    18–20 px
Body          16–18 px
Label         13–14 px
Code          13–14 px monospace
```

Use sentence case. Keep reading lines near 60–70 characters. Do not shrink explanatory copy below comfortable reading size.

### 6.3 Color tokens

Names are semantic; agents may tune exact values while preserving WCAG AA contrast.

```css
:root {
  --color-canvas: #f7f7f5;
  --color-surface: #ffffff;
  --color-text: #141414;
  --color-text-muted: #666666;
  --color-border: #deded9;
  --color-action: #171717;
  --color-action-text: #ffffff;
  --color-risk-low: #247a52;
  --color-risk-review: #8a6500;
  --color-risk-high: #a33a32;
  --color-focus: #346beb;
}

[data-theme='dark'] {
  --color-canvas: #0d0d0d;
  --color-surface: #151515;
  --color-text: #f3f3f1;
  --color-text-muted: #a1a19a;
  --color-border: #30302d;
  --color-action: #f3f3f1;
  --color-action-text: #111111;
  --color-risk-low: #5fc493;
  --color-risk-review: #d6aa43;
  --color-risk-high: #ed7b70;
  --color-focus: #75a0ff;
}
```

Never use green to mean “authentic.” It means only low artifact risk.

### 6.4 Spacing and grid

- 4 px base unit.
- Content max width: approximately 1120 px.
- Reading content: approximately 680–760 px.
- Desktop: 12-column layout.
- Tablet: 6 columns.
- Mobile: 4 columns.
- Major section spacing: 64–96 px desktop, 40–64 px mobile.
- Component spacing should express grouping before adding borders.

### 6.5 Surfaces

Use containers only for real grouping or interaction:

- Drop zone.
- Main assessment summary.
- Individual evidence disclosures when needed.
- Code/API examples.

Do not place every metric or paragraph in a separate card. Avoid nested cards and heavy shadows. Borders should be 1 px and radii restrained, approximately 8–12 px.

## 7. Component guidance

### Drop zone

- Entire area is clickable and keyboard reachable.
- Support drag state, invalid state and selected state.
- Use a simple upload icon, heading, constraints and action.
- Do not animate continuously.

### Score summary

- Show classification as text first.
- Show risk as `74 / 100`, not `74% probability of fraud`.
- Show confidence separately.
- If `INCONCLUSIVE`, confidence and missing evidence dominate; do not force a risk color.

### Evidence list

Order by severity and score impact. Each item includes:

```text
Severity
Plain-language title
What was observed
Why it matters
Confidence
Score contribution
Optional technical detail
```

### Extracted-data table

Use aligned label/value rows. Mask CBU/CVU and CUIT/CUIL by default. Allow deliberate reveal only if product requirements later authorize it.

### Reconciliation checklist

Present amount, approximate date, originator, beneficiary and operation ID as a checklist for comparing against the beneficiary account. Do not imply that checking the screenshot is reconciliation.

## 8. Responsive behavior

- The upload task and primary result must fit naturally at 360 px width.
- Result columns stack in priority order on mobile.
- Avoid horizontal scrolling except code blocks.
- Touch targets are at least 44 × 44 px.
- The receipt preview never forces the viewport wider than the device.
- Desktop layouts may place score and strongest evidence side by side, with no more than two major columns.

## 9. Motion

- 120–220 ms for state transitions.
- Respect `prefers-reduced-motion`.
- Use motion to clarify state change, not decorate idle screens.
- Never delay result visibility for an animation.

## 10. Accessibility

- Native file input remains accessible even when visually customized.
- Drag and drop always has a keyboard/file-picker equivalent.
- Processing and completion messages use an ARIA live region.
- Focus moves to the result heading after a successful analysis only when it will not surprise keyboard users.
- Severity uses text and icons in addition to color.
- Charts are unnecessary for MVP 1; prefer exact values and evidence rows.

## 12. Theme switcher UX

Implements `ui-localization-and-theming` (FR-012 expanded per proposal D1); see
`openspec/changes/mvp-init-foundation/specs/ui-localization-and-theming/spec.md`.

| Aspect | Decision |
| --- | --- |
| Placement | Header right cluster, immediately right of the language switcher, left of API docs / GitHub links. Not in the main workspace — it must never compete with the upload action (§2.1). |
| Control | Binary segmented control (Light · Dark) at ≥768 px; a cycling icon button with a visible current-state label below 768 px. Touch target ≥ 44 × 44 px. |
| Default | First paint follows `prefers-color-scheme`; the control reflects the *resolved* theme, so no third "System" option is exposed. |
| Persistence | `localStorage['rrd.theme']`. Explicit choices persist; `system` re-subscribes to the OS preference and updates live via a `matchMedia` change listener. |
| First paint | A small blocking inline script in `app.html` sets `data-theme` before body render. Without it the light tokens flash before a dark preference applies. |
| Transition | Adding `data-theme` toggles a 160 ms transition (inside the 120–220 ms range in §9) on `background-color`, `color` and `border-color` only, applied through a temporary `theme-transition` class removed on `transitionend`. Never transition `box-shadow` or layout properties. |
| Reduced motion | Under `prefers-reduced-motion: reduce` the class is not applied; the swap is instant. |
| Accessibility | Native `<button>`/radio semantics with `aria-pressed` or `aria-checked`; focus ring uses `--color-focus`; the change is announced through the existing ARIA live region. |
| Constraint | Risk colors must keep WCAG AA contrast in both themes (§6.3). Green still means low artifact risk, never "authentic". |

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

## 13. Language switcher UX

Implements `ui-localization-and-theming` (FR-012 expanded per proposal D1); see
`openspec/changes/mvp-init-foundation/specs/ui-localization-and-theming/spec.md`.

| Aspect | Decision |
| --- | --- |
| Placement | Header right cluster, left of the theme switcher. Two-option control labelled `ES` / `EN`, each with an `aria-label` in its own language. |
| Persistence | `localStorage['rrd.locale']`; `?lang=` overrides for one visit and is then persisted, which makes bilingual links shareable. |
| Message store | `apps/web/src/lib/i18n/messages/{es,en}.json`, flat dot-namespaced keys: `common.*`, `header.*`, `upload.*`, `processing.*`, `result.*`, `evidence.*`, `errors.*`, `legal.*`, `a11y.*`. |
| Source of truth | `es.json` defines the key set (PRD is Spanish-first). A unit test asserts exact key parity between locales and fails CI on drift. |
| Fallback | Missing key → Spanish value → the raw key in development builds. Never render an empty string. |
| Server enums | `classification`, `recommended_action`, `severity` and `signals[].code` are mapped client-side to `result.*` / `evidence.signal.<CODE>` keys. An unknown code falls back to the server `description` field. The API therefore stays locale-free. |
| Switching cost | Changing locale re-renders the current `FraudAssessment` from client state. It never re-uploads the image or re-calls the API. |
| Copy rule | Both locales must respect §5: no `real`, `fake`, `authentic` or `verified` outcome, and the reconciliation limitation is present in idle and result states. |
| Number/date format | `Intl.NumberFormat` / `Intl.DateTimeFormat` with the active locale; the amount `currency` stays the server-provided code (`ARS`), never re-derived client-side. |

Resolution order: `?lang=` → `localStorage` → `navigator.languages` → `es` (design.md DD4). Localized
route prefixes (`/es/…`, `/en/…`) were rejected for duplicating routes on a single-page tool; server
`Accept-Language` negotiation was rejected for introducing the browser coupling the API forbids (D4).

## 14. Agent design acceptance checklist

- Upload action is visible in the first viewport at common laptop and mobile sizes.
- No external reference product is named or copied.
- No outcome says real, fake, authentic or verified.
- Risk and confidence are visually and semantically distinct.
- Disclaimer appears in idle and result contexts.
- Strongest evidence is visible without opening every disclosure.
- All states work in light/dark themes.
- Keyboard, focus, contrast and reduced-motion checks pass.
- The UI remains useful when one analyzer fails and the result is partial.
- Theme switcher (§12) defaults to `system`, persists an explicit choice, and never flashes the wrong theme on first paint.
- Language switcher (§13) re-renders all visible copy without re-uploading the image or re-calling the API, and both locales define the same key set.
