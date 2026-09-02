# Verify Report: ui-frontend-implementation

## Slice 1a

Change: ui-frontend-implementation | Slice verified: 1a only | PR: #13 (feat/web-scaffold-api-client -> dev)
Verdict: PASS WITH WARNINGS

### Completeness (tasks.md, slice 1a)
27/29 checklist items [x], 2 items [~] with documented deviations (1.3 .env, 5.2 Playwright e2e). No item silently dropped; both partials carry an explicit rationale and unblock condition. Confirmed by direct read of tasks.md lines 62-106.

### Runtime evidence (independently re-executed)
| Command | Result |
|---|---|
| cd apps/web and npx vitest run (after clean npm ci) | 8 files, 46/46 tests passing |
| cd apps/web and npm run check | 228 files, 0 errors, 0 warnings |
| cd apps/api and uv run pytest -q | all pass (4 skipped, OCR-model-dependent), no regression |
| Real cross-origin API call | Started uvicorn with RECEIPT_RISK_CORS_ALLOWED_ORIGINS=http://localhost:5173 plus vite dev on port 5173; curl OPTIONS preflight with Origin header returned access-control-allow-origin echoed; a real multipart POST to /v1/receipts/analyze returned 200 with a genuine AnalyzeResponse body (INCONCLUSIVE, OCR analyzers failed as expected without models present) |

### Spec compliance
Independently re-read spec.md. Actual counts: 8 requirements, 12 scenarios (verified by heading grep) - not "9 requirements, 15 scenarios" as recorded in Engram artifact sdd/ui-frontend-implementation/spec and repeated in docs/features/ui-frontend-implementation/SDD.md line 19. Documentation drift, not a functional defect (WARNING 4).

Coverage summary:
- Idle/upload state: covered (page.smoke.test.ts idle case)
- File selection/validation (valid plus oversized/unsupported): covered (FilePreview.test.ts, workspace.test.ts, page.smoke.test.ts)
- Uploading/processing ARIA-live: covered (ProcessingStages.test.ts, page.smoke.test.ts)
- Successful result display (3 scenarios: full render, no forbidden language, INCONCLUSIVE no forced color): deliberately out of scope for slice 1a - these belong to Slice 1b (tasks.md Phase 2, all unchecked); confirmed ScoreSummary, EvidenceList, ExtractedDataTable do not exist in this PR file list
- Validation error states (server error plus timeout): covered (ErrorPanel.test.ts, client.test.ts, workspace.test.ts, page.smoke.test.ts)
- Connectivity/network error: covered (page.smoke.test.ts network case)
- Rate-limit 429: covered (client.test.ts, workspace.test.ts, page.smoke.test.ts)
- No client-side persistence: structurally true (no localStorage, sessionStorage, indexedDB, or cookie references anywhere in apps/web/src or tests), but no automated test asserts it (WARNING 5)

### Disclaimer-always-renders invariant, independently verified
+page.svelte renders ReconciliationNotice unconditionally, outside any state-dispatch conditional block. No code path can unmount it, a structural guarantee, not just a tested one. page.smoke.test.ts asserts the disclaimer text present across all 6 covered states (idle, selected, uploading, result, network error, 429, 415, oversized client-validation). All pass under independent re-run.

### docs/API.md correction, independently verified against real schema
Re-read apps/api/src/receipt_risk/adapters/api/schemas.py directly: ExtractedFieldModel has exactly value, masked_value, confidence, is_checksum_valid (optional). docs/API.md now shows only amount, date_time, destination_cbu, cuit with no currency, beneficiary_name, or operation_id, and states is_checksum_valid must be treated as optional. apps/web/src/lib/api/types.ts mirrors the schema field-for-field. Claim confirmed correct.

### CI fix, independently verified
.github/workflows/ci.yml Type check step runs npm run check (svelte-kit sync then svelte-check), not a bare svelte-check call. The api job is untouched by this PR diff; its test suite was re-run independently with no regressions.

### .env deviation, verified non-blocking
apps/web/env.sample exists, apps/web/.gitignore excludes the real .env, and docs/wiki/Local-Setup.md documents the manual copy step. Independently ran type-check, unit tests, and the real dev server using PUBLIC_API_BASE_URL as a process env var with no .env file present, all succeeded.

