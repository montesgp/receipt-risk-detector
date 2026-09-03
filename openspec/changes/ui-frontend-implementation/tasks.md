# Tasks: UI Frontend Implementation

> Note: this artifact intentionally exceeds the default 530-word budget. The
> orchestrator explicitly requested 5 full ordered task lists with per-scenario
> RED/GREEN traceability and per-slice forecasts; completeness was prioritized
> over the generic size guideline for this multi-slice change.

## Overall Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 1a: 550–650 · 1b: 350–450 · 2: 120–180 · 3a: 300–400 · 3b: 250–350 · 4: 300–380 |
| 400-line budget risk | High (1a), Medium (1b), Low (2), Medium (3a), Medium (3b), Medium (4) |
| Chained PRs recommended | Yes |
| Suggested split | PR 1a → PR 1b → PR 2 → PR 3a → PR 3b → PR 4 (6 chained PRs; slice 3 sub-split, see decision below) |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Slice 3 split decision (design.md left this open)

**Decision: namespace/infra sub-split, not `size:exception`.** Slice 3 becomes
two chained PRs: **3a** (i18n runtime: resolver, rune store, seed JSON,
key-parity test, `LanguageSwitcher`) and **3b** (literal-copy replacement
sweep across every 1a/1b/2 component, done as two internal commits —
upload/errors namespace, then result/evidence namespace). Rationale:
`delivery_strategy=auto-chain` with `stacked-to-main` already gives a
mechanism to land High-risk work as independent reviewable PRs without
maintainer sign-off, so `size:exception` (which requires an explicit
approval step) is unnecessary here. 3a and 3b both land under 400 lines on
their own, whereas a single slice-3 PR would combine two unrelated risks
(a new subsystem in 3a vs. a wide mechanical diff in 3b) into one review.

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1a | Scaffold + upload + real API call + minimal result, Spanish-only, light-only | PR 1a (base: `dev`) | `npx vitest run tests/unit/client.test.ts tests/unit/workspace.test.ts` | `npx playwright test tests/e2e/smoke.spec.ts` (requires local API at `PUBLIC_API_BASE_URL`) | Delete `apps/web/` entirely; restores API-only repo state |
| 1b | Full result presentation components | PR 1b (base: PR 1a) | `npx vitest run tests/unit/format.test.ts tests/unit/*.svelte.test.ts` | Manual: upload → confirm full result renders against live API | Revert `ResultView.svelte` + child components; workspace still shows raw success without rich UI |
| 2 | Theme switcher | PR 2 (base: PR 1b) | `npx vitest run tests/unit/theme.test.ts` | Playwright smoke: toggle theme, reload, no flash (added fully in slice 4, manual check here) | Remove `lib/theme/`, `ThemeSwitcher.svelte`, inline script; app defaults to light-only |
| 3a | i18n runtime + language switcher (no literal replacement yet) | PR 3a (base: PR 2) | `npx vitest run tests/unit/i18n-resolution.test.ts tests/unit/key-parity.test.ts` | Manual: switch language, confirm switcher renders (components still Spanish-hardcoded) | Remove `lib/i18n/`, `LanguageSwitcher.svelte`; app stays Spanish-only |
| 3b | Literal-copy replacement sweep (upload/errors, then result/evidence) | PR 3b (base: PR 3a) | `npx vitest run` (full unit suite + key-parity) | Manual: switch EN/ES, confirm every visible string changes | Revert sweep commits independently per namespace; i18n infra from 3a stays intact |
| 4 | Accessibility polish + Playwright e2e | PR 4 (base: PR 3b) | `npx vitest run tests/unit/live-region.test.ts` | `npx playwright test tests/e2e/` | Remove `LiveRegion.svelte`, focus-mgmt lines, new e2e specs; app remains functionally complete |

---

## Slice 1a: Scaffold, API Client, State Machine, CORS/Env, Docs

