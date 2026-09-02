# ADR 0002: FR-012 scope expansion to full bilingual UI + theme switcher

## Status

Accepted

## Context

`docs/PRD.md` FR-012 originally scoped an "internationalization foundation": Spanish-first UI copy,
centralized so English could be added later without restructuring components. It did not require a
working English locale or a theme switcher for MVP1.

`docs/ROADMAP.md`'s scope-control rule states: "Agents must not implement, scaffold databases for, or
add dependencies for future phases unless an approved issue/ADR explicitly moves that capability into
current scope." Promoting FR-012 to a full bilingual UI and a working theme switcher is exactly this
kind of scope move, so it requires an explicit, traceable decision rather than being folded silently
into a docs-only change.

The user explicitly approved this expansion for MVP1 (proposal decision D1, "User-approved
promotion").

## Decision

Expand FR-012 for MVP1 from "Spanish-first foundation only" to:

1. Full bilingual ES/EN UI copy, centralized in `apps/web/src/lib/i18n/messages/{es,en}.json`, with a
   test enforcing exact key parity between locales.
2. A working light/dark theme switcher built on the existing semantic color token system
   (`docs/DESIGN.md` §6.3), defaulting to `system` preference and persisting explicit user choice.

The expanded requirement is specified in
`openspec/changes/mvp-init-foundation/specs/ui-localization-and-theming/spec.md`. `docs/PRD.md`
FR-012 is back-annotated to mark its original wording as superseded and cross-link the new spec,
rather than duplicating requirement text in two places.

## Consequences

- `docs/DESIGN.md` §12 (Theme Switcher UX) and §13 (Language Switcher UX) become part of the MVP1
  UX contract, not a later-phase addition.
- Component structure for user-facing copy must support locale switching without restructuring
  (already true because copy is centralized), and the `es.json` key set becomes the enforced schema
  for `en.json`.
- Scope risk: "D1 doubles UI copy work and delays MVP1" (proposal Risks, likelihood Med). Mitigation:
  copy is centralized and specified once per locale; no component restructuring is introduced by this
  ADR.
- This ADR is the roadmap scope-control exception basis referenced by
  `openspec/changes/mvp-init-foundation/tasks.md` task 4.2 and the `ui-localization-and-theming` spec.

## References

- `docs/PRD.md` FR-012
- `openspec/changes/mvp-init-foundation/specs/ui-localization-and-theming/spec.md`
- `docs/DESIGN.md` §12–§13
- `docs/ROADMAP.md` (Scope-control rule for agents)
- `openspec/changes/mvp-init-foundation/proposal.md` decision D1
