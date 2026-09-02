# Proposal: Receipt Analysis Implementation

Implements GitHub issue [#1](https://github.com/montesgp/receipt-risk-detector/issues/1).

## Intent

`openspec/specs/receipt-analysis/spec.md` is frozen and complete, but `apps/api/src/receipt_risk/` is an empty skeleton with a single `/health` route. The product's entire value — evidence-based risk assessment of an Argentine transfer receipt — exists only as documentation. This change makes the specified behavior real. Why now: `apps/api` finally has a working pytest/ruff toolchain, so Strict TDD is mechanically enforceable for the first time.

## Scope

### In Scope
- Ingestion: multipart upload, content-decode validation, dimension/pixel limits, SHA-256 `analysis_id`, guaranteed temp-file cleanup.
- Metadata/provenance: ExifTool subprocess adapter, C2PA inspection via `c2pa-python` (Reader-only).
- OCR behind `OcrPort` + deterministic financial validators (CBU/CVU, CUIT/CUIL, ARS normalization, date bounds, contradictions).
- Risk engine: `ValidationSignal` aggregation, versioned ruleset config, independent confidence, `INCONCLUSIVE` override, `FraudAssessment` assembly, `/v1/receipts/analyze` wiring.
- Synthetic Argentine fixtures under `samples/` plus sidecar manifest (real authoring work, slice 1 — none exist today).
- Infra: Dockerfile stages for OCR models/ExifTool binary and matching CI system-dependency steps.

### Out of Scope
- PDF input, persistence, accounts, batch analysis, the SvelteKit results UI (FR-008).
- Tuned scoring weights and a documented reference-CPU benchmark (PRD §13 stays open; ship reasonable versioned defaults, not fake precision).

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- None. This change implements frozen specs (`receipt-analysis`, boundary touch on `public-api-contract`) without altering requirements. `sdd-spec` should confirm no delta is required rather than author one.

## Approach

Ports-and-adapters per `docs/ARCHITECTURE.md`: pure check-digit and scoring logic in `domain/`, orchestration in `application/`, all tooling in `adapters/` (ruff TID251 already enforces this).

Delivered as **4 sequential chained PRs**, each merged into `dev` before the next starts. Order is dependency- and risk-driven, not arbitrary:

1. **Ingestion** — zero external tool dependencies, so it is TDD-able immediately and unblocks fixture authoring every later slice consumes.
2. **Metadata + C2PA** — one pip dependency plus one system binary; small, isolated failure surface.
3. **OCR + financial validators** — highest risk: heaviest new dependencies, the new Docker model-baking stage, and the only unbenchmarked latency driver (NFR-001). Isolating it keeps its risk out of the other three PRs.
4. **Risk engine + response assembly** — must be last; it consumes signals produced by slices 1–3 and is the only slice that exposes the endpoint publicly.

### Locked technical decisions (not open questions)

| Decision | Choice |
|---|---|
| CBU/CVU check digit | 22 digits, two blocks, mod 10. Block 1 weights `[7,1,3,9,7,1,3]`; block 2 weights `[3,9,7,1,3,9,7,1,3,9,7,1,3]`; DV = `(10 - sum % 10) % 10`. Known-answer fixture: `2850590940090418135201` (DV1=9, DV2=1). |
| CUIT/CUIL check digit | 11 digits, mod 11, weights `[5,4,3,2,7,6,5,4,3,2]`; `11 → 0`, `10 → invalid`. Known-answer fixture: `20-17254359-7`. |
| C2PA | `c2pa-python` (official CAI, Apache-2.0, Reader-only) — no CLI subprocess. |
| OCR | PaddleOCR ONNX variant ships first behind `OcrPort`; Tesseract documented as the fallback/benchmark comparator. Revisitable once real fixtures allow a benchmark. |

### Locked product decisions (confirmed with the product owner)

- **Endpoint exposure**: `/v1/receipts/analyze` stays unexposed (404/501) until slice 4. Slices 1–3 ship dead code paths behind tests only — one credible launch, not incremental partial answers.
- **`INCONCLUSIVE` is not "OCR failed"**: `confidence_score` and `risk_score` stay independent per analyzer, so a failed OCR extraction does not alone force `INCONCLUSIVE` — if metadata/C2PA produced usable signals, `risk_score` is computed from those, with lower `confidence_score` reflecting the reduced evidence coverage. `INCONCLUSIVE` fires only when evidence coverage across *all* analyzers together falls below threshold, not when a single analyzer fails.
- **A failed extraction is itself a signal, not a gap**: when a core field (amount, CBU/CVU, CUIT/CUIL, date) cannot be extracted, the OCR adapter emits an explicit `ValidationSignal` (e.g. `CORE_FIELD_EXTRACTION_FAILED`, category `data_quality`, carrying the failure reason: `low_confidence` / `no_text_detected` / `timeout`) that contributes to `risk_score` — an unreadable receipt is itself suspicious, never a silent no-op.
- **Bounded OCR retry**: before emitting an extraction-failure signal, the `OcrPort` adapter applies one bounded preprocessing retry (deskew, contrast/sharpness normalization) within the NFR-001 latency budget — not an unbounded retry loop, and not a second OCR engine call in the critical path (Tesseract stays a benchmark comparator, per the OCR decision above, not an automatic in-request fallback).
- **A valid AI-generation provenance claim alone can drive `risk_score` to the top classification band** — it is a critical signal on its own, per AGENTS.md's existing invariant, and still never becomes an absolute `is_fake`/`is_real` verdict.
- **Fixture realism**: `samples/` fixtures stay 100% synthetic (fabricated layouts, no real bank templates) for this change — non-negotiable per AGENTS.md's fixture policy. The product owner will separately supply their own personal real receipts (legitimate and deliberately fabricated) for manual, out-of-repo testing once the pipeline is more mature; those never enter `samples/` or any committed fixture, consistent with the "no real receipts in the repository" invariant and the fact that nothing is persisted server-side either way.
- **Adaptive/learning scoring is explicitly deferred to ROADMAP, not this change**: the product owner wants an eventual "judge" mechanism that learns from accumulated test/real-world outcomes to refine scoring. The current versioned, static ruleset config ships as-is for MVP1; this idea is noted here for traceability but must not leak into this change's scope (ROADMAP.md's scope-control rule applies) — revisit only via an explicit future proposal once enough labeled outcomes exist to make "learning" meaningful rather than guesswork.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `apps/api/src/receipt_risk/domain/` | New | Assessment model, signals, check-digit validators, ruleset |
| `apps/api/src/receipt_risk/application/` | New | Ports, analyze use case, orchestration, cleanup |
| `apps/api/src/receipt_risk/adapters/{api,ocr,metadata,provenance}/` | New | Upload handler and tool adapters |
| `apps/api/pyproject.toml` | Modified | New adapter deps + extended ruff banned-api list |
| `apps/api/Dockerfile` | Modified | ExifTool binary, OCR model pre-baking stage |
| `.github/workflows/ci.yml` | Modified | System-dependency install step (none exists today) |
| `samples/` | New | Synthetic fixtures + `manifest.json` |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| OCR accuracy/latency misses NFR-001 | High | `OcrPort` keeps the engine swappable; benchmark once slice-1 fixtures exist |
| Docker image bloat from OCR models | Med | Pin ONNX model version, pre-bake in a dedicated build stage, measure image size |
| Scoring weights are unvalidated guesses | High | Versioned ruleset file, no hardcoded constants; treated as a documented default, not a tuned answer |
| Slice 3 blows the 400-line review budget alone | Med | Sub-split validators from the OCR adapter into two PRs if forecast exceeds budget |
| Synthetic fixtures unrepresentative of real receipts | Med | Manifest records provenance and expected signals; revisit after first real-world sampling |