> **Apply batch history**: batch 1 covered Phases 1–3 and docs tasks 6.1–6.2
> (scaffold + toolchain, API client, workspace state machine,
> `docs/API.md`/`Local-Setup.md`). Batch 2 covered Phase 4 (idle/upload/
> processing/error components), Phase 5.1 (wiring into `+page.svelte` + a
> Vitest smoke test proving the disclaimer renders in every state), and docs
> tasks 6.3–6.5 (README, CI Node job, SDD/TDD/RDD doc mirrors). Task 5.2
> (Playwright `smoke.spec.ts`) is explicitly deferred to slice 4, which
> already owns the Playwright e2e buildout — see 5.2's `[~]` note.

### Phase 1: Scaffold & Toolchain (no tests yet — foundation)
- [x] 1.1 Create `apps/web/{package.json,svelte.config.js,vite.config.ts,tsconfig.json}` — SvelteKit 5 + TS + `@sveltejs/adapter-static` (design File Changes / Slice 1a)
- [x] 1.2 Add `vitest`, `@testing-library/svelte`, `jsdom`, `@playwright/test` deps; wire Vitest in `vite.config.ts`
- [~] 1.3 Create `apps/web/.env` (`PUBLIC_API_BASE_URL=http://localhost:8000`), `.env.example`, `.gitignore` (DD6) — **DEVIATION**: the apply sandbox categorically denies writing any path named `.env*`, in any tool, even non-secret content. Committed `apps/web/env.sample` (identical content) plus `apps/web/.gitignore` instead, and documented the manual `cp env.sample .env` step in `docs/wiki/Local-Setup.md`. A human (or a session without this restriction) must create the real `apps/web/.env` once before `$env/static/public` resolves; verified locally in this session by exporting `PUBLIC_API_BASE_URL` as a process env var instead.
- [x] 1.4 Create `apps/web/src/{app.html,app.css,app.d.ts}` — DESIGN.md §6.3 tokens, §6.2 type scale, §6.4 spacing
- [x] 1.5 Create `apps/web/src/routes/{+layout.svelte,+page.svelte,+page.ts}` with `prerender = true`
- [x] 1.6 Verify harness: `npx svelte-check` and `npx vitest run` execute clean with zero tests (proves toolchain before any RED task)

### Phase 2: API client (DD2 failure taxonomy; spec: Validation error states, Service-unavailable, Rate-limit)
- [x] 2.1 RED `tests/unit/client.test.ts`: `analyzeReceipt` maps 400/413/415/422 → `client-validation`/`problem` variants (spec "Server-side validation error is explained")
- [x] 2.2 RED same file: 504 → `timeout`-labeled `problem`; `fetch` rejection → `network` (spec "Analysis timeout is distinguished...", "Network failure shows a connectivity state, not a result")
- [x] 2.3 RED same file: 429 → parses `Retry-After`, preserves file reference (spec "Rate limit preserves the file and surfaces retry timing")
- [x] 2.4 RED same file: unparseable body → `malformed` (DD2)
- [x] 2.5 GREEN `lib/api/types.ts` — mirrors `schemas.py` exactly (design Interfaces/Contracts)
- [x] 2.6 GREEN `lib/api/errors.ts` — status→code map, `Retry-After` parser
- [x] 2.7 GREEN `lib/api/client.ts` — `analyzeReceipt(file): Promise<AnalyzeResult>` implementing DD2
- [x] 2.8 REFACTOR extract shared fetch/error-mapping helper if duplicated across cases — `buildFailureFromResponse`/`parseRetryAfter` extracted to `lib/api/errors.ts`; no further duplication found

### Phase 3: Workspace state machine (DD1; design "Workspace state machine" table)
- [x] 3.1 RED `tests/unit/workspace.test.ts`: `idle→selected→uploading→result` happy path
- [x] 3.2 RED same file: 429 retains `File` and re-`analyze`s after `Retry-After`; 415/400/413/422 clears file back to `idle`
- [x] 3.3 GREEN `lib/features/receipt-analysis/workspace.svelte.ts` — `AnalysisWorkspace` class (`$state`/`$derived`, DD1)

