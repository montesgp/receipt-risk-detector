# Design: MVP1 Foundation — Visual Architecture, Switcher UX, Rate Limiting

## Technical Approach

This change ships documentation and diagram sources only; no runtime code. It produces three
deliverables that later implementation changes consume as contracts:

1. **Diagram sources** — six `.drawio` files under `docs/diagrams/`, exported to SVG and embedded in
   `docs/ARCHITECTURE.md` next to (not replacing) the existing Mermaid views (proposal D3).
2. **Switcher UX** — new `docs/DESIGN.md` sections specifying theme and language interaction,
   placement, persistence and fallback, implementing `ui-localization-and-theming` (D1).
3. **Rate-limit mechanism** — the concrete D2 design that `api-rate-limiting` and a later
   implementation change build against.

Every statement below respects `AGENTS.md`: modular monolith, one-way dependency
`Adapters → Application → Domain`, analyzer ports/adapters, and no domain/application import of
FastAPI, PaddleOCR, ExifTool or OpenCV.

## Diagram Inventory

| File (all under `docs/diagrams/`) | View | Embedded in |
|---|---|---|
| `system-context.drawio` | Actors, system boundary, MVP1 constraints | ARCHITECTURE.md §2 |
| `container-view.drawio` | Layers, ports, adapters, composition root | ARCHITECTURE.md §3 |
| `processing-sequence.drawio` | UML sequence for `POST /v1/receipts/analyze` | ARCHITECTURE.md §4 |
| `deployment-railway.drawio` | Railway `dev`→staging and `main`→production | ARCHITECTURE.md §12 |
| `uml-use-case.drawio` | Actors × use cases, `<<include>>` / `<<extend>>` | ARCHITECTURE.md (new §2.1) |
| `uml-activity-receipt-analysis.drawio` | Activity with partitions, fork/join, decisions | ARCHITECTURE.md (new §4.1) |

Exports go to `docs/diagrams/export/<name>.svg` and are referenced with relative Markdown image
links. `docs/diagrams/` did not previously exist, so there is no collision. The `.drawio` source is
plain uncompressed `mxGraphModel` XML so diffs stay reviewable.

## Architecture Decisions

### DD1 — Commit uncompressed `.drawio` XML plus exported SVG

**Choice**: raw XML source in `docs/diagrams/`, generated SVG in `docs/diagrams/export/`, Mermaid kept.
**Alternatives**: Mermaid only (no UML activity partitions or use-case notation); PNG export
(unreviewable, not scalable); compressed `.drawio` (opaque diffs).
**Rationale**: source-editable, diff-reviewable and renderable on GitHub without a plugin.

### DD2 — UML activity with partitions supersedes the PRD §7 flowchart

**Choice**: partitions map exactly to the architecture layers; parallel analyzers use a real
fork/join; INCONCLUSIVE and every `4xx`/`429` path are explicit decision outcomes.
**Alternatives**: keep the PRD flowchart (not UML, hides concurrency and failure paths); state machine
(wrong abstraction for a request-scoped flow).
**Rationale**: the diagram becomes a testable behavioral contract and doubles as the visual index of
the error table in `ARCHITECTURE.md` §9.

### DD3 — Theme: tri-state preference, `localStorage` with `prefers-color-scheme` fallback

**Choice**: stored value `rrd.theme ∈ {system, light, dark}`, default `system`; applied by setting
`data-theme` and `color-scheme` on `<html>`.
**Alternatives**: cookie + SSR (needs server state, contradicts the static-deployable web service);
binary light/dark toggle (no way back to the OS preference); CSS-only `@media` (no user override).
**Rationale**: `data-theme='dark'` already drives the existing token block in `DESIGN.md` §6.3, so no
token restructuring is required.

### DD4 — Language: client-resolved locale, no localized routes

**Choice**: `rrd.locale ∈ {es, en}`, resolution order `?lang=` → `localStorage` → `navigator.languages`
→ `es`; `<html lang>` updated on change.
**Alternatives**: `/es/…` `/en/…` route prefixes (duplicates routes for a single-page tool);
`Accept-Language` server negotiation (introduces browser coupling the API forbids per D4).
**Rationale**: the API response stays locale-free, so the same JSON serves the web UI, n8n and bots.

### DD5 — Rate limiting as ASGI middleware, not a route dependency

**Choice**: pure ASGI middleware registered in the composition root, running before body parsing.
**Alternatives**: FastAPI `Depends` (runs after multipart streaming starts, so a limited client still
uploads 10 MB; needs per-route repetition); reverse-proxy/Redis limiting (Redis contradicts the
no-persistence invariant; proxy config is not portable across the two Railway environments).
**Rationale**: rejects abusive traffic at the cheapest possible point and applies uniformly.

### DD6 — Trust `X-Forwarded-For` only behind an explicit flag

