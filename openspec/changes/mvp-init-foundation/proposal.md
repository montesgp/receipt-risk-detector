# Proposal: MVP1 Foundation — Formal Specs, Visual Architecture, i18n/Theme UX

## Intent

MVP1 exists only as prose (`docs/PRD.md` FR-001–FR-012, NFR-001–006). There are no machine-checkable specs, no editable architecture source, no UML, and no defined rate-limit mechanism. This change converts the PRD into OpenSpec Given/When/Then requirements and closes three concrete documentation gaps so implementation changes can start from a verifiable contract instead of narrative.

## Decisions this proposal makes (traceable, not silent)

| # | Decision | Status |
|---|----------|--------|
| D1 | **FR-012 expanded**: MVP1 ships a working light/dark theme switcher AND full bilingual ES/EN copy — not "foundation only". | **User-approved promotion.** Satisfies the ROADMAP.md scope-control rule as an explicit approved exception, not scope creep. |
| D2 | **Rate limiting made concrete**: in-process per-IP token bucket as FastAPI middleware (default 30 req/min; 10 req/min on analysis endpoint), `429` + problem-details + `Retry-After`, env-configurable. Reverse-proxy limiting stays optional deployment hardening. | New. Chosen over Redis/gateway because MVP1 forbids persistence and runs as a single modular monolith container. |
| D3 | **draw.io delivery**: commit raw `.drawio` under `docs/diagrams/` AND embed exported `.svg` in `docs/ARCHITECTURE.md`. Mermaid is retained. | New. Source-editable + doc-embedded, reviewable in diff. |
| D4 | **API independence reaffirmed**: no auth/API keys in MVP1 (PRD §5 non-goal holds). Independence = CORS allowlist + versioned JSON contract + D2 rate limiting + no browser-session coupling. Server-side third-party consumers (n8n, bots, backends) are an intended, supported pattern. | Reaffirmation. |
| D5 | **Gitflow policy documented**: two branches — `dev` → Railway staging, `main` → Railway production. Documented here; repo creation deferred. | New (docs only). |
| D6 | **Issue-granularity convention**: one GitHub issue per PRD requirement group, generated from these specs by the later change. | Convention only. |
| D7 | **Artifact reconciliation**: OpenSpec is the source of truth; `docs/features/mvp-init-foundation/{SDD,TDD,RDD}.md` are mirrors per AGENTS.md, written in `sdd-design`/`sdd-apply`. | Reconciles both conventions. |

## Scope

### In Scope
- OpenSpec delta specs translating FR-001–FR-012 + NFR-001–006 into GWT scenarios.
- `docs/diagrams/*.drawio` + exported SVGs for the 4 existing architecture views (D3).
- UML use-case diagram and UML activity/swimlane diagram for `upload receipt → risk assessment`.
- `docs/DESIGN.md` evolved into the canonical visual reference: theme-switcher UX (placement, persistence, system-preference default) and language-switcher UX.
- Rate-limit mechanism specification (D2) and gitflow policy doc (D5).

### Out of Scope (belongs to future change `repo-github-setup`)
- Creating the GitHub repository, branch protection, gitflow enforcement.
- GitHub Wiki content and GitHub Issues creation.
- CI/CD pipeline configuration and Railway environment provisioning.
- Python/uv/`pyproject.toml` scaffolding and any application code.

## Capabilities

### New Capabilities
- `receipt-analysis`: upload → preprocessing → OCR → signals → explainable risk score (FR-001–FR-008).
- `public-api-contract`: versioned JSON contract, CORS allowlist, no browser state, problem-details errors (FR-009, FR-010, NFR-002).
- `api-rate-limiting`: D2 mechanism, limits, headers, `429` behavior (NFR-003).
- `data-retention`: no persistence beyond request lifecycle; log minimization (FR-011).
- `ui-localization-and-theming`: bilingual ES/EN copy + theme switcher and persistence (FR-012, expanded per D1).
- `architecture-documentation`: draw.io sources, exported SVGs, UML diagrams, DESIGN.md as canonical visual reference.

### Modified Capabilities
- None. `openspec/specs/` is empty; PRD prose is translated, not amended in place. FR-012's expansion is captured in the new `ui-localization-and-theming` spec and back-annotated into `docs/PRD.md`.

## Approach

1. Create `openspec/specs/` and the change folder; translate PRD prose to GWT requirement-by-requirement, preserving MVP1 invariants (no absolute authenticity verdicts, no storage).
2. Author draw.io sources from the existing Mermaid views, export SVG, embed in ARCHITECTURE.md.
3. Author the two UML diagrams (the existing PRD §7 flowchart is not UML and is superseded for this flow).
4. Extend DESIGN.md with switcher UX sections on top of the existing token system.
5. Specify D2 rate limiting and annotate NFR-003; document D5 gitflow.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `openspec/specs/`, `openspec/changes/mvp-init-foundation/` | New | Formal specs and change artifacts |
| `docs/diagrams/` | New | `.drawio` sources + exported `.svg` |
| `docs/ARCHITECTURE.md` | Modified | Embed SVGs; annotate Railway target vs §12 hosting-agnosticism |
| `docs/DESIGN.md` | Modified | Theme + language switcher UX sections |
| `docs/PRD.md` | Modified | FR-012 expansion (D1); NFR-003 concrete mechanism (D2) |
| `docs/features/mvp-init-foundation/` | New | AGENTS.md SDD/TDD/RDD mirrors |
| `CONTRIBUTING.md` | Modified | Gitflow policy (D5), issue-granularity convention (D6) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| D1 doubles UI copy work and delays MVP1 | Med | Copy is centralized; both locales specified once, no component restructuring |
| Documentation-heavy change exceeds the 400-line review budget | High | `sdd-tasks` must forecast and recommend chained PR slices (specs / diagrams / design+docs) |
| In-process token bucket resets on restart and is per-instance | Med | Documented as an MVP1 limitation; multi-instance limiting deferred with the auth phase |
| Spec translation drifts from PRD wording | Low | Every requirement cites its FR/NFR ID |
| Railway commitment narrows ARCHITECTURE.md §12 | Low | Annotate §12 as deployment preference, not architecture dependency |

## Rollback Plan

Documentation-only change with no runtime impact. Revert by deleting `openspec/changes/mvp-init-foundation/`, `openspec/specs/`, `docs/diagrams/`, and `docs/features/mvp-init-foundation/`, and restoring `docs/{PRD,ARCHITECTURE,DESIGN}.md` and `CONTRIBUTING.md` from their pre-change versions. No data migration, no deploy, no consumer breakage.

## Dependencies

- draw.io / diagrams.net for `.drawio` authoring and SVG export.
- No runtime or package dependencies; the repo is still unscaffolded.

## Success Criteria

- [ ] Every FR-001–FR-012 and NFR-001–006 maps to at least one GWT scenario in `openspec/specs/`.
- [ ] Four architecture views exist as `.drawio` sources with SVGs embedded in ARCHITECTURE.md.
- [ ] UML use-case and activity/swimlane diagrams cover the upload → risk assessment flow.
- [ ] DESIGN.md specifies theme-switcher and language-switcher UX including persistence.
- [ ] NFR-003 names a concrete rate-limit algorithm, default limits, and `429` response shape.
- [ ] MVP1 invariants hold: no absolute authenticity verdicts, no persistence, no API keys.
- [ ] Out-of-scope items are recorded as the future `repo-github-setup` change.