### Phase 4: Idle/upload/processing/error components (spec: Idle/upload state, File selection and validation, Uploading/processing state)
- [x] 4.1 RED `DropZone` test: keyboard-operable, calls `onselect(file)` (spec "Idle state shows constraints and disclaimer")
- [x] 4.2 GREEN `lib/components/DropZone.svelte`
- [x] 4.3 RED `FilePreview` test: shows filename/type/size (spec "Valid file moves to preview")
- [x] 4.4 GREEN `lib/components/FilePreview.svelte`
- [x] 4.5 RED `ProcessingStages` test: ARIA-live region present, no fabricated percentages (spec "Processing state is announced")
- [x] 4.6 GREEN `lib/components/ProcessingStages.svelte`
- [x] 4.7 RED `ErrorPanel` test: code-derived actionable message, never raw `detail`/stack (spec "Server-side validation error is explained")
- [x] 4.8 GREEN `lib/components/ErrorPanel.svelte`
- [x] 4.9 RED `ReconciliationNotice` test: renders unconditionally in idle AND result contexts (DD7, AGENTS.md MVP1 invariant)
- [x] 4.10 GREEN `lib/components/ReconciliationNotice.svelte`

### Phase 5: Wiring + smoke e2e
- [x] 5.1 GREEN wire `DropZone`/`FilePreview`/`ProcessingStages`/`ErrorPanel`/`ReconciliationNotice` into `+page.svelte` — **DEVIATION**: wired via direct component composition in `+page.svelte` reading `workspace` (a local `const`), not `setContext(workspace)`, because slice 1a has only one consumer (`+page.svelte` itself); `setContext` is deferred to slice 1b/2/3 when `ThemeSwitcher`/`LanguageSwitcher` need cross-component access from the layout. A Vitest component test (`tests/unit/page.smoke.test.ts`) proves `ReconciliationNotice` renders in every reachable state (idle, selected, uploading, result, network error, timeout, rate-limited, rejected-file, client-validation) instead of Playwright, which is deferred to 5.2/slice 4 per scope-management.
- [~] 5.2 Playwright `playwright.config.ts` + `tests/e2e/smoke.spec.ts` — **DEFERRED to slice 4** (this apply batch prioritized the Vitest smoke coverage in 5.1 over standing up the Playwright harness under time pressure; `@playwright/test` is already a devDependency from Phase 1.2, so slice 4 only needs to add the config + spec, not the toolchain).

### Phase 6: Docs + CI
- [x] 6.1 Correct `docs/API.md` §3 `extracted_data` example to the real `ExtractedFieldModel` shape; remove fictional `beneficiary_name`, `operation_id`, `currency`; omit `is_checksum_valid` since `mappers.py` never populates it (design "docs/API.md §3 corrected `extracted_data`")
- [x] 6.2 Update `docs/wiki/Local-Setup.md`: document `RECEIPT_RISK_CORS_ALLOWED_ORIGINS=http://localhost:5173` as a required local API env var, plus `npm run dev` steps
- [x] 6.3 Update `README.md` local-dev section with the same web/CORS steps
- [x] 6.4 Update `.github/workflows/ci.yml`: add Node 20 job (`npm ci`, `svelte-check`, `vitest run`)
- [x] 6.5 Create `docs/features/ui-frontend-implementation/{SDD,TDD,RDD}.md` mirrors (AGENTS.md rule)

#### Slice 1a Review Workload Forecast
| Field | Value |
|---|---|
| Estimated changed lines | 550–650 |
| 400-line budget risk | High |
| Note | Scaffold configs + tokens CSS + client + state machine + 5 components; not further splittable — a partial SvelteKit scaffold is not independently reviewable/mergeable. Ship as a single High-risk PR per proposal's pre-agreed sub-split. |

---

## Slice 1b: Full Result Presentation

### Phase 1: Formatters
- [x] 1.1 RED `tests/unit/format.test.ts`: `Intl` amount/date formatting cases
- [x] 1.2 GREEN `lib/features/receipt-analysis/format.ts`