**Choice**: key on the socket peer address unless `RATE_LIMIT_TRUST_FORWARDED_FOR=true`, in which case
use the leftmost `X-Forwarded-For` entry.
**Alternatives**: always trust the header (any client can spoof its identity and evade the limit);
never trust it (on Railway every request keys to the edge IP, so one abuser limits all users).
**Rationale**: correct behind the Railway edge, safe by default in local and direct-exposure runs.

## Theme Switcher UX (new `docs/DESIGN.md` §12)

| Aspect | Decision |
|---|---|
| Placement | Header right cluster, immediately right of the language switcher, left of API docs / GitHub links. Not in the main workspace — it must never compete with the upload action (`DESIGN.md` §2.1). |
| Control | Tri-state segmented control (System · Light · Dark) at ≥768 px; a cycling icon button with a visible current-state label below 768 px. Touch target ≥ 44 × 44 px. |
| Default | `system` — first paint follows `prefers-color-scheme`. |
| Persistence | `localStorage['rrd.theme']`. Explicit choices persist; `system` re-subscribes to the OS preference and updates live via a `matchMedia` change listener. |
| First paint | A small blocking inline script in `app.html` sets `data-theme` before body render. Without it the light tokens flash before a dark preference applies. |
| Transition | Adding `data-theme` toggles a 160 ms transition (inside the 120–220 ms range in §9) on `background-color`, `color` and `border-color` only, applied through a temporary `theme-transition` class removed on `transitionend`. Never transition `box-shadow` or layout properties. |
| Reduced motion | Under `prefers-reduced-motion: reduce` the class is not applied; the swap is instant. |
| Accessibility | Native `<button>`/radio semantics with `aria-pressed` or `aria-checked`; focus ring uses `--color-focus`; the change is announced through the existing ARIA live region. |
| Constraint | Risk colors must keep WCAG AA contrast in both themes (§6.3). Green still means low artifact risk, never "authentic". |

## Language Switcher UX (new `docs/DESIGN.md` §13)

| Aspect | Decision |
|---|---|
| Placement | Header right cluster, left of the theme switcher. Two-option control labelled `ES` / `EN`, each with an `aria-label` in its own language. |
| Persistence | `localStorage['rrd.locale']`; `?lang=` overrides for one visit and is then persisted, which makes bilingual links shareable. |
| Message store | `apps/web/src/lib/i18n/messages/{es,en}.json`, flat dot-namespaced keys: `common.*`, `header.*`, `upload.*`, `processing.*`, `result.*`, `evidence.*`, `errors.*`, `legal.*`, `a11y.*`. |
| Source of truth | `es.json` defines the key set (PRD is Spanish-first). A unit test asserts exact key parity between locales and fails CI on drift. |
| Fallback | Missing key → Spanish value → the raw key in development builds. Never render an empty string. |
| Server enums | `classification`, `recommended_action`, `severity` and `signals[].code` are mapped client-side to `result.*` / `evidence.signal.<CODE>` keys. An unknown code falls back to the server `description` field. The API therefore stays locale-free. |
| Switching cost | Changing locale re-renders the current `FraudAssessment` from client state. It never re-uploads the image or re-calls the API. |
| Copy rule | Both locales must respect `DESIGN.md` §5: no `real`, `fake`, `authentic` or `verified` outcome, and the reconciliation limitation is present in idle and result states. |
| Number/date format | `Intl.NumberFormat` / `Intl.DateTimeFormat` with the active locale; the amount `currency` stays the server-provided code (`ARS`), never re-derived client-side. |

## Rate-Limiting Design (`api-rate-limiting`, D2)

**Placement**: `apps/api/src/receipt_risk/adapters/api/middleware/rate_limit.py`, wired in
`bootstrap/`. The pure algorithm lives in `adapters/api/rate_limit/bucket.py` with no framework
import, so it is unit-testable without ASGI. Domain and application layers are untouched.

**Ordering**: CORS middleware must wrap the rate limiter so a `429` still carries
`Access-Control-Allow-Origin` and the browser can read the error. `OPTIONS` preflights and
`/health`, `/ready`, `/version` are exempt.

**Algorithm**: per-key token bucket with lazy refill on a monotonic clock — no background task.
Two independent buckets are evaluated; the analysis route must satisfy both.

| Bucket | Capacity (burst) | Refill | Applies to |
|---|---|---|---|
| `default` | 30 | 0.5 tokens/s (30/min) | every non-exempt route |
| `analyze` | 10 | 0.1667 tokens/s (10/min) | `POST /v1/receipts/analyze` |

**Memory bound**: entries are stored in an LRU map capped at `RATE_LIMIT_MAX_TRACKED_KEYS`
(default 10 000) and swept lazily when idle longer than two refill windows. Without the cap, IP
rotation turns the limiter itself into a memory-exhaustion vector.

**Concurrency**: a single `asyncio.Lock` guards the map. Correct for one uvicorn worker on one event
loop; explicitly incorrect for multiple workers.

**Response contract** (matches `API.md` §5):

