# Design: UI Frontend Implementation

## Technical Approach

A single-route SvelteKit 5 app under `apps/web/`, prerendered, with three layers: `lib/api` (only module that knows HTTP), `lib/features/receipt-analysis` (runes state machine + containers), `lib/components` (dumb presentational). `lib/i18n` and `lib/theme` are cross-cutting rune classes provided through Svelte context. Delivered as 5 chained PRs into `dev` (slice 1 splits into 1a/1b as pre-agreed in the proposal).

## Architecture Decisions

| # | Decision | Choice | Alternatives rejected | Rationale |
|---|---|---|---|---|
| DD1 | State container | One `AnalysisWorkspace` class in `workspace.svelte.ts` using `$state`/`$derived`, instantiated in `+page.svelte` and passed via `setContext` | Svelte 4 `writable` stores; module-level rune singleton | Runes are the Svelte 5 idiom; a per-instance class keeps SSR/prerender free of shared state and lets Vitest instantiate isolated workspaces |
| DD2 | Failure taxonomy | Discriminated union `AnalyzeFailure = { kind:'problem' } \| { kind:'network' } \| { kind:'malformed' } \| { kind:'client-validation' }` | Throwing `Error` subclasses; returning `ProblemDetails \| null` | `fetch` rejecting (API down, CORS blocked, DNS) is semantically distinct from a structured `problem+json` and needs different copy ("no pudimos contactar el servicio") and retry affordance |
| DD3 | Theme first paint | Blocking inline `<script>` in `app.html` reading `rrd.theme`, setting `data-theme` + `color-scheme` on `<html>` | CSS-only `@media`; post-hydration effect | DESIGN.md §12 mandates it; without it light tokens flash before a dark preference applies. Cost is ~8 uncompressed lines, no network |
| DD4 | i18n runtime | Hand-rolled `I18n` rune class + flat JSON per locale, both bundled eagerly | `paraglide-js`; lazy `import()` per locale | Locked in the proposal. Eager bundling because both files are small (~5 KB) and locale switching must be synchronous with no loading state |
| DD5 | Missing-key fallback | active locale → `es` → raw key (never empty); `console.warn` only in `import.meta.env.DEV` | Return empty string; throw | DESIGN.md §13 fallback chain; a visible raw key is a debuggable failure, an empty string is a silent one |
| DD6 | API base URL | `PUBLIC_API_BASE_URL` via `$env/static/public`, with a committed non-secret `apps/web/.env` = `http://localhost:8000` plus `.env.example` | `$env/dynamic/public`; hardcoded default in code | Locked in the proposal. **Gotcha**: `$env/static/public` fails the build when the var is unset and supports no code-level default — the committed `.env` is what makes "defaults to localhost:8000" true |
| DD7 | Disclaimer banner | `ReconciliationNotice.svelte` rendered unconditionally by the layout in idle *and* result contexts, never behind a state branch | Render only in result; render inside the result card | AGENTS.md MVP1 invariant + DESIGN.md §5/§14 — an always-mounted component cannot be skipped by a state bug |

## Data Flow

    DropZone ──file──> AnalysisWorkspace ($state) ──FormData──> analyzeReceipt()
        ^                    │                                      │
        |                    │<── AnalyzeResponse | AnalyzeFailure ──┘
     ErrorPanel <────────────┤
     ResultView  <───────────┘   (locale switch re-renders from held state — no refetch)

    app.html inline script ──> <html data-theme> <── ThemeController ($state) <── ThemeSwitcher

### Workspace state machine (DESIGN.md §4)

`idle → selected → uploading → (result | error)`

| Error variant | Trigger | File retained? | Next |
|---|---|---|---|
| `rate-limited` | 429 | Yes | re-`analyze` after `Retry-After` |
| `timeout` | 504 | Yes | re-`analyze` |
| `network` | `fetch` rejects | Yes | re-`analyze` |
| `rejected-file` | 400 / 413 / 415 / 422 | No → `idle` | pick another file |
| `client-validation` | local type/size check, no request sent | No → `idle` | pick another file |

Retaining the file is in-memory only (`File` object). No `localStorage`/`sessionStorage`/IndexedDB/cookie write of image bytes or results, ever.

## File Changes