### Phase 2: Result components (spec "Successful result display"; design component props sketch)
- [x] 2.1 RED `ScoreSummary` test: text-first classification, no forced risk color when `INCONCLUSIVE` (spec "INCONCLUSIVE result does not force a risk color")
- [x] 2.2 GREEN `lib/components/ScoreSummary.svelte`
- [x] 2.3 RED `EvidenceList`/`EvidenceItem` test: sorted by severity then `score_contribution` desc
- [x] 2.4 GREEN `lib/components/EvidenceList.svelte` + `EvidenceItem.svelte`
- [x] 2.5 RED `ExtractedDataTable` test: renders `masked_value` when present, never unmasks `value`, treats `is_checksum_valid` as optional
- [x] 2.6 GREEN `lib/components/ExtractedDataTable.svelte`
- [x] 2.7 RED `ReconciliationChecklist` test: renders items even when a field is absent
- [x] 2.8 GREEN `lib/components/ReconciliationChecklist.svelte`
- [x] 2.9 RED `TechnicalDetail` test: shows `engine_version`/`ruleset_version`/`analyzer_statuses`
- [x] 2.10 GREEN `lib/components/TechnicalDetail.svelte`
- [x] 2.11 RED forbidden-word test on full rendered result (spec "No forbidden authenticity language appears": no "real"/"fake"/"authentic"/"verified transfer")
- [x] 2.12 GREEN `lib/components/ResultView.svelte` composing all above; `limitations[]` always rendered (spec "Full result renders from the live response")

### Phase 3: Wiring
- [x] 3.1 GREEN wire `ResultView` into workspace `result` state in `+page.svelte`

#### Slice 1b Review Workload Forecast
| Field | Value |
|---|---|
| Estimated changed lines | 350–450 |
| 400-line budget risk | Medium |
| Note | ~6 presentational components + formatter + specs; independently revertible, no further split needed |

---

## Slice 2: Theme Switcher

### Phase 1: Theme core (DD3; spec "Manual theme toggle", "System-preference default", "Theme persists after reload")
- [x] 1.1 RED `tests/unit/theme.test.ts`: `system` follows `matchMedia`; explicit choice persists to `localStorage['rrd.theme']`; reduced motion skips transition class
- [x] 1.2 GREEN `lib/theme/theme.svelte.ts` — `ThemeController` (`$state`)
- [x] 1.3 GREEN `app.html` blocking inline script (DD3): reads `rrd.theme`, sets `data-theme` + `color-scheme` before body paint
- [x] 1.4 GREEN `app.css`: `[data-theme='dark']` block + `.theme-transition` (160 ms, `prefers-reduced-motion` guarded)

### Phase 2: Switcher UI (spec "Switchers are keyboard-operable with visible focus", "State change is announced and not color-only")
- [x] 2.1 RED `ThemeSwitcher` test: tri-state `aria-checked`, keyboard-operable, visible `--color-focus` state
- [x] 2.2 GREEN `lib/components/ThemeSwitcher.svelte`
- [x] 2.3 GREEN wire `ThemeSwitcher` into layout via context; state change announced through ARIA live region — **NOTE**: announced via a local `role="status"` region inside `ThemeSwitcher.svelte` itself, not the shared `LiveRegion.svelte` (that component is slice 4 scope and does not exist yet)

#### Slice 2 Review Workload Forecast
| Field | Value |
|---|---|
| Estimated changed lines | 120–180 |
| 400-line budget risk | Low |
| Note | One rune class, one component, one CSS block, one inline script — no split needed |

---

## Slice 3a: i18n Runtime + Language Switcher

### Phase 1: i18n core (DD4, DD5; design i18n contract)
- [x] 1.1 RED `tests/unit/i18n-resolution.test.ts`: resolution order `?lang=` → `localStorage['rrd.locale']` → `navigator.languages` → `'es'`; `?lang=zz` ignored (spec bilingual requirement context)
- [x] 1.2 GREEN `lib/i18n/resolve.ts`
- [x] 1.3 RED `tests/unit/key-parity.test.ts`: `Object.keys(es)` === `Object.keys(en)`, diff printed both ways, every value is a string (spec "Centralized strings source")
- [x] 1.4 GREEN `lib/i18n/messages/{es,en}.json` seeded with slice 1a/1b/2 namespaces (upload, errors, result, evidence, theme)
- [x] 1.5 GREEN `lib/i18n/i18n.svelte.ts` — `I18n` rune class; missing-key fallback active→`es`→raw key, never `''`, `console.warn` only in `import.meta.env.DEV` (DD5)
- [x] 1.6 GREEN `lib/i18n/enum-map.ts` — classification/action/severity/signal-code → message-key mapping, `description` fallback for unknown signal codes — **NOTE**: this apply batch added `tests/unit/enum-map.test.ts` (not explicitly named by this task list) to keep the mapping under TDD since it isn't wired into any component yet.