```json
{
  "type": "https://project.example/problems/rate-limited",
  "title": "Too many requests",
  "status": 429,
  "detail": "Rate limit exceeded for this client. Retry after the indicated interval.",
  "instance": "/v1/receipts/analyze",
  "request_id": "req_01...",
  "code": "RATE_LIMITED"
}
```

Headers: `Retry-After` (integer seconds, ceiling of the time to one token), plus `RateLimit-Limit`,
`RateLimit-Remaining` and `RateLimit-Reset`. No analysis runs, no temp file is created, and the
client IP is never logged unmasked.

**Configuration**: `RATE_LIMIT_ENABLED`, `RATE_LIMIT_DEFAULT_PER_MINUTE`,
`RATE_LIMIT_ANALYZE_PER_MINUTE`, `RATE_LIMIT_BURST_MULTIPLIER`, `RATE_LIMIT_TRUST_FORWARDED_FOR`,
`RATE_LIMIT_MAX_TRACKED_KEYS`, `RATE_LIMIT_EXEMPT_PATHS`.

**Accepted MVP1 limitation (must be documented in `API.md` and `ARCHITECTURE.md` §11)**: state lives
in process memory. It resets on every restart and redeploy, and it is not shared across instances, so
horizontal scaling multiplies the effective limit by the instance count. This is abuse damping, not a
security control against distributed abuse. Shared-store limiting is deferred to the authentication
phase.

## File Changes

| File | Action | Description |
|---|---|---|
| `docs/diagrams/system-context.drawio` | Create | System context source |
| `docs/diagrams/container-view.drawio` | Create | Layered container/component source |
| `docs/diagrams/processing-sequence.drawio` | Create | UML sequence source |
| `docs/diagrams/deployment-railway.drawio` | Create | Two-environment Railway deployment source |
| `docs/diagrams/uml-use-case.drawio` | Create | UML use-case source |
| `docs/diagrams/uml-activity-receipt-analysis.drawio` | Create | UML activity source |
| `docs/diagrams/export/*.svg` | Create (apply) | Exported SVGs referenced from ARCHITECTURE.md |
| `docs/ARCHITECTURE.md` | Modify | Embed SVGs; add §2.1 and §4.1; annotate §11 rate-limit scope and §12 Railway as preference |
| `docs/DESIGN.md` | Modify | Add §12 theme switcher and §13 language switcher; extend §3 header IA and §11 checklist |
| `docs/API.md` | Modify | Document `429` headers and the per-instance limitation |
| `docs/PRD.md` | Modify | FR-012 expansion (D1); NFR-003 concrete mechanism (D2) |
| `CONTRIBUTING.md` | Modify | Gitflow policy (D5) and issue-granularity convention (D6) |
| `docs/features/mvp-init-foundation/{SDD,TDD,RDD}.md` | Create | AGENTS.md mirrors of this design (D7) |

## Testing Strategy

| Layer | What to test | Approach |
|---|---|---|
| Docs | Every `.drawio` parses and every embedded SVG path resolves | Link/XML check in the apply phase |
| Unit (future change) | Token bucket refill, burst, exhaustion, `Retry-After` value, LRU eviction | Pure tests on `bucket.py` with an injected clock |
| Unit (future change) | Locale key parity `es.json` ↔ `en.json`; fallback chain | Snapshot/set-difference test |
| Contract (future change) | `429` body matches the `problem+json` envelope and carries CORS headers | Contract test against the OpenAPI example |
| E2E (future change) | Theme persists across reload; `system` follows OS change; locale re-renders without re-upload | Browser test |

This change itself is documentation-only, so only the Docs row executes now. The remaining rows are
the acceptance contract handed to the implementation changes.

## Threat Matrix

| Boundary | Applicability | Reason |
|---|---|---|
| Documentation-like paths | N/A | Only Markdown, SVG and `.drawio` XML are produced; nothing is classified as executable. |
| Git repository selection | N/A | No VCS automation; the repository does not exist yet (D5 defers it to `repo-github-setup`). |
| Commit state | N/A | No commit automation in this change. |
| Push state | N/A | No push automation in this change. |
| PR commands | N/A | No PR automation in this change. |

The rate limiter's request-routing and header-trust boundary (DD5, DD6) carries no runtime surface in
this change. Its adversarial cases — spoofed `X-Forwarded-For`, IP rotation against the LRU cap,
clock non-monotonicity, and preflight bypass — are recorded here and MUST be re-evaluated as an
applicable matrix in the implementation change that ships the middleware.

## Migration / Rollout

No migration. Documentation-only, no runtime impact. Rollback is the proposal's revert plan.

## Open Questions

- [ ] Whether `RATE_LIMIT_TRUST_FORWARDED_FOR` should default to `true` in the Railway environments
      only, which requires the env template that `repo-github-setup` will own.

Diagram delivery is resolved, not open: `.drawio` source files are linked directly from
`ARCHITECTURE.md` as the final approach (no SVG export step), viewed via GitHub's draw.io
viewer/extension, diagrams.net, or the desktop app after download. This keeps the rendered view and
editable source identical by construction.