### Slice 1a — scaffold, upload, real API call, minimal result
| File | Action |
|---|---|
| `apps/web/{package.json,svelte.config.js,vite.config.ts,tsconfig.json,.env,.env.example,.gitignore}` | Create — SvelteKit 5, TS, `@sveltejs/adapter-static`, `vitest`, `@testing-library/svelte`, `jsdom`, `@playwright/test`. No UI component library |
| `apps/web/src/{app.html,app.css,app.d.ts}` | Create — DESIGN.md §6.3 tokens, §6.2 type scale, §6.4 spacing |
| `apps/web/src/routes/{+layout.svelte,+page.svelte,+page.ts}` | Create — `prerender = true` |
| `apps/web/src/lib/api/types.ts` | Create — mirrors `schemas.py` exactly |
| `apps/web/src/lib/api/client.ts` | Create — `analyzeReceipt(file): Promise<AnalyzeResult>` |
| `apps/web/src/lib/api/errors.ts` | Create — status→code map, `Retry-After` parse |
| `apps/web/src/lib/features/receipt-analysis/workspace.svelte.ts` | Create — DD1 state machine |
| `apps/web/src/lib/components/{DropZone,FilePreview,ProcessingStages,ErrorPanel,ReconciliationNotice}.svelte` | Create |
| `apps/web/tests/unit/{client,workspace}.test.ts` | Create |
| `docs/API.md` | Modify — §3 extracted-data example (below) |
| `docs/wiki/Local-Setup.md`, `README.md` | Modify — Web section: `RECEIPT_RISK_CORS_ALLOWED_ORIGINS=http://localhost:5173`, `npm run dev` |
| `.github/workflows/ci.yml` | Modify — Node 20 job: `npm ci`, `svelte-check`, `vitest run` |
| `docs/features/ui-frontend-implementation/{SDD,TDD,RDD}.md` | Create — AGENTS.md mirror rule |

### Slice 1b — full result presentation
`ScoreSummary.svelte`, `EvidenceList.svelte` + `EvidenceItem.svelte`, `ExtractedDataTable.svelte`, `ReconciliationChecklist.svelte`, `TechnicalDetail.svelte`, `ResultView.svelte`; `lib/features/receipt-analysis/format.ts` (`Intl` amount/date); matching Vitest specs.

### Slice 2 — theme
`lib/theme/theme.svelte.ts`, `lib/components/ThemeSwitcher.svelte`, `app.html` inline script, `app.css` `[data-theme='dark']` block + `.theme-transition` (160 ms, `prefers-reduced-motion` guarded), `tests/unit/theme.test.ts`.

### Slice 3 — i18n
`lib/i18n/{i18n.svelte.ts,resolve.ts,enum-map.ts,messages/es.json,messages/en.json}`, `lib/components/LanguageSwitcher.svelte`, replacement of every hardcoded literal from 1a/1b/2, `tests/unit/{i18n-resolution,key-parity}.test.ts`.

### Slice 4 — a11y + e2e
`lib/components/LiveRegion.svelte`, focus management in `ResultView`, `tests/e2e/*.spec.ts`, `playwright.config.ts`, CI e2e job.

## Interfaces / Contracts

```ts
// lib/api/types.ts — mirrors schemas.py, NOT docs/API.md
export interface ExtractedFieldModel {
  value?: string | null; masked_value?: string | null;
  confidence: number; is_checksum_valid?: boolean | null;
}
export interface SignalModel {
  code: string; category: string; severity: string; confidence: number;
  description: string; evidence: Record<string, string>; score_contribution: number;
}
export interface AnalyzeResponse {
  analysis_id: string; engine_version: string; ruleset_version: string;
  classification: string; risk_score: number; confidence_score: number;
  recommended_action: string; signals: SignalModel[];
  extracted_data: Record<string, ExtractedFieldModel>;
  analyzer_statuses: { analyzer: string; status: string; duration_ms: number }[];
  limitations: string[]; duration_ms: number;
}
export interface ProblemDetails {
  type: string; title: string; status: number; detail: string;
  instance: string; request_id: string; code: string;
}
export type AnalyzeResult =
  | { ok: true; data: AnalyzeResponse }
  | { ok: false; failure: AnalyzeFailure };
```

`extracted_data` is a **map with unknown keys**; the table iterates entries and looks up `result.field.<key>` labels with the raw key as fallback. Today `mappers.py` emits only `amount`, `destination_cbu`, `cuit`, `date_time`; `destination_cbu`/`cuit` carry `masked_value` and never `value`; `is_checksum_valid` is currently never populated, so the table must treat it as optional.

### docs/API.md §3 corrected `extracted_data`

```json
"extracted_data": {
  "amount": { "value": "125000.00", "confidence": 0.97 },
  "date_time": { "value": "2026-09-01T14:43:00-03:00", "confidence": 0.88 },
  "destination_cbu": { "masked_value": "******************5678", "confidence": 0.94 },
  "cuit": { "masked_value": "*******4321", "confidence": 0.9 }
}
```

No `currency` key (never existed on the model), no `beneficiary_name`/`operation_id` (not extracted in MVP1), `is_checksum_valid` omitted because it is not populated today.

### Component props sketch

| Component | Props | Responsibility |
|---|---|---|
| `DropZone` | `disabled`, `onselect(file)` | Drag/click/keyboard file choice; wraps a real `<input type=file>` |
| `ScoreSummary` | `classification`, `riskScore`, `confidenceScore`, `recommendedAction` | Text-first classification, `74 / 100`, no risk color when `INCONCLUSIVE` |
| `EvidenceList` | `signals` | Sort by severity then `score_contribution` desc |
| `ExtractedDataTable` | `data: Record<string, ExtractedFieldModel>` | Label/value rows; renders `masked_value` when present, never unmasks |
| `ReconciliationChecklist` | `data` | Manual comparison items; renders even when a field is absent |
| `ErrorPanel` | `variant`, `retryAfter?`, `onretry?` | Actionable copy only, never `detail` raw or a stack trace |
| `ReconciliationNotice` | — | Always-mounted §5 limitation sentence |
| `ThemeSwitcher` | — (context) | Tri-state radio group, `aria-checked` |
| `LanguageSwitcher` | — (context) | ES/EN, `aria-pressed`, per-language `aria-label` |

