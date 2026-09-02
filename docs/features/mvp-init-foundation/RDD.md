# RDD: MVP1 Foundation — Visual Architecture, Switcher UX, Rate Limiting

> OpenSpec is the source of truth for this change. This file is an `AGENTS.md`-required mirror for
> discoverability; it summarizes and links rather than duplicates. See
> `openspec/changes/mvp-init-foundation/design.md` § Threat Matrix and § Open Questions for full
> content.

## Purpose

Records open research questions deferred out of this documentation-only change, plus the Threat
Matrix applicability rationale required by the design.

## Threat Matrix (all rows N/A for this change)

| Boundary | Applicability | Reason |
| --- | --- | --- |
| Documentation-like paths | N/A | Only Markdown, SVG and `.drawio` XML are produced; nothing is classified as executable. |
| Git repository selection | N/A | No VCS automation; the repository does not exist yet (D5 defers it to `repo-github-setup`). |
| Commit state | N/A | No commit automation in this change. |
| Push state | N/A | No push automation in this change. |
| PR commands | N/A | No PR automation in this change. |

The rate limiter's request-routing and header-trust boundary (DD5, DD6) carries no runtime surface in
this change. Its adversarial cases — spoofed `X-Forwarded-For`, IP rotation against the LRU cap, clock
non-monotonicity, and preflight bypass — are recorded here and MUST be re-evaluated as an applicable
matrix in the implementation change that ships the middleware.

## Deferred research questions (from `docs/PRD.md` §13 and `design.md` Open Questions)

| # | Question | Status | Owner phase |
| --- | --- | --- | --- |
| 1 | Select PaddleOCR or Tesseract as the initial production OCR adapter, after a documented Argentine-receipt benchmark. | Open | Implementation change for `receipt-analysis` |
| 2 | Select the supported C2PA toolchain and license-compatible integration. | Open | Implementation change for `receipt-analysis` |
| 3 | Define the initial scoring weights and how `INCONCLUSIVE` overrides range classification. | Open | Implementation change for `receipt-analysis` risk engine |
| 4 | Define the reference CPU used for the NFR-001 latency targets (p50 < 4s, p95 < 10s). | Open | Implementation change; must be rebaselined against real hardware and fixtures |
| 5 | Decide whether PDF support belongs in MVP1 (excluded by default). | Open | Product decision, not implicitly implied by this change |
| 6 | Diagram delivery format: `.drawio` source links versus exported SVGs. | Resolved | `docs/ARCHITECTURE.md` links directly to the `.drawio` sources as the final approach (not an interim step), viewed via GitHub's draw.io viewer/extension, diagrams.net, or the desktop app after download. This keeps the rendered view and editable source identical by construction, with no export-drift risk. |
| 7 | Whether `RATE_LIMIT_TRUST_FORWARDED_FOR` should default to `true` in Railway environments only. | Open | Requires the env template that `repo-github-setup` will own |

None of these questions block this documentation-only change's success criteria; they are the
research handoff to the implementation changes that consume these specs.