### Phase 2: Language switcher (spec "Switchers are keyboard-operable...", "State change is announced...")
- [x] 2.1 RED `LanguageSwitcher` test: `aria-pressed`, per-language `aria-label`, keyboard-operable
- [x] 2.2 GREEN `lib/components/LanguageSwitcher.svelte`
- [x] 2.3 GREEN wire `LanguageSwitcher` into layout; locale switch re-renders from held state, never re-uploads/re-calls API (locked decision, "Result re-render on locale switch")

### Phase 3: LIMITATION_STATEMENT locale-mismatch fix (frontend-only; out-of-band bug found in slice 1b verify)
- [x] 3.1 GREEN `ResultView.svelte` — stop rendering the server's raw `limitations[]` strings; `apps/api`'s `LIMITATION_STATEMENT` is a hardcoded English constant that would otherwise leak untranslated English text into the Spanish/bilingual UI regardless of locale. The view now always renders its own client-owned disclaimer sentence (identical Spanish copy to `ReconciliationNotice.svelte`), which will move behind `t('legal.disclaimer')` in slice 3b along with every other literal in this component. `apps/api` was not touched (frontend-only fix, per instructions).
- [x] 3.2 GREEN updated `tests/unit/ResultView.test.ts` to assert the client disclaimer always renders and the raw server `limitations[]` text never does, regardless of what the server sends.

#### Slice 3a Review Workload Forecast
| Field | Value |
|---|---|
| Estimated changed lines | 300–400 |
| 400-line budget risk | Medium |
| Note | New subsystem (resolver, rune store, enum-map, seed JSON, switcher) — isolated from the literal-replacement sweep in 3b |

---

## Slice 3b: Literal-Copy Replacement Sweep

