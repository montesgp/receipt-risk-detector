# SDD: MVP1 Foundation — Visual Architecture, Switcher UX, Rate Limiting

> OpenSpec is the source of truth for this change. This file is an `AGENTS.md`-required mirror for
> discoverability; it summarizes and links rather than duplicates. Do not edit requirement text here —
> edit `openspec/changes/mvp-init-foundation/` instead. See
> `openspec/changes/mvp-init-foundation/{proposal.md,design.md}` for full content.

## Summary

This change is documentation and diagram sources only — no application code, no `apps/api`/`apps/web`
scaffolding. It converts `docs/PRD.md` FR-001–FR-012 / NFR-001–006 into OpenSpec GWT requirements and
closes three concrete gaps: visual architecture (diagrams), switcher UX (theme + language), and a
concrete rate-limiting mechanism.

## Capability specs (source of truth)

| Capability | Spec | Covers |
| --- | --- | --- |
| `receipt-analysis` | `openspec/changes/mvp-init-foundation/specs/receipt-analysis/spec.md` | FR-001–FR-008 |
| `public-api-contract` | `openspec/changes/mvp-init-foundation/specs/public-api-contract/spec.md` | FR-009, FR-010, NFR-002 |
| `api-rate-limiting` | `openspec/changes/mvp-init-foundation/specs/api-rate-limiting/spec.md` | NFR-003 |
| `data-retention` | `openspec/changes/mvp-init-foundation/specs/data-retention/spec.md` | FR-011 |
| `ui-localization-and-theming` | `openspec/changes/mvp-init-foundation/specs/ui-localization-and-theming/spec.md` | FR-012 (expanded, D1) |
| `architecture-documentation` | `openspec/changes/mvp-init-foundation/specs/architecture-documentation/spec.md` | Diagrams, DESIGN.md as canonical visual reference |

## Design decisions (see `design.md` for full rationale and alternatives)

| # | Decision | Where documented |
| --- | --- | --- |
| DD1 | Commit uncompressed `.drawio` XML plus exported SVG, Mermaid retained | `docs/ARCHITECTURE.md` §2–§4, §12 |
| DD2 | UML activity diagram with partitions supersedes the PRD §7 flowchart | `docs/ARCHITECTURE.md` §4.1 |
| DD3 | Theme: tri-state (`system`/`light`/`dark`), `localStorage`, `prefers-color-scheme` fallback | `docs/DESIGN.md` §12 |
| DD4 | Language: client-resolved locale, no localized routes | `docs/DESIGN.md` §13 |
| DD5 | Rate limiting as ASGI middleware, not a route dependency | `docs/API.md` §5b, `docs/adr/0003-rate-limit-token-bucket.md` |
| DD6 | Trust `X-Forwarded-For` only behind an explicit flag | `docs/adr/0003-rate-limit-token-bucket.md` |

Proposal-level decisions D1–D7 (FR-012 expansion, rate-limit mechanism, draw.io delivery, API
independence, gitflow, issue granularity, artifact reconciliation) are recorded in
`openspec/changes/mvp-init-foundation/proposal.md` and, where irreversible or cross-cutting,
in `docs/adr/000{1,2,3}-*.md`.

## Architecture constraints respected

Per `AGENTS.md`: modular monolith, one-way dependency `Adapters → Application → Domain`, analyzer
ports/adapters, and no domain/application import of FastAPI, PaddleOCR, ExifTool or OpenCV. This
change adds no code, so these constraints apply to the *future* implementation change that ships the
rate-limit middleware and switcher components, not to this change itself.

## File changes

See `openspec/changes/mvp-init-foundation/design.md` § File Changes for the authoritative list
(diagrams, `docs/ARCHITECTURE.md`, `docs/DESIGN.md`, `docs/API.md`, `docs/PRD.md`,
`CONTRIBUTING.md`, ADRs, and this mirror set).

## Diagram delivery approach

Diagrams are delivered as direct links to `docs/diagrams/*.drawio` source files rather than exported
SVGs (design.md's "Diagram Inventory" and task 1.1). This is the intended final approach: it keeps the
rendered view and the editable source identical by construction and avoids export drift. `docs/ARCHITECTURE.md`
links directly to the `.drawio` sources, viewed via GitHub's draw.io viewer/extension, diagrams.net, or
the desktop app after download.
