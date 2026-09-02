# Proposal: UI Frontend Implementation

Implements GitHub issue [#5](https://github.com/montesgp/receipt-risk-detector/issues/5) (`ui-localization-and-theming`). The issue is still open and needs the `status:approved` label applied when work starts — an orchestrator action, not part of this proposal.

## Intent

`apps/api/` is fully implemented and merged to `main`: `POST /v1/receipts/analyze` returns a complete `FraudAssessment` today. `apps/web/` does not exist at all. The product's entire user-facing value — a person uploading a suspicious Argentine transfer receipt and reading evidence-based risk output — is currently reachable only through curl and `/docs`. Nobody outside the repo can use the product.

Why now: the API contract is frozen and stable, `openspec/specs/ui-localization-and-theming/spec.md` is frozen (8 GWT scenarios), and `docs/DESIGN.md` §12/§13 already specify switcher placement, persistence keys, resolution order, and rejected alternatives. There is no remaining UX ambiguity blocking implementation — only the code is missing.

## Scope

### In Scope
- SvelteKit 5 + TypeScript scaffold under `apps/web/` (Vitest + Playwright wired, custom CSS on the existing DESIGN.md token system, no UI component library).
- The five DESIGN.md §4 workspace states: idle/upload, file-selected preview, processing (ARIA live region), result (score, confidence, evidence, extracted data, checklist, technical detail), error (no raw stack traces).
- A typed API client bound to the **real** `AnalyzeResponse`/`ExtractedFieldModel`/`ProblemDetails` schemas in `apps/api/src/receipt_risk/adapters/api/schemas.py`.
- Theme switcher (tri-state System/Light/Dark, `localStorage['rrd.theme']`, `matchMedia` subscription, blocking first-paint script, reduced-motion handling).
- Bilingual ES/EN i18n layer (`localStorage['rrd.locale']`, `?lang=` override, key-parity test, client-side server-enum → message-key mapping with `description` fallback).
- Accessibility acceptance per DESIGN.md §14 and the frozen spec: keyboard operability, visible `--color-focus` state, `aria-pressed`/`aria-checked`, no color-only status.
- Documented local-dev setup (API base URL config + CORS env var) and a correction to `docs/API.md`'s extracted-data example.

### Out of Scope
- **Web infrastructure**: production web `Dockerfile`, a second Railway service, `railway.json` web block, deploy config. Deferred to a separate later infra change, matching the `repo-github-setup` precedent that kept live provisioning out of business-logic changes.
- Accounts, history/persistence, batch upload, billing, API keys/OAuth (PRD §5 non-goals — explicit, not implied).
- Any change to `apps/api/` behavior. The API stays locale-free; the frontend owns 100% of locale logic.
- Absolute authenticity verdicts. No copy may render `is_real`, `is_fake`, `authentic`, or "verified transfer".

## Capabilities

### New Capabilities
- `receipt-analysis-web-client`: the browser-side upload → analyze → result journey (FR-008): the five workspace states, client-side file validation, error surfacing from `ProblemDetails`, rate-limit (429) handling, and the invariant that no image or result is persisted client-side.

### Modified Capabilities
- None. `ui-localization-and-theming` is frozen and implemented as written; `sdd-spec` should confirm no delta is required rather than author one. `public-api-contract` and `data-retention` are consumed, not changed.

## Approach

Layout per `docs/ARCHITECTURE.md` §6: `apps/web/src/lib/{api,components,features/receipt-analysis,i18n}/`. Presentational components stay dumb; feature containers own state; the API client is the only module that knows about HTTP.

Delivered as **4 sequential chained PRs**, each merged into `dev` before the next starts. Ordering optimizes for *visible product value first*, not textbook build order — the opposite tradeoff from `receipt-analysis-implementation`, where nothing was demoable until the last slice:

1. **Scaffold + upload + real API call + result display** — Spanish-only hardcoded copy, light theme only, no switchers. This is the slice that turns the product from curl-only into something a human can click through locally. It also forces the frontend to bind to the real response schema on day one.
2. **Theme switcher** (DESIGN.md §12) — isolated, no coupling to i18n, immediately visible.
3. **Bilingual i18n layer** (DESIGN.md §13) — largest new surface area; extracting hardcoded Spanish copy into the message store is mechanical once the UI shape is settled by slices 1–2.
4. **Accessibility polish + Playwright e2e** — must be last: it verifies behavior introduced in slices 1–3 and encodes the DESIGN.md §14 checklist as executable acceptance.

Rationale for hardcoding Spanish in slice 1: the alternative (i18n first) delays anything visible by two slices and would force message-key authoring against a UI whose copy is not yet settled, guaranteeing churn in `es.json`/`en.json`. Spanish-first also matches the product default locale, so slice 1 is a genuine usable state, not a placeholder.

### Locked technical decisions (not open questions)

| Decision | Choice | Rationale |
|---|---|---|
| i18n implementation | Hand-rolled: flat dot-namespaced JSON + a Svelte 5 runes store + a `t()` accessor implementing DESIGN.md §13's exact resolution and fallback chain. **Not** `paraglide-js`. | Paraglide's value is per-route tree-shaking and a URL-based locale strategy; this is a single-page tool and DESIGN.md explicitly rejects `/es/`/`/en/` route prefixes. Forcing a non-default strategy adds compiler/build complexity for ~9 namespaces, and the bespoke fallback contract must be hand-authored either way. |
| Local dev API access | Direct cross-origin calls with `RECEIPT_RISK_CORS_ALLOWED_ORIGINS=http://localhost:5173` documented as the required local API env var. **No Vite dev-server proxy.** | Production topology is a separate web service calling the API cross-origin, so dev must exercise the same CORS path the production browser will use; a proxy hides allowlist misconfiguration until deploy and creates a dev-only second code path alongside the configurable API base URL the frontend needs anyway. Matches `docs/ARCHITECTURE.md` §10 ("directly under configured CORS… a thin proxy only when deployment requires it"). |
| API base URL | Single `PUBLIC_API_BASE_URL` env var read via SvelteKit `$env/static/public`, defaulting to `http://localhost:8000`. | One code path for dev and prod; the later infra change only sets a value. |
| `docs/API.md` correction | Slice 1 fixes §3's illustrative extracted-data JSON to the real generic `ExtractedFieldModel` shape (`value`, `masked_value`, `confidence`, `is_checksum_valid`). | The doc currently shows per-field objects with an `amount.currency` field that does not exist on the model. Slice 1 is where the frontend first binds to the contract, so it is where the divergence is proven and must be recorded. The error envelope and rate-limit header sections of `docs/API.md` are accurate and stay as-is. |
| Result re-render on locale switch | Re-render from already-held client state; never re-upload or re-call the API. | DESIGN.md §13; also avoids a second rate-limit consumption. |

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `apps/web/` | New | Entire SvelteKit application, `package.json`, Vite/Vitest/Playwright config |
| `apps/web/src/lib/api/` | New | Typed client + schema types mirroring `schemas.py` |
| `apps/web/src/lib/features/receipt-analysis/` | New | Workspace state machine and containers |
| `apps/web/src/lib/i18n/messages/{es,en}.json` | New | Message store + key-parity test (slice 3) |
| `apps/web/src/app.html` | New | Blocking first-paint theme script (slice 2) |
| `docs/API.md` | Modified | Corrected extracted-data example (slice 1) |
| `README.md` / `docs/` local-dev section | Modified | Frontend dev commands + CORS env var step |
| `.github/workflows/ci.yml` | Modified | Node install, `apps/web` lint/typecheck/test job |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Slice 1 exceeds the 400-line review budget (scaffold + upload + client + full result UI) | High | Pre-agreed sub-split: 1a = scaffold + upload + API call + raw result; 1b = full result presentation (evidence, extracted data, checklist). `sdd-tasks` must forecast this explicitly. |
| Frontend binds to `docs/API.md` instead of the real schema and breaks against the live API | Med | Types generated/derived from `schemas.py`; slice 1 includes an integration test against the running API, plus the doc correction itself. |
| Hardcoded Spanish copy in slices 1–2 leaks past slice 3 | Med | Slice 3 acceptance includes a check that no user-facing literal string remains outside the message store. |
| Hand-rolled i18n misses a DESIGN.md §13 rule (fallback chain, `?lang=` precedence) | Med | Each resolution-order rule gets a unit test; key-parity test is CI-enforced. |
| Theme flash on first paint | Med | Blocking inline script in `app.html` sets `data-theme` before body paint; Playwright check in slice 4. |
| No web infra means the frontend stays unreachable publicly after this change | Accepted | Deliberate: this change ships a locally runnable, functionally complete client. Deployment is a tracked follow-up change. |

## Rollback Plan

Each slice is one PR into `dev` and reverts independently. Slices 2–4 are additive layers over a working slice 1, so reverting any of them leaves a functioning Spanish/light-theme client. Reverting slice 1 removes `apps/web/` entirely and restores the API-only repo state; no API code, deploy config, or persisted data is touched by any slice. The `docs/API.md` correction is a standalone commit that can be kept even if slice 1 is reverted.

## Dependencies

- `apps/api` running locally (or a deployed API URL) with `RECEIPT_RISK_CORS_ALLOWED_ORIGINS` set.
- Node toolchain in CI (none exists today — the workflow currently installs Python only).
- Slices are strictly ordered: each depends on the previous being merged to `dev`.

## Success Criteria

- [ ] Every scenario in `openspec/specs/ui-localization-and-theming/spec.md` has a passing automated test.
- [ ] A user can upload a receipt in a local browser and read a full risk result rendered from the live API response.
- [ ] Theme and locale both survive a page reload; theme defaults to `prefers-color-scheme` when unset.
- [ ] `es.json` and `en.json` have exactly identical key sets, enforced by a CI test.
- [ ] No user-facing string is hardcoded outside the message store after slice 3.
- [ ] Switchers are fully operable by keyboard with visible focus, and state is exposed via `aria-pressed`/`aria-checked` and announced in the ARIA live region.
- [ ] No rendered copy contains `is_real`, `is_fake`, `authentic`, or "verified transfer".
- [ ] `docs/API.md`'s extracted-data example matches `ExtractedFieldModel` exactly.
- [ ] No image bytes or analysis results are written to `localStorage`, `sessionStorage`, IndexedDB, or cookies.

## Key Learnings

1. The frontend must bind to `apps/api/src/receipt_risk/adapters/api/schemas.py`, not to `docs/API.md`'s illustrative example, because the real `ExtractedFieldModel` is generic and has no `currency` field.
2. Slice ordering here optimizes for visible product value first, inverting the dependency-first ordering used by `receipt-analysis-implementation`.
3. A hand-rolled i18n store fits this single-page app better than `paraglide-js`, whose default route-prefixed locale strategy is explicitly rejected by DESIGN.md §13.
4. Local dev uses real cross-origin CORS rather than a Vite proxy so that allowlist misconfiguration fails in development instead of at deploy time.
5. Web deployment infrastructure is deliberately excluded, keeping this change functionally complete but locally scoped, per the `repo-github-setup` precedent.
