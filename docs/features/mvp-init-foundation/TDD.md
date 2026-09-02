# TDD: MVP1 Foundation — Visual Architecture, Switcher UX, Rate Limiting

> OpenSpec is the source of truth for this change. This file is an `AGENTS.md`-required mirror for
> discoverability; it summarizes and links rather than duplicates. See
> `openspec/changes/mvp-init-foundation/design.md` § Testing Strategy for full content.

## Scope note

This change is documentation-only: no runtime code, no `apps/api`/`apps/web`. Strict TDD's
red-green-refactor cycle does not apply — there is no test runner in this repository yet. Acceptance
here is documentation-review: every GWT scenario below is checked by reading the produced artifact,
not by executing a test suite.

## Acceptance criteria (documentation-review, executed now)

| Layer | What to check | How it was verified in this change |
| --- | --- | --- |
| Docs | Every `.drawio` parses as valid XML | Checked via `xml.etree.ElementTree.parse()` on all 6 files during apply; all passed |
| Docs | Every FR-001–FR-012 / NFR-001–006 maps to at least one GWT scenario | Traced across the 6 capability specs in `openspec/changes/mvp-init-foundation/specs/*/spec.md`; see Phase 6 verification in `tasks.md` |
| Docs | No MVP1 invariant violated in new prose | Checked against `AGENTS.md` invariants (no absolute verdicts, no persistence, no API keys) during Phase 6 |
| Docs | Out-of-scope items absent from edited files | Checked that repo creation, CI/CD, and app scaffolding are not introduced |

## Deferred test strategy (handed to future implementation changes)

The following rows are the acceptance contract for the change(s) that actually ship code against this
change's specs and design. They do not execute now.

| Layer | What to test | Approach | Spec scenario reference |
| --- | --- | --- | --- |
| Unit | Token bucket refill, burst, exhaustion, `Retry-After` value, LRU eviction | Pure tests on `bucket.py` with an injected clock | `api-rate-limiting` spec: "Default limit enforced", "Analysis endpoint stricter limit", "Restart resets counters" |
| Unit | Locale key parity `es.json` ↔ `en.json`; fallback chain | Snapshot/set-difference test | `ui-localization-and-theming` spec: "Centralized strings source" |
| Contract | `429` body matches the `problem+json` envelope and carries CORS headers | Contract test against the OpenAPI example | `api-rate-limiting` spec: "Analysis endpoint stricter limit"; `public-api-contract` spec: "Documented error shape" |
| E2E | Theme persists across reload; `system` follows OS change; locale re-renders without re-upload | Browser test | `ui-localization-and-theming` spec: "Theme persists after reload", "Language persists after reload", "Manual theme toggle" |
| Integration | Multi-instance deployment is documented as not rate-limit-safe | Documentation assertion only in this change; runtime test belongs to the implementation change | `api-rate-limiting` spec: "Multi-instance deployment not rate-limit-safe" |

## False-positive / false-negative risks (documentation scope)

Not applicable to this change — there is no scoring or detection logic here. Scoring-related
false-positive/false-negative risk analysis belongs to the `receipt-analysis` capability's future
implementation TDD.