## Rollback Plan

Each slice is one PR into `dev` and reverts independently. The endpoint stays unexposed until slice 4, so reverting any of slices 1–3 removes only dead code paths. Reverting slice 4 restores the pre-change API surface. Infra reverts are isolated to `Dockerfile` and `ci.yml` commits.

## Dependencies

- `c2pa-python`, PaddleOCR (ONNX) + `onnxruntime`, `opencv-python-headless`, `Pillow`; system `exiftool`.
- Slices are strictly ordered: each depends on the previous being merged to `dev`.

## Success Criteria

- [ ] Every `receipt-analysis` spec scenario has a passing test (scenarios referenced, not restated here).
- [ ] CBU/CVU and CUIT/CUIL validators pass the two known-answer fixtures above.
- [ ] `POST /v1/receipts/analyze` returns a full `FraudAssessment` with `ruleset_version` and `engine_version`.
- [ ] No response field or copy contains `is_real`, `is_fake`, `authentic`, or `verified transfer`.
- [ ] Identical input + ruleset version yields identical `risk_score`, `confidence_score`, `classification`.
- [ ] CI green with the new system dependencies; container builds and runs OCR without network at start.
- [ ] A core-field extraction failure produces an explicit `CORE_FIELD_EXTRACTION_FAILED` signal with a failure reason, contributing to `risk_score`, rather than a silent gap or a forced `INCONCLUSIVE`.
- [ ] `INCONCLUSIVE` triggers only on whole-request low evidence coverage across analyzers, verified by a test where one analyzer fails but others succeed and a non-`INCONCLUSIVE` classification is still returned.
