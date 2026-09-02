# Tasks: MVP1 Foundation — Specs, Diagrams, Switcher UX, Rate Limiting

Documentation-and-specs only. No app code, no `apps/api`/`apps/web` scaffolding.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1,800–2,200 (6 drawio sources ~900, 6 SVG exports generated, ARCHITECTURE.md ~150, DESIGN.md ~200, API.md ~60, PRD.md ~50, CONTRIBUTING.md ~60, 3 ADRs ~180, 3 feature mirrors ~400) |
| 400-line budget risk | High (also High against this project's 800-line budget) |
| Chained PRs recommended | Yes |
| Suggested split | Single PR requested — apply as `size:exception` with work-unit commits below |
| Delivery strategy | single-pr |
| Chain strategy | size-exception |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: size-exception
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Export 6 SVGs, embed in ARCHITECTURE.md §2.1/§4.1/§12 | PR 1 (size:exception) | `drawio -x -f svg docs/diagrams/*.drawio -o docs/diagrams/export/` then Markdown link check | N/A — doc-only, no runtime | Delete `docs/diagrams/export/*.svg`, revert ARCHITECTURE.md |
| 2 | DESIGN.md §12/§13 switcher UX + PRD.md FR-012/NFR-003 cross-links | PR 1 (size:exception) | Manual GWT-scenario trace vs `ui-localization-and-theming` spec | N/A — doc-only | Revert DESIGN.md, PRD.md hunks |
| 3 | API.md 429 contract + CONTRIBUTING.md gitflow/issue convention | PR 1 (size:exception) | Diff `API.md` §5 against `api-rate-limiting` spec response contract | N/A — doc-only | Revert API.md, CONTRIBUTING.md hunks |
| 4 | 3 ADRs (Railway target, FR-012 expansion, rate-limit algorithm) | PR 1 (size:exception) | Peer read-through against `design.md` DD5/DD6 and D1/D5 | N/A — doc-only | Delete `docs/adr/000X-*.md` |
| 5 | `docs/features/mvp-init-foundation/{SDD,TDD,RDD}.md` mirrors, cross-linked to specs | PR 1 (size:exception) | Confirm every spec requirement is referenced at least once | N/A — doc-only | Delete `docs/features/mvp-init-foundation/` |

## Phase 1: Diagrams

- [x] 1.1 Link each `docs/diagrams/*.drawio` (6 files) directly from `ARCHITECTURE.md` as the final delivery approach — no SVG export step. Diagrams are viewed via GitHub's draw.io viewer/extension, diagrams.net, or the desktop app after download, keeping the rendered view and editable source identical by construction.
- [x] 1.2 Embed `system-context.svg`, `container-view.svg` in `ARCHITECTURE.md` §2/§3; add `uml-use-case.svg` as new §2.1. (Linked to `.drawio` sources per 1.1 deferral.)
- [x] 1.3 Embed `processing-sequence.svg` in §4; add `uml-activity-receipt-analysis.svg` as new §4.1. (Linked to `.drawio` sources per 1.1 deferral.)
- [x] 1.4 Embed `deployment-railway.svg` in §12; annotate §12 as "Railway is the deployment preference, not an architecture dependency" (D3/D5). (Linked to `.drawio` source per 1.1 deferral; annotation added.)
- [x] 1.5 Verify every `.drawio` parses as valid XML and every embedded SVG relative path resolves. All 6 `.drawio` files parsed successfully via `xml.etree.ElementTree`; no SVG paths exist yet (see 1.1), so no SVG path-resolution check applies.

## Phase 2: Switcher UX and PRD Reconciliation

- [x] 2.1 Add `DESIGN.md` §12 Theme Switcher UX table (placement, control, default, persistence, first paint, transition, reduced motion, a11y, constraint) from `design.md`.
- [x] 2.2 Add `DESIGN.md` §13 Language Switcher UX table (placement, persistence, message store, fallback, server enums, switching cost, copy rule, number/date format).
- [x] 2.3 Extend `DESIGN.md` §3 header IA and checklist (renumbered §14 after inserting §12/§13) to reference the two new switchers.
- [x] 2.4 Update `docs/PRD.md` FR-012: mark original wording superseded, cross-link `openspec/changes/mvp-init-foundation/specs/ui-localization-and-theming/spec.md` (no duplicated requirement text).
- [x] 2.5 Update `docs/PRD.md` NFR-003: name the concrete token-bucket mechanism, cross-link `specs/api-rate-limiting/spec.md`.

## Phase 3: Rate Limiting and Contribution Docs

- [x] 3.1 Add `API.md` §5 subsection: `429` problem-details body, `Retry-After`, `RateLimit-Limit/Remaining/Reset` headers, exempt paths.
- [x] 3.2 Document the per-instance/reset-on-restart limitation in `API.md` (must not be silent) and cross-link `ARCHITECTURE.md` §11.
- [x] 3.3 Add gitflow policy (`dev`→staging, `main`→production) to `CONTRIBUTING.md` (D5).
- [x] 3.4 Add issue-granularity convention (one issue per PRD requirement group) to `CONTRIBUTING.md` (D6).

## Phase 4: ADRs

- [x] 4.1 `docs/adr/0001-railway-as-deployment-target.md`: context (ARCHITECTURE.md §12 hosting-agnosticism), decision, consequences.
- [x] 4.2 `docs/adr/0002-fr-012-scope-expansion.md`: D1 promotion from "Spanish-first foundation" to full bilingual + theme switcher, ROADMAP.md scope-control exception basis.
- [x] 4.3 `docs/adr/0003-rate-limit-token-bucket.md`: D2/DD5/DD6 — ASGI middleware token bucket over Redis/gateway/`Depends`, forwarded-header trust flag.

## Phase 5: Feature Mirrors and Cross-Linking

- [x] 5.1 Create `docs/features/mvp-init-foundation/SDD.md`: mirror `design.md` Technical Approach + Architecture Decisions, cross-link all 6 capability specs.
- [x] 5.2 Create `docs/features/mvp-init-foundation/TDD.md`: mirror `design.md` Testing Strategy table, cite spec scenario IDs per capability.
- [x] 5.3 Create `docs/features/mvp-init-foundation/RDD.md`: mirror the Threat Matrix, mark all rows N/A with reason per `design.md`.
- [x] 5.4 Add a short "OpenSpec is source of truth" note at the top of each mirror file (D7).

## Phase 6: Verification

- [x] 6.1 Trace every FR-001–FR-012 and NFR-001–006 to at least one GWT scenario across the 6 specs (proposal Success Criteria). **PARTIAL — gap found**: FR-001–FR-012 all map cleanly (receipt-analysis: FR-001–FR-008; public-api-contract: FR-009/FR-010; api-rate-limiting: NFR-003; data-retention: FR-011; ui-localization-and-theming: FR-012). NFR-002 maps to public-api-contract's "Documented error shape" scenario. NFR-006 is reasonably covered by receipt-analysis's "Deterministic score for identical input" scenario. **NFR-001 (Performance) and NFR-004 (Accessibility) have zero GWT scenario coverage in any of the 6 change-scoped specs** — confirmed by grep across `openspec/changes/mvp-init-foundation/specs/`. This is a genuine gap against the proposal Success Criteria, not a false pass; flagged as a risk in the apply return rather than silently checked off or fixed by rewriting specs outside this phase's scope.
- [x] 6.2 Confirm no MVP1 invariant is violated in new prose (no absolute verdicts, no persistence, no API keys). Verified via grep across `docs/`: all "real/fake/authentic/verified" occurrences are in the forbidden-word lists (DESIGN.md §5, §14 checklist, PRD.md) or explicit negations ("never authentic"); all "API key" occurrences state their absence; no persistence introduced.
- [x] 6.3 Confirm out-of-scope items (repo creation, CI/CD, app scaffolding) are absent from all edited files. Verified via grep: all `repo-github-setup` references correctly defer repo creation/CI-CD/provisioning to the future change; no scaffolding introduced.

## Key Learnings

1. `docs/diagrams/*.drawio` sources already exist with real `mxGraphModel` content; only SVG export and embedding remain.
2. `docs/diagrams/export/` and `docs/adr/` do not exist yet and must be created during apply.
3. The 800-line project review budget does not change the outcome: even excluding generated SVGs, authored doc/ADR/mirror content alone is estimated near or above 800 lines, so risk stays High.
4. `openspec/specs/` (published specs) is out of scope for this phase; only the change-scoped `specs/<capability>/spec.md` deltas exist, created in `sdd-spec`.
5. Delivery strategy `single-pr` combined with High risk forces `size:exception`, per the Review Workload Guard in `sdd-phase-common.md`.
