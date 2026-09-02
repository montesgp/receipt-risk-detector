# Verify Report: receipt-analysis-implementation

## Slice 1: Ingestion + fixture authoring

Verdict: PASS WITH WARNINGS (1 CRITICAL - samples/ path - must be fixed before merge; rest is clean)

### 1. Spec scenario to test mapping (receipt-analysis capability)

| Scenario | Covering test | Result |
|---|---|---|
| Valid image accepted | test_valid_jpeg_under_max_size_accepted, test_valid_png_accepted | PASS |
| Oversized or corrupt image rejected | test_oversized_image_rejected_4xx, test_corrupt_content_fails_decode_rejected_4xx | PASS |
| Excessive dimensions rejected | test_excessive_dimensions_rejected, test_excessive_pixel_count_rejected | PASS |
| Temp files removed on all paths | test_temp_file_cleanup_runs_on_success_error_and_exception | PASS |

All 4 slice-1 GWT scenarios have a passing runtime-verified test. 17/17 tests pass.

### 2. Independent re-run (not trusting apply report)

- uv run pytest -v: 17 passed in 0.66s (fresh run, not cached from apply).
- uv run ruff check .: All checks passed.
- uv run ruff format --check .: 26 files already formatted.

### 3. Layering boundary (grep, not claim)

Regex search for fastapi/cv2/paddleocr/PIL/Pillow imports over domain/ and application/: zero matches in both. Pillow import confirmed to exist ONLY in adapters/image/pillow_decoder.py and the standalone samples/generate.py (exempted via per-file-ignores "samples/**" = ["TID251"]). Boundary is real, not just claimed.

### 4. Temp-file cleanup - traced code path, not taken at face value

IngestionService.ingest() only calls temp_path.write_bytes(data) as the LAST step, after every validation gate has already passed. On every REJECTION path, no temp file is ever created - nothing to leak. On the SUCCESS path, the caller must call cleanup() from a finally block; cleanup() itself is idempotent. One residual gap: if write_bytes itself raises mid-write, the caller never receives a SafeImageRef to pass to cleanup(), and a partial file could be orphaned. Narrow, low-probability WARNING with no test coverage, acceptable for slice 1 scope but should be tracked before slice 4.

### 5. Privacy: no raw bytes or PII in logs

Zero logging statements exist anywhere in apps/api/src/receipt_risk/ as of slice 1. The privacy rule is vacuously satisfied for this slice; the real log-scan test is correctly deferred to slice 4 task 4.25.

### 6. samples/ path: DEFINITIVE VERDICT - apps/api/samples/ is WRONG, must move to repo root

Evidence:
- README.md "Repository layout" (lines 115-134) shows samples/ as a top-level sibling to apps/, not nested under apps/api/.
- README.md own "API example" section uses -F "file=@samples/receipt.png" - a repo-root-relative path.
- design.md "File Changes" table lists every other slice-1 path with an explicit apps/api/ prefix but lists samples/generate.py, samples/fonts/DejaVuSans.ttf, samples/images/star, samples/manifest.json WITHOUT that prefix. Every other path that belongs under apps/api/ says so explicitly, so the one exception (samples/) means repo root, matching README.
- design.md "Fixture Design" ASCII tree also renders samples/ as a bare top-level tree.

Conclusion: apps/api/samples/ is a genuine deviation, not an acceptable alternative interpretation. manifest.json own generator.script field says "samples/generate.py" (root-relative) while the file lives at apps/api/samples/generate.py, confirming the placement is wrong.

Corrective action needed before merge: move apps/api/samples/ to repo-root samples/, update tests/conftest.py SAMPLES_DIR, tests/fixtures/test_manifest_integrity.py SAMPLES_DIR, and the pyproject.toml per-file-ignore glob for samples.

### 7. samples/generate.py determinism: independently verified

Ran generate.py generate() function twice into two separate fresh temp directories via direct module import. diff -rq between the two output directories: IDENTICAL. SHA-256 of both runs output matches each other AND matches the committed samples/images files exactly. python samples/generate.py --check also independently reports "All fixtures match committed bytes."

### 8. manifest.json sha256 provenance: independently computed, not trusted

Computed sha256 of all 4 committed fixture files directly and cross-checked against manifest.json declared values. All 4 fixtures match: verified both via the automated test (passing) and manual sha256sum cross-check in this verify pass.

### 9. Task 1.11 TDD-ordering deviation (test_ports.py after ports.py existed)

Confirmed minor, honestly-disclosed process deviation, not untested code. ImageDecoderPort is a runtime_checkable Protocol with one method (probe). test_image_decoder_port_is_runtime_checkable asserts isinstance conformance, and probe() itself is exercised indirectly by every test_ingestion.py test. Full test coverage exists regardless of write order.

### 10. git diff --stat against dev (independently run)

git diff --stat origin/dev...HEAD: 29 files changed, 2355 insertions, 11 deletions.

Breakdown: binary/generated files (font, images, license, uv.lock) excluded from authored-line budget. OpenSpec planning docs (design.md 756, proposal.md 101, tasks.md 186) = 1043 lines. Authored implementation and tests total approximately 1114 lines, exceeding the 400-line PR review-workload budget. This was flagged in advance in tasks.md Review Workload Forecast table as High risk, so it is a disclosed, accepted risk under auto-chain delivery strategy, but PR 7 does exceed the standard reviewer budget.

## Key Learnings

1. samples/ must live at repo root per README documented layout and design.md own File Changes table, which prefixes every other slice-1 path with apps/api/ except samples/; apps/api/samples/ placement is a genuine defect requiring a path move.
2. samples/generate.py determinism claim holds under independent verification: two fresh runs produced byte-identical output matching committed fixture bytes exactly.
3. Slice 1 temp-file cleanup design creates temp files only after all validation gates pass, so rejection paths never leak files by construction; one residual gap is an unhandled mid-write I/O exception.
4. Zero logging statements exist in slice 1 source tree, so the privacy no-PII-in-logs rule is vacuously satisfied and correctly deferred to slice 4 log-scan test.
5. PR 7 actual authored diff of approximately 1114 lines confirms tasks.md pre-declared High 400-line-budget risk forecast for slice 1 was accurate.