### Phase 1: Namespace — upload/errors
- [x] 1.1 RED update `DropZone`/`FilePreview`/`ProcessingStages`/`ErrorPanel`/`ReconciliationNotice` tests asserting `t()`-driven copy replaces hardcoded literals — **NOTE**: also fixed the `LanguageSwitcher` announcement bug (was interpolating the button's "switch to" `aria-label` key instead of a language name) and added `LanguageSwitcher.test.ts` cases proving the correct announcement text in both directions (es→en, en→es); also updated `tests/unit/page.smoke.test.ts` to supply an `I18n` context (it renders `+page.svelte` standalone, without `+layout.svelte`, and now needs the same context every touched component reads)
- [x] 1.2 GREEN replace hardcoded Spanish literals in `DropZone`/`FilePreview`/`ProcessingStages`/`ErrorPanel`/`ReconciliationNotice` with `t()` calls against existing slice 3a keys; added `header.language.nameEs`/`header.language.nameEn` to `es.json`/`en.json` for the `LanguageSwitcher` fix (the only new keys this batch — no new upload/errors/legal keys were needed, slice 3a's seed already covered them)

### Phase 2: Namespace — result/evidence/theme
- [x] 2.1 RED update `ScoreSummary`/`EvidenceList`/`ExtractedDataTable`/`ReconciliationChecklist`/`TechnicalDetail`/`ResultView`/`ThemeSwitcher` tests asserting `t()`-driven copy — **NOTE**: also added `tests/unit/locale-integration.test.ts` (with a test-only `tests/unit/support/LocaleIntegrationHost.svelte` mirroring the real `+layout.svelte`/`+page.svelte` composition) proving a single `LanguageSwitcher` click re-renders `ScoreSummary` + `EvidenceList` + `ExtractedDataTable` together from shared state, not just each component in isolation
- [x] 2.2 GREEN replace remaining literals in `ScoreSummary`/`EvidenceItem`/`EvidenceList`/`ExtractedDataTable`/`ReconciliationChecklist`/`TechnicalDetail`/`ResultView`/`ThemeSwitcher` with `t()` calls against existing slice 3a `result.*`/`evidence.*`/`theme.*` keys and `lib/i18n/enum-map.ts` helpers (`classificationKey`/`actionKey`/`severityKey`); no new keys were needed — the slice 3a seed already covered this namespace

### Phase 3: Verification
- [x] 3.1 GREEN re-run `key-parity.test.ts` — confirm no orphan keys after full sweep (3/3 passing, no keys added this batch)
- [x] 3.2 GREEN added `tests/unit/literal-audit.test.ts` — a grep-based Vitest check that scans every `.svelte` file under `lib/components/` (all 14, both batches) for hardcoded accented-Spanish characters in template markup (script/comment/style blocks excluded), runs as part of the existing `npx vitest run` CI job, and fails future regressions automatically

#### Slice 3b Review Workload Forecast
| Field | Value |
|---|---|
| Estimated changed lines | 250–350 |
| 400-line budget risk | Medium |
| Note | Mechanical but touches ~11 components; splitting into two commits (this phase 1 / phase 2) by namespace keeps the diff reviewable without a second PR |

---

## Slice 4: Accessibility Polish + Playwright e2e

### Phase 1: a11y (DESIGN.md §14, spec "State change is announced and not color-only")
- [ ] 1.1 RED `tests/unit/live-region.test.ts`: `LiveRegion` announces processing/result/error transitions
- [ ] 1.2 GREEN `lib/components/LiveRegion.svelte`
- [ ] 1.3 GREEN focus management in `ResultView.svelte` — move focus to result heading on render

### Phase 2: e2e (design "Playwright slice 4 sketch")
- [ ] 2.1 GREEN finalize `playwright.config.ts`; `tests/e2e/upload-to-result.spec.ts` — route-intercept `**/v1/receipts/analyze`, `setInputFiles` synthetic PNG, assert result heading, `74 / 100`, ≥1 evidence item, masked CBU `/^\*+\d{4}$/`, limitation sentence
- [ ] 2.2 GREEN `tests/e2e/theme-persistence.spec.ts` — set `localStorage['rrd.theme']='dark'`, reload, assert `<html data-theme="dark">` on first paint via `addInitScript` probe (no flash)
- [ ] 2.3 GREEN `tests/e2e/locale-switch.spec.ts` — switch to EN, assert heading text changed with no second network request
- [ ] 2.4 GREEN opt-in real-API spec behind `RUN_REAL_API` env flag; excluded from CI by default (design Open Questions: recommended not to run in CI)
- [ ] 2.5 GREEN `.github/workflows/ci.yml` — add Playwright e2e job (excludes the opt-in real-API spec)

### Phase 3: Final audit
- [ ] 3.1 Manual keyboard-only pass through the full upload→result flow, recorded in the PR description (DESIGN.md §14 checklist)
- [ ] 3.2 Manual confirmation no status is communicated by color alone (`ScoreSummary`, `ThemeSwitcher`, `LanguageSwitcher`)

#### Slice 4 Review Workload Forecast
| Field | Value |
|---|---|
| Estimated changed lines | 300–380 |
| 400-line budget risk | Medium |
| Note | Live region + focus mgmt + 3 Playwright specs + CI job; no split needed |

## Key Learnings

1. Slice 3's design-flagged open question (`size:exception` vs. sub-split) is resolved as a namespace/infra sub-split into 3a/3b, both landing under the 400-line budget independently, because `auto-chain`/`stacked-to-main` already provides an approval-free chained-PR path that a `size:exception` would duplicate.
2. Slice 1a cannot be sub-split further because a partial SvelteKit scaffold has no independently mergeable state, so its High risk is accepted as a single PR per the proposal's pre-agreed slice boundary.
3. Every RED task in slices 1a/1b/2/3a/4 traces to an exact spec scenario or design.md decision (DD1–DD7) rather than a generic "add tests" task, satisfying the TDD sequencing requirement given no test runner exists before slice 1a's scaffold phase.
4. The literal-copy sweep in 3b is ordered by namespace (upload/errors, then result/evidence/theme) matching design.md's own fallback suggestion, turned into two commits inside one PR rather than two separate PRs since both fit the review budget individually.