### Playwright e2e deferral to slice 4, definitive verdict: ACCEPTABLE, not a merge blocker
design.md recommends an early smoke e2e as a nicety, not as a spec.md requirement. The substituted page.smoke.test.ts (Vitest plus jsdom plus testing-library) covers the same GWT scenarios via a mocked fetch. This session additionally exercised the real dev server and a real cross-origin network round trip end-to-end, which is stronger evidence for this specific slice than a scripted Playwright smoke spec would have been. Slice 4 already owns building the full Playwright harness; standing up a throwaway harness now would be wasted work. Verdict: acceptable trade-off for slice 1a sign-off; does not need to be pulled forward or block PR #13.

### Component scope correctness, confirmed correct
Slice 1a five components (DropZone, FilePreview, ProcessingStages, ErrorPanel, ReconciliationNotice) match design.md File Changes / Slice 1a table exactly. ScoreSummary, EvidenceList, ExtractedDataTable are correctly absent, Slice 1b scope per design.md and tasks.md (Phase 2, unchecked). The apply report claim of catching a prompt/tasks.md component-scope mismatch is independently verified correct.

### git diff --stat origin/dev...HEAD
41 files changed, 5380 insertions(+), 13 deletions(-)
apps/web/package-lock.json contributes 2982 generated lines (excluded from authored risk count), roughly 2398 authored lines. Exceeds the 400-line budget but was pre-forecast and pre-accepted in design.md and tasks.md as a single non-splittable PR.

## Issues

### CRITICAL
None.

### WARNING
1. Task 1.3 (apps/web/.env) remains [~], blocked by a categorical sandbox denial on writing any .env* path. Mitigated by env.sample plus documented manual copy step; functionally verified non-blocking. Needs a human or unrestricted session to create the real file once.
2. Task 5.2 (Playwright e2e) remains [~], deferred to slice 4. See definitive verdict above: acceptable, not a merge blocker.
3. Task 5.1 setContext deviation (direct workspace binding instead of setContext) is documented and spec-non-breaking. Revisit when slice 2/3a introduce a second consumer needing the same instance from the layout.
4. Scenario-count documentation drift: spec.md actually contains 8 requirements and 12 scenarios, not "9 requirements, 15 scenarios" as recorded in the spec Engram artifact and docs/features/ui-frontend-implementation/SDD.md. Recommend a follow-up doc correction; does not affect functional correctness.
5. The No client-side persistence spec scenario has no automated covering test, though code inspection confirms the invariant holds structurally. Recommend adding a positive assertion test in slice 1b or slice 4.

### SUGGESTION
None beyond the above WARNINGs.

## Final Verdict

PASS WITH WARNINGS. No CRITICAL findings. Slice 1a implementation matches its scoped spec/design/tasks; all runtime evidence (tests, type-check, API regression check, and a live cross-origin API round trip) was independently reproduced and passed. The two [~] tasks are legitimate, well-documented, non-blocking deviations. PR #13 is safe to merge as slice 1a; the 5 WARNINGs are follow-up/cleanup items, not merge blockers.

## Key Learnings

1. The frozen receipt-analysis-web-client spec actually has 8 requirements and 12 scenarios, not the 9/15 recorded in two prior artifacts, indicating a miscount that propagated across the spec save and its docs mirror.
2. A real cross-origin round trip (uvicorn plus vite dev servers, curl with an Origin header) is reproducible in this sandbox and is stronger evidence than a Playwright smoke spec for proving CORS configuration correctness.
3. The ReconciliationNotice disclaimer invariant is enforced structurally in +page.svelte (mounted outside any conditional block), not just by test coverage, making it robust against future state-machine changes.
4. Three successful result display spec scenarios are intentionally uncovered by slice 1a test suite because ScoreSummary, EvidenceList, and ExtractedDataTable are correctly scoped to slice 1b per design.md File Changes table.
5. Deferring the Playwright harness from slice 1a to slice 4 is an acceptable trade-off when the frozen spec scenarios are otherwise covered by Vitest component and integration tests.