### i18n contract

```ts
locale = ?lang= → localStorage['rrd.locale'] → navigator.languages → 'es'   // DESIGN.md §13
t(key: string, params?: Record<string, string|number>): string              // never returns ''
```
`?lang=` is validated against `['es','en']`, applied for the visit, then persisted. Server enums map to `result.classification.<CODE>` / `result.action.<CODE>` / `evidence.severity.<level>` / `evidence.signal.<CODE>`; an unknown signal code falls back to the server `description` string.

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit | `analyzeReceipt` maps 400/413/415/422/429/504 → failure variants; `fetch` rejection → `network`; unparseable body → `malformed`; `Retry-After` parse | Vitest + stubbed `fetch` |
| Unit | Workspace transitions, especially 429 retains the `File` and `415` clears it | Vitest on the class directly, no DOM |
| Unit | i18n resolution order (4 cases), missing key → `es` → raw key, `?lang=zz` ignored | Vitest + stubbed `localStorage`/`navigator` |
| Unit | **Key parity**: `Object.keys(es)` set === `Object.keys(en)` set, with the diff printed both ways; plus an assertion that every value is a string (enforces flatness) | Vitest importing both JSON files |
| Unit | Theme: `system` follows `matchMedia`, explicit choice persists, reduced motion skips the transition class | Vitest + `matchMedia` stub |
| Component | DropZone keyboard path, masked fields never render `value`, `ReconciliationNotice` present in idle and result, no forbidden word (`real`/`fake`/`authentic`/`verified`) in rendered output | `@testing-library/svelte` |
| E2E | Upload → result happy path; theme and locale survive reload; no theme flash | Playwright |

A **smoke e2e is valuable in 1a already** (load page, drop zone visible, disclaimer visible) — cheap, and it makes the Playwright harness exist before slice 4 has to write five specs at once. Slice 4 then only adds assertions.

Playwright slice 4 sketch: route-intercept `**/v1/receipts/analyze` with a fixture `AnalyzeResponse`; `setInputFiles` a synthetic PNG; assert the result heading, `74 / 100`, at least one evidence item, a masked CBU matching `/^\*+\d{4}$/`, and the limitation sentence; then set `localStorage['rrd.theme']='dark'`, reload, and assert `<html data-theme="dark">` on the *first* paint via an `addInitScript` probe; then switch to EN and assert the heading text changed with **no** second network request. One real-API spec stays opt-in behind an env flag so CI is not coupled to a running API.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary. The only untrusted input is the user's own local file, which is validated client-side (type/size) purely as UX and re-validated authoritatively server-side; the client never executes or interprets file contents beyond `URL.createObjectURL` for preview (revoked on replace/reset).

## Review Workload Forecast

| Slice | 400-line budget risk | Reasoning |
|---|---|---|
| 1a | **High** | Scaffold configs + tokens CSS + client + state machine + 5 components; config/CSS lines are cheap to review but still count. Likely 500–650 lines |
| 1b | Medium | ~6 presentational components + formatters + specs |
| 2 | Low | One rune class, one component, one CSS block, one inline script |
| 3 | **High** | Two message JSONs (~120 keys each) plus a literal-replacement sweep across every component from 1a/1b/2. Mostly mechanical — a `size:exception` is more honest here than a further split, but sub-splitting by namespace (`upload/errors` then `result/evidence`) is the fallback |
| 4 | Medium | Live region + focus management + Playwright specs |

## Migration / Rollout

No data migration. Each slice is one PR into `dev`; PR #1a targets `dev`, each later slice targets the previous slice's branch until merged. Reverting any of 1b–4 leaves a working client; reverting 1a removes `apps/web/` entirely. The `docs/API.md` correction is an independent commit inside 1a.

## Open Questions

- [ ] None blocking. Two items for `sdd-tasks` to record rather than resolve: whether slice 3 takes a `size:exception` or a namespace sub-split, and whether the opt-in real-API Playwright spec runs in CI at all (recommended: no).

## Key Learnings

1. The real `extracted_data` map contains only `amount`, `destination_cbu`, `cuit`, and `date_time`, so `docs/API.md`'s `beneficiary_name` and `operation_id` entries are fictional as well as its `currency` field.
2. `mappers.py` never populates `is_checksum_valid`, so the extracted-data table must treat that flag as optional rather than assume it accompanies `destination_cbu`.
3. `$env/static/public` has no code-level default, so a committed non-secret `apps/web/.env` is what actually makes `PUBLIC_API_BASE_URL` default to `http://localhost:8000`.
4. A `fetch` rejection caused by a missing CORS allowlist entry is indistinguishable from the API being down, which is why the local-setup docs must state `RECEIPT_RISK_CORS_ALLOWED_ORIGINS=http://localhost:5173` explicitly.
5. Slices 1a and 3 are the two High-risk slices against the 400-line review budget, for opposite reasons: scaffold breadth versus mechanical message-key sweep.
