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

## Slice 2: Metadata + C2PA

Verdict: PASS (0 CRITICAL, 0 WARNING, 1 SUGGESTION)

### 1. Spec scenario to test mapping (receipt-analysis capability, Slice 2 scope)

| Scenario | Covering test(s) | Result |
|---|---|---|
| Missing metadata is neutral | test_missing_metadata_is_neutral_zero_signals_status_completed (exiftool, mocked, zero signals + status=completed); test_exiftool_inspects_real_fixture_without_metadata_neutrally (real binary, integration); test_c2pa_missing_manifest_emits_no_signal; test_c2pa_reader_inspects_real_fixture_without_manifest_neutrally (real Reader, integration) | PASS |
| Valid AI-generated provenance claim | test_c2pa_valid_ai_generated_claim_emits_critical_signal (asserts SignalCode.VALID_AI_GENERATED_CLAIM + Severity.CRITICAL + SignalCategory.PROVENANCE); test_valid_ai_generated_claim_signal_is_critical_severity (domain shape test) | PASS |

Both Slice 2 GWT scenarios have passing, runtime-verified covering tests (unit + integration). "Absence must not reduce risk score" is honored structurally: the neutral path returns zero signals; no scorer exists yet (slice 4), so the invariant is enforced by construction.

### 2. Independent re-run (not trusting apply report)

- uv run pytest -q -rs: 35 passed, 2 skipped (both tests/integration/test_metadata_provenance_integration.py, exiftool absent from this Windows sandbox PATH - matches documented skipif reason).
- uv run ruff check .: All checks passed.
- uv run ruff format --check .: 31 files already formatted.

### 3. Layering boundary (grep, not claim)

grep for import subprocess / import c2pa / from c2pa over apps/api/src/receipt_risk/: matches confined to exactly adapters/metadata/exiftool.py and adapters/provenance/c2pa_reader.py. Zero matches in domain/ or application/. Ruff's flake8-tidy-imports banned-api additionally bans both names outside adapters/** at lint time (ruff check . passed, confirming the rule is active, not dead config).

### 4. Subprocess safety (adapters/metadata/exiftool.py, _run_exiftool) - read directly, not trusted

- Argv is a literal Python list: [_EXIFTOOL, "-json", "-n", "-charset", "utf8", "-fast2", "--", str(path)] - never a shell string.
- shell=False explicit keyword (also verified by test_exiftool_argv_never_contains_client_supplied_filename, which asserts captured kwargs shell is False).
- timeout=timeout_s is a mandatory constructor parameter (DEFAULT_TIMEOUT_S = 2.0); subprocess.TimeoutExpired is caught and converted to status=timed_out, never left to propagate or orphan a process (subprocess.run with timeout kills the child via Popen.communicate internally per Python's documented contract).
- A double-dash end-of-options marker sits immediately before str(path), closing the -execute / argfile (-@) and any other leading-dash option-injection surface described in the threat matrix; test_exiftool_leading_dash_filename_no_option_injection proves a dash-prefixed temp filename is still treated as a literal filename.
- _EXIFTOOL is resolved once via shutil.which("exiftool") at import time (absolute path, never a bare command name reliant on a possibly-poisoned PATH at call time); env={"PATH": os.defpath, "LANG": "C"} further pins the subprocess's own PATH to the OS default rather than inheriting the parent process environment.
- The client-supplied filename never reaches this module: SafeImageRef.path is a server-generated temp path assigned by application/ingestion.py (slice 1); the adapter only ever sees that generated path. Confirmed by test_exiftool_argv_never_contains_client_supplied_filename, which asserts the malicious declared name is absent from the joined argv and the real temp path is the last argv element.
- No -@ argfile flag appears anywhere in the fixed argv, so ExifTool's own argfile-injection vector is structurally unreachable (the flag is simply never emitted, not merely sanitized).

All 4 threat-matrix adversarial cases (shell metacharacters in filename, leading-dash filename, hung binary, missing binary) have a dedicated RED test, and all 4 pass.

### 5. Skip-marked integration tests - confirmed via CI logs, not the apply report's claim

- Local: uv run pytest -q -rs shows both test_metadata_provenance_integration.py tests skipped with reason "exiftool binary not on PATH - CI installs it, this sandbox does not" - clean skip, no error.
- CI (gh run view 33601691863 --log, job "API Lint and Test"): the "Install system dependencies" step installs libimage-exiftool-perl and runs exiftool -ver successfully before the Test step. The Test step output is "35 passed in 1.07s" with 35 dots and zero s (skip) markers - pytest --collect-only -q independently confirms exactly 35 tests total are collected in this suite (2+2+4+1+2+6+2+11+5). Since local runs produce 33 passed + 2 skipped = 35 total, and CI produces 35 passed + 0 skipped = 35 total, the only consistent explanation is that CI's exiftool presence flips the skipif condition to False and both integration tests execute for real and pass - pytest always emits an explicit s marker for a skip regardless of environment, so its absence in the CI log confirms real execution, not silent omission. Claim confirmed by direct log inspection, not accepted on the apply report's word.

### 6. Privacy: no raw bytes / EXIF dumps / C2PA manifest PII in logs or exceptions

- grep for log./logging./logger. over adapters/metadata/ and adapters/provenance/: zero matches - neither adapter logs anything.
- exiftool.py: except ExifToolUnavailable / except subprocess.TimeoutExpired convert to a typed AnalyzerResult carrying only a status and error_code string - the raw stdout/tags dict is never included in any exception path. The only place tags are used is _derive_signals, which extracts a single lower-cased software string into evidence={"software": software} - a name string, not a raw EXIF dump.
- c2pa_reader.py: except Exception: return None swallows the underlying c2pa.Reader exception entirely (no re-raise, no logging of its message) - a broken/malformed manifest never surfaces its content. evidence on both signal types carries only {"active_manifest": str(active_label)} (a manifest UUID/label string), never the manifest JSON body.
- Both adapters return AnalyzerResult (a domain type) exclusively, per application/ports.py's own docstring contract that no port signature mentions dict/JSON so raw tool output can never cross the boundary - confirmed true by direct inspection of both inspect() methods, which never return or leak the parsed tags/manifest dict itself.

### 7. Business-logic scope check - no premature OCR/scoring/endpoint work

- grep for OcrPort/risk_score/def score/router/analyze_receipt/FraudAssessment/ScoringRuleset/financial over apps/api/src/: only matches are domain/signals.py (the SignalCode enum, expected in-scope), application/ports.py (docstrings referencing future slices by name, not implementing them), and adapters/api/__init__.py, whose entire content is a one-line docstring placeholder with zero code - matches slice 4's design.md note that adapters/api/router.py and bootstrap/app.py stay untouched until slice 4.
- No domain/financial/*, no domain/ruleset.py or domain/scoring.py, no application/analyze_receipt.py, no OCR adapter files exist on this branch. git diff --stat dev...HEAD confirms the changed-file set is exactly the slice-2 file list from design.md's Slice Boundaries table - no slice-3/4 files appear.

### 8. Design/config diffs verified byte-for-byte against design.md's literal specification

git diff dev...HEAD for pyproject.toml, Dockerfile, ci.yml matches design.md's "exact additions" sections: c2pa-python>=0.7 dependency; S602/S604/S605/S607 added to ruff.lint.select with the documented no-per-file-ignore comment; subprocess/c2pa banned-api entries with the documented messages; libimage-exiftool-perl apt layer in the Dockerfile at the documented location (before pip install uv, in the runtime stage); the CI "Install system dependencies" step inserted immediately after actions/checkout@v4, exactly as design.md specifies. No unexplained drift.

### 9. Resolution of the 3 flagged "known deviations"

1. 3rd signal code PROVENANCE_VALIDATION_FAILED - CONFIRMED SOUND, not scope drift. design.md's "Provenance adapter" prose states verbatim: "A manifest that fails validation emits a separate lower-severity signal; a missing manifest emits nothing." - read directly in this verification, not taken on the apply report's word. design.md's domain-signals interface table only lists the 2 AI-claim-critical codes because that table is explicitly the domain-signals code enum snapshot for slice 1's file, annotated "codes extended in 2/3/4" - it was never meant to be an exhaustive per-slice checklist; the prose is the authoritative requirement and the code was correctly derived from it, not invented.
2. Substring-match heuristic for algorithmic-source detection - CONFIRMED REASONABLE. _ALGORITHMIC_SOURCE_MARKERS is a 3-entry tuple matched case-insensitively against the full IPTC digitalSourceType URI string. It is clearly commented as a non-exhaustive "documented default" in both the adapter docstring and inline above the tuple, cross-referencing the proposal's "reasonable defaults, not fake precision" stance verbatim. It is never presented as authoritative elsewhere (no claim of completeness in any test name, docstring, or public surface). Matches the same pattern already used and accepted for _EDITOR_SOFTWARE_MARKERS in the ExifTool adapter.
3. ~760-line diff vs ~350 forecast - CONFIRMED NOT SCOPE CREEP. git diff --stat dev...HEAD shows exactly the slice-2 file set (10 source/test files + 3 config files + uv.lock + tasks.md checkbox updates); no slice-3/4 file exists on this branch (see item 7). The excess is entirely attributable to test volume: 6 tests in test_exiftool_adapter.py (4 threat-matrix RED tests + neutral-path + editor-signal test) at 180 lines, 4 tests in test_c2pa_reader.py at 100 lines, plus the new integration file (61 lines) - all traced 1:1 to spec scenarios or the design.md threat matrix, not speculative extra coverage. uv.lock's +363 lines (from c2pa-python's transitive dependency tree) is excluded from the authored-line review budget per the project's own generated-artifact exclusion rule; excluding it, authored additions are roughly 404 lines, modestly over the 350 forecast - consistent with, not contradicting, tasks.md's own advance warning to "watch test volume."

### 10. git diff --stat against dev (independently run)

.github/workflows/ci.yml: 6 lines added
apps/api/Dockerfile: 5 lines added
apps/api/pyproject.toml: 8 lines changed
apps/api/src/receipt_risk/adapters/metadata/exiftool.py: 144 lines added (new file)
apps/api/src/receipt_risk/adapters/provenance/c2pa_reader.py: 128 lines added (new file)
apps/api/src/receipt_risk/application/ports.py: 35 lines changed
apps/api/src/receipt_risk/domain/signals.py: 5 lines added
apps/api/tests/integration/test_metadata_provenance_integration.py: 61 lines added (new file)
apps/api/tests/unit/test_c2pa_reader.py: 100 lines added (new file)
apps/api/tests/unit/test_domain_signals.py: 42 lines added (new file)
apps/api/tests/unit/test_exiftool_adapter.py: 180 lines added (new file)
apps/api/tests/unit/test_ports.py: 46 lines changed
apps/api/uv.lock: 363 lines added (generated, excluded from authored budget)
openspec/changes/receipt-analysis-implementation/tasks.md: 36 lines changed (checkbox updates)
Total: 14 files changed, 1130 insertions, 29 deletions.

Matches design.md's Slice 2 file list exactly (metadata + provenance adapters, ports.py/signals.py extensions, pyproject.toml/Dockerfile/ci.yml config, plus tests). No file outside this set was touched.

### 11. SUGGESTION (non-blocking)

The algorithmic-source and editor-software marker lists have no regression test asserting they stay in sync with the code comment claiming "not exhaustive, revisit with real-world samples" - a future slice (or a dedicated follow-up) could add a golden/property test enumerating known IPTC digitalSourceType codes to catch silent marker-list drift. Not blocking Slice 2 merge; purely a forward-looking hardening note.

## Key Learnings

1. design.md's domain-signals interface table is a per-slice code snapshot, not an exhaustive checklist - its own prose is the authoritative source for PROVENANCE_VALIDATION_FAILED, and the apply-time deviation is correctly derived from that prose, not invented.
2. CI's "35 passed, 0 skipped" vs local's "33 passed, 2 skipped" (both against 35 total collected tests) is the correct signature proving the two exiftool-dependent integration tests genuinely execute for real in CI rather than being silently dropped - pytest always emits an explicit skip marker, so its absence in CI confirms real execution.
3. ExifTool subprocess safety is enforced structurally (fixed argv list, shell=False, end-of-options guard, shutil.which-resolved absolute path, pinned subprocess environment, mandatory timeout) rather than by sanitizing the untrusted client filename, which never reaches the adapter at all because ingestion discards it before this layer runs.
4. Both slice-2 adapters return only the domain AnalyzerResult type and swallow tool exceptions without logging or re-raising their content, so raw EXIF/C2PA manifest bytes structurally cannot leak into logs or error responses.
5. The ~760-line actual diff vs ~350-line forecast is fully explained by threat-matrix test volume across two new adapters, not by any slice-3/4 code appearing early, confirmed by both a file-set diff and a scope grep finding zero premature OCR/scoring/router code.

## Slice 3a: Financial validators (pure domain, no new deps)

Verdict: PASS (0 CRITICAL, 1 WARNING, 0 SUGGESTION)

### 1. Independent recomputation of both locked known-answer fixtures (hand math, not the implementation)

Wrote a standalone script (not importing receipt_risk) reimplementing the mod-10/mod-11 formulas from the proposal's locked algorithm table and ran it against the two fixtures:

- CBU 2850590940090418135201: manual mod-10 block1 -> DV1=9 (matches digit[7]=9); manual mod-10 block2 -> DV2=1 (matches digit[21]=1). Matches the locked algorithm exactly.
- CUIT 20172543597 (from 20-17254359-7): manual mod-11 over weights [5,4,3,2,7,6,5,4,3,2] on the first 10 digits -> check digit=7 (matches digit[10]=7). Matches the locked algorithm exactly.

### 2. Actual implementation run directly (not trusting the test file)

Ran validate_cbu() and validate_cuit() directly in a uv run python one-liner, independent of pytest:

- validate_cbu("2850590940090418135201") -> is_valid=True, normalized echoes input. Matches.
- validate_cuit("20-17254359-7") -> is_valid=True, normalized="20172543597" (hyphens stripped). Matches.
- Corrupted variant 1: flipped last digit of CBU fixture -> is_valid=False, failure=BLOCK2_CHECK_DIGIT. Correctly rejected.
- Corrupted variant 2: flipped mid-block digit of CBU fixture -> is_valid=False, failure=BLOCK2_CHECK_DIGIT. Correctly rejected.
- Corrupted variant 3: flipped CUIT check digit -> is_valid=False, failure=CHECK_DIGIT. Correctly rejected.
- Corrupted variant 4: flipped CUIT leading digit -> is_valid=False, failure=CHECK_DIGIT. Correctly rejected.

Independent recomputation confirms the locked algorithm's expected outputs, and the actual implementation reproduces the same outputs on both valid fixtures and correctly rejects all four deliberately corrupted variants.

### 3. Spec scenario to test mapping (Slice 3a scope)

| Scenario | Covering test(s) | Result |
|---|---|---|
| Invalid CBU check digit (FR-006, the only Slice-3a GWT scenario in spec.md) | test_validate_cbu_rejects_mutated_block2_check_digit (unit, literal); test_invalid_cbu_fixture_produces_expected_signal (manifest-driven, exercises validate_financials() end-to-end against samples/manifest.json's invalid_cbu_check_digit fixture, asserting INVALID_CBU_CHECK_DIGIT / financial_consistency / high) | PASS |

Only one GWT scenario in openspec/specs/receipt-analysis/spec.md traces to Slice 3a (Invalid CBU check digit under Requirement: Financial validation); this matches tasks.md's own scenario trace line for the slice. Both the literal unit test and the fixture-driven end-to-end test pass at runtime.

### 4. Independent re-run (not trusting the apply report)

- uv run pytest -q: 63 passed, 2 skipped (pre-existing exiftool-absent skips from Slice 2, unrelated to this slice; confirmed by rerun, not accepted from the apply report).
- uv run ruff check .: All checks passed.
- uv run ruff format --check .: 45 files already formatted.

### 5. Zero new dependencies

git diff dev -- apps/api/pyproject.toml is empty - confirmed independently. Pure-logic slice, no new dependency surface.

### 6. Layering boundary (grep, not claim)

grep of import statements in src/receipt_risk/domain/financial/*.py shows only stdlib and internal receipt_risk.domain.* imports (__future__, collections.abc, dataclasses, enum, typing, datetime, re, decimal). Zero fastapi/starlette/cv2/paddleocr/PIL/subprocess/c2pa imports anywhere under domain/financial/. Layering is real, not asserted.

### 7. Deviation review #1 - field-name-agnostic detect_contradictions()

Confirmed reasonable, not a bug. design.md defines exactly one contradiction signal code (AMOUNT_DATE_CONTRADICTION, line 132) - no generic field-contradiction code exists in the locked vocabulary. detect_contradictions() groups any repeated field name with disagreeing normalized values (not just amount/date pairs) and financial_validation.py emits the single available code for every such group. This is a broadening, not a narrowing, of detection: it does not silently under-detect real amount/date contradictions (the literal amount-repeated-twice scenario in test_amount_date_contradiction_detected still fires correctly), and any other repeated-field disagreement also now surfaces via the same code rather than being silently dropped. Acceptable interpretation given the constrained code vocabulary; worth a design.md follow-up note if a future slice wants field-specific contradiction codes, but not a blocking issue.

### 8. Deviation review #2 - CORE_FIELD_EXTRACTION_FAILED and ExtractionFailureReason defined here, consumed in 3b

Confirmed intentional, not premature slice-3b logic leaking in. tasks.md task 3a.17 explicitly lists CORE_FIELD_EXTRACTION_FAILED and ExtractionFailureReason as part of the Slice 3a domain/signals.py modification. design.md (line 134, and the OCR-adapter prose near lines 379/402) independently confirms the vocabulary is meant to live in domain/signals.py ahead of the adapter that emits it, consistent with domain-first sequencing already used for other signal codes in Slices 1-2. The diff for domain/signals.py shows only enum/StrEnum additions - no adapter code, no OCR-specific logic, nothing beyond vocabulary. Zero premature slice-3b implementation.

### 9. git diff --stat against dev (independently run)

17 files changed, 730 insertions(+), 20 deletions(-)

Breakdown: pure-domain source (cbu.py 63, cuit.py 38, money.py 55, dates.py 28, contradictions.py 28, financial/__init__.py 8), application orchestration (financial_validation.py 117), domain/signals.py +17, 7 new/extended test files (~358 lines), and tasks.md checkbox updates (38 lines). File set matches design.md's Slice 3a boundary exactly - no adapters/ocr files, no pyproject.toml, no Dockerfile/ci.yml changes present (those belong to Slice 3b per design.md's slice table).

WARNING (non-blocking): tasks.md's own Review Workload Forecast projected Slice 3 (pre-split) risk as Medium. Actual authored diff is approximately 692 lines (730 total minus the 38-line tasks.md checkbox delta), moderately exceeding the forecast, mostly attributable to test volume across 7 new test files covering multiple validators. Not a scope-creep concern (file set matches the design boundary exactly, confirmed above) and delivery strategy (auto-chain, already accepted by the product owner) already resolves the PR-boundary question - flagged for tasks.md forecast-accuracy tracking only, not a blocker for this PR.

## Key Learnings

1. Independent hand recomputation of the CBU mod-10 (DV1=9, DV2=1) and CUIT mod-11 (check digit=7) formulas exactly matches both the locked proposal algorithm and the actual validate_cbu/validate_cuit implementation output.
2. Four deliberately corrupted variants (CBU last-digit flip, CBU mid-block digit flip, CUIT check-digit flip, CUIT leading-digit flip) are all correctly rejected by the implementation with the expected ChecksumFailure reason.
3. detect_contradictions being field-name-agnostic rather than amount/date-specific is a reasonable interpretation given design.md defines only one AMOUNT_DATE_CONTRADICTION code, and it broadens rather than narrows detection coverage.
4. CORE_FIELD_EXTRACTION_FAILED and ExtractionFailureReason living in Slice 3a's domain/signals.py ahead of Slice 3b's OCR adapter is explicitly required by tasks.md task 3a.17, not scope leakage.
5. Slice 3a's actual diff (approximately 692 authored lines) moderately exceeds tasks.md's own pre-declared forecast, driven by test volume across 7 new test files, not by file-set scope creep.

## Slice 3b: OCR adapter + infra

Verdict: PASS

Context: this slice was completed in two passes -- a background sdd-apply agent (ports.py OcrPort, field_parsers.py, preprocess.py, paddle_onnx.py, unit tests) was killed mid-work before finishing infra, then the orchestrator directly finished fetch_ocr_models.py, Dockerfile/ci.yml, an expanduser bugfix plus regression test, and tests/integration/test_ocr_integration.py. Both halves were verified with equal rigor.

### 1. Spec scenario to test mapping

| Scenario / decision | Covering test | Result |
|---|---|---|
| Field extracted with confidence (FR-005) | test_amount_extracted_with_raw_normalized_and_confidence, test_real_engine_extracts_all_core_fields_from_clean_fixture (real engine, real fixture) | PASS |
| Bounded single retry (locked decision) | test_exactly_one_preprocessing_retry_when_below_threshold, test_retry_keeps_better_result_by_coverage_and_confidence, test_no_text_detected_reason_skips_retry_when_budget_insufficient | PASS |
| CORE_FIELD_EXTRACTION_FAILED signal (locked decision) | test_core_field_extraction_failed_emitted_with_reason_low_confidence_after_retry | PASS |
| Threat matrix: OCR model loading, bogus dir | test_ocr_adapter_bogus_model_dir_returns_analyzer_unavailable_no_download, test_ocr_adapter_extract_with_bogus_model_dir_returns_analyzer_unavailable | PASS |
| Threat matrix: zero outbound network connections | test_ocr_analysis_makes_zero_outbound_network_connections | PASS |

All 21 slice-3b tasks marked [x] and match the actual code state.

### 2. Independent re-run (not trusting apply/orchestrator claims)

- uv run pytest: 76 passed, 4 skipped locally (2 exiftool-absent, 2 OCR-model-dir-absent -- pre-existing skip patterns, not new gaps).
- uv run ruff check .: All checks passed.
- uv run ruff format --check .: 53 files already formatted.
- Re-ran CI's own log for PR #10 run 33660161135 ("API Lint and Test"): 80 passed (76 local + the 4 that only run when models/exiftool are present) -- exact arithmetic match, confirming the CI environment genuinely exercises the 4 tests this sandbox skips, not a silently-degraded green.

### 3. Model pin authenticity (independently reproduced)

Downloaded all 3 pinned URLs myself with `uv run --with requests==2.32.3 python scripts/fetch_ocr_models.py --dest <tmp> --verify`:
- Real download succeeded, "sha256 verified" printed for det.onnx, cls.onnx, rec.onnx.
- Independently recomputed sha256 with sha256sum outside the script: matched the pinned values in fetch_ocr_models.py exactly for all 3 files.
- Ran the script a second time: printed "already present, sha256 matches" for all 3 files with zero new downloads -- idempotency confirmed.
- Inspected first 32 bytes of each file with xxd: readable protobuf strings (PaddlePaddle, batch_norm2d_0.b_0, conv12_...) -- genuine ONNX/protobuf content, not an HTML error page.

### 4. Real-engine integration test (ran myself against my own downloaded models)

RECEIPT_RISK_OCR_MODEL_DIR=<my tmp dir> uv run pytest tests/integration/test_ocr_integration.py -v -> 2 passed in 8.45s.
- clean_valid_transfer.png: extracted destination_cbu=2850590940090418135201, cuit=20172543597, amount=125000.00 -- matches samples/manifest.json's declared_fields exactly.
- low_quality_skewed.jpg: the module docstring's honesty note ("this fixture's degradation does NOT trigger the retry branch with the real engine -- verified by instrumenting the engine call count, which stays at 1") is independently confirmed true -- the test asserts call_count == 1 and it passed. The orchestrator did not overstate or fabricate this claim.

### 5. expanduser bug -- reproduced both failing and fixed states myself

Without .expanduser(): path stays "~\.cache\receipt-risk\ocr-models" (relative, does not exist).
With .expanduser(): resolves to the real absolute home directory path.

Confirms the root-cause claim: GitHub Actions' env: mapping passes "~/.cache/receipt-risk/ocr-models" through literally without shell expansion, so _model_dir_from_env() without .expanduser() would silently look in a nonexistent relative path. The fix (Path(value).expanduser()) is present in paddle_onnx.py, and test_model_dir_from_env_expands_tilde_to_home_directory covers the regression.

### 6. Network-blocking test -- verified it actually discriminates loopback vs outbound

Extracted the guard's exact logic into a standalone script and fired a real connect() attempt to 8.8.8.8:53: the guard correctly raised AssertionError("OCR analysis attempted to open an outbound network connection"). Loopback addresses (127.0.0.1, ::1, localhost) are explicitly allow-listed, required so asyncio's Windows ProactorEventLoop self-pipe socketpair does not false-positive. The guard is a real behavioral check, not a no-op.

### 7. Bounded retry hard bound

Read paddle_onnx.py::_run_bounded_retry: exactly two possible engine-call sites in the function body (engine(pixels) at attempt 1, engine(preprocessed) at attempt 2), no loop, no recursion -- structurally impossible to exceed 2 calls under any input. Confirmed further by _CountingEngine-based tests asserting call_count == 1 (early completion / budget-insufficient paths) or call_count == 2 (retry-triggered paths) -- no test path shows a 3rd call.

### 8. Layering

grep -rl for cv2/onnxruntime/rapidocr_onnxruntime imports over apps/api/src/receipt_risk/ returns only adapters/ocr/paddle_onnx.py and adapters/ocr/preprocess.py. field_parsers.py imports only stdlib plus receipt_risk.domain.analysis / receipt_risk.domain.financial.money -- no tool-specific import. Boundary holds structurally; ruff's TID251/banned-api additions (onnxruntime, rapidocr_onnxruntime) also present in pyproject.toml.

### 9. Dockerfile / ci.yml vs design.md's exact snippets

Diffed apps/api/Dockerfile, .github/workflows/ci.yml, apps/api/pyproject.toml against dev. Content matches design.md's literal snippets field-for-field (ocr-models build stage, COPY --from=ocr-models, RECEIPT_RISK_OCR_MODEL_DIR/HF_HUB_OFFLINE/OMP_NUM_THREADS env vars, "Cache OCR models" + "Fetch OCR models" steps, Test step's env block). One immaterial ordering deviation: design.md said to insert the CI steps "after Sync dependencies"; the actual diff places them after Lint/Format check and immediately before Test, which is functionally equivalent (still runs before pytest, still after uv sync) -- WARNING, not CRITICAL, no spec or design requirement is broken by this ordering choice.

### 10. PR #10 CI run authenticity (not just "job passed")

Fetched the full log of run 33660161135 for job "API Lint and Test": Fetch OCR models step's log shows real download URLs hit (https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.9.2/...) and "sha256 verified" for all 3 files at 17:18:02, immediately followed by the Test step's env block showing RECEIPT_RISK_OCR_MODEL_DIR: ~/.cache/receipt-risk/ocr-models and "80 passed in 4.51s". This is a real, non-silently-skipped execution of the critical model-fetch step, not a false green.

### 11. git diff --stat vs dev

```
.github/workflows/ci.yml                           |  13 +-
apps/api/Dockerfile                                |  46 +++-
apps/api/pyproject.toml                            |   9 +
apps/api/scripts/fetch_ocr_models.py               | 129 +++++++++
.../src/receipt_risk/adapters/ocr/field_parsers.py | 135 +++++++++
.../src/receipt_risk/adapters/ocr/paddle_onnx.py   | 265 ++++++++++++++++++
.../src/receipt_risk/adapters/ocr/preprocess.py    |  76 ++++++
apps/api/src/receipt_risk/application/ports.py     |  16 +-
apps/api/tests/integration/test_ocr_integration.py |  93 +++++++
apps/api/tests/unit/test_ocr_field_parsers.py      |  63 +++++
apps/api/tests/unit/test_ocr_paddle_onnx.py        | 213 +++++++++++++++
apps/api/tests/unit/test_ocr_preprocess.py         |  57 ++++
apps/api/tests/unit/test_ports.py                  |  19 +-
apps/api/uv.lock                                   | 301 ++++++++++++++++++++-
.../receipt-analysis-implementation/tasks.md       |  42 +--
15 files changed, 1436 insertions(+), 41 deletions(-)
```

Excluding uv.lock (generated) and the tasks.md checkbox update, authored diff is roughly 1093 lines -- above the tasks.md forecast (~600-650, already flagged High) but the forecast itself anticipated this and offered a size:exception fallback; not a new finding.

### 12. Apply-progress artifact gap (process note, not a code defect)

No Engram apply-progress observation exists for slice 3b specifically (the last persisted one, #1856, still says "Remaining: Slice 3b ... not started"). This is consistent with the stated history: the background agent was killed before it could persist progress, and the orchestrator that finished the slice did not author a replacement apply-progress save. WARNING: the pipeline's memory trail has a gap for this slice; recommend the orchestrator backfill an apply-progress observation for slice 3b before archive.

### Summary

- CRITICAL: none.
- WARNING: (1) CI step insertion order differs immaterially from design.md's literal instruction; (2) no apply-progress Engram record exists for slice 3b, leaving a stale "not started" record as the most recent memory of this slice's status.
- SUGGESTION: none beyond what's already noted inline.

All spec scenarios, locked decisions, and threat-matrix cases for slice 3b are backed by a passing runtime test that this verify pass re-ran independently. Model pins are real, correct, and reproducible. The expanduser fix and the network-blocking test's loopback/outbound discrimination both hold under direct reproduction. Safe to proceed to slice 4 once the orchestrator addresses the apply-progress backfill.

## Slice 4 (final): Risk engine + response assembly

Verdict: PASS WITH WARNINGS.

### 1. Spec scenario to test mapping

| Scenario / requirement | Covering test | Result |
|---|---|---|
| receipt-analysis: Deterministic score for identical input | test_deterministic_score_same_input_and_ruleset_twice_identical_triple plus my own independent re-run | PASS |
| receipt-analysis: No absolute verdict | test_response_never_contains_forbidden_verdict_vocabulary plus my own grep over adapters/api and docs/API.md | PASS |
| Locked decision: OCR fails, others succeed, NOT INCONCLUSIVE | test_confidence_independent_of_risk_ocr_fails_others_succeed_not_inconclusive plus my own constructed scenario | PASS, LOW_RISK not INCONCLUSIVE, confidence_score=50 |
| Locked decision: all analyzers fail, INCONCLUSIVE | test_inconclusive_when_all_analyzers_fail_coverage_zero plus my own re-run | PASS, confidence_score=0, INCONCLUSIVE |
| CORE_FIELD_EXTRACTION_FAILED contributes to risk_score | verified independently by A/B comparison with and without the signal | PASS, risk_score rose from 0 to 15 |
| public-api-contract: Analysis endpoint works without session | test_post_analyze_returns_full_assessment_with_ruleset_and_engine_version plus my own TestClient smoke test | PASS |
| public-api-contract: Version endpoint reports engine and ruleset | my own smoke test of GET /version | PASS |
| public-api-contract: Stable error contract | test_api_error_contract.py plus my own smoke test | PASS for 5 reachable ingestion codes plus RATE_LIMITED; ANALYZER_UNAVAILABLE structurally unreachable, disclosed, see item 7 |
| public-api-contract: CORS allowlist scenarios | none | FAIL, no covering test, no implementation, see item 11 |
| api-rate-limiting: default and analyze-endpoint limits, 429 with Retry-After | test_rate_limit.py, test_rate_limit_middleware.py plus my own independent 11-request run against the real app | PASS, 429 on request 11 |
| api-rate-limiting: env-configurable limits, documented single-instance limitation | config.py env vars, docs/API.md section 5b | PASS |
| data-retention: sensitive fields masked in logs | test_log_privacy.py caplog scan | PASS |

### 2. Independent re-run (not trusting the apply report)

- cd apps/api && uv run pytest --tb=no -rs: 122 passed, 4 skipped (2 exiftool-absent, 2 OCR-model-dir-absent, same pre-existing sandbox skip pattern as slices 2 and 3b).
- uv run ruff check .: All checks passed.
- uv run ruff format --check .: 81 files already formatted.

### 3. Determinism, independently re-implemented

Called domain.assessment.assemble() twice with byte-identical signals/results/ruleset but different duration_ms (100 vs 999). Diffed (risk_score, confidence_score, classification): identical, (54, 100, SUSPICIOUS) both times.

### 4. INCONCLUSIVE correctness, independently constructed

Built an AnalyzerResult list with ocr.status=failed and metadata/provenance both completed, plus the CORE_FIELD_EXTRACTION_FAILED signal. Result: classification=LOW_RISK (not INCONCLUSIVE), confidence_score=50 (0.20 metadata + 0.30 provenance = 0.50 coverage, matches design.md worked example exactly), risk_score=15. Re-ran with all three analyzers failed and zero signals: classification=INCONCLUSIVE, confidence_score=0. Both match design.md locked-decision worked example verbatim.

### 5. CORE_FIELD_EXTRACTION_FAILED risk contribution, independently confirmed by A/B

Same ocr-failed analyzer-status set scored twice: with vs without the signal. risk_score went from 0 to 15 solely from the signal (weight 15 times severity_multiplier MEDIUM 1.0 times confidence 1.00 equals 15).

### 6. Rate limiting, independently exceeded

Fired 11 real POST /v1/receipts/analyze requests against the actual bootstrap.app.app. Request 11 returned 429, Retry-After 6, and the documented problem+json body with code RATE_LIMITED, matching docs/API.md section 5b exactly. Confirms the 10/min analyze bucket fired, since the looser 30/min default bucket would not trip until request 31.

### 7. ANALYZER_UNAVAILABLE 503 structural unreachability, confirmed accurate and honestly disclosed

Traced every exception/timeout branch in application/analyze_receipt.py guarded(): every branch returns an AnalyzerResult, none re-raises. router.py only catches IngestionError and AnalysisTimeoutError. There is no code path that can ever return a 503 from POST /v1/receipts/analyze. This is a real spec/documentation mismatch (docs/API.md section 5 still lists 503 ANALYZER_UNAVAILABLE as an expected error) but it is the direct correct consequence of the locked never-abort decision, and it is explicitly disclosed in docs/features/receipt-analysis/TDD.md and the PR body as a known contract gap. WARNING, not CRITICAL: recommend a documentation fast-follow.

### 8. Full endpoint smoke test, run myself

TestClient against the real receipt_risk.bootstrap.app.app: GET /health returns 200 status ok; GET /ready returns 200 with analyzer identities; GET /version returns 200 with engine_version 0.1.0 and ruleset_version 2026-09-01; POST /v1/receipts/analyze with the real clean_valid_transfer.png fixture bytes returns 200 with a full FraudAssessment shape matching docs/API.md section 3 top-level keys (OCR and exiftool genuinely failed locally since this sandbox lacks the binary and models; c2pa succeeded for real, confirming the never-abort contract end to end against the real router).

### 9. Layering, grepped not asserted

Grep for fastapi/starlette imports over domain/ and application/: zero matches in both, for slice 4 new files.

### 10. bootstrap/app.py dependency_overrides pattern, definitive verdict per the orchestrator request

Facts confirmed by reading dependencies.py, router.py, bootstrap/app.py, and every test that constructs a FastAPI app:

- get_use_case() is a placeholder that unconditionally raises RuntimeError; it exists purely as a Depends() identity key, never meant to execute.
- router.py handler takes use_case: AnalyzeReceiptUseCase = Depends(get_use_case).
- bootstrap/app.py creates exactly one module-level FastAPI() instance, constructs the real use case singleton once at import time, and sets app.dependency_overrides[get_use_case] = lambda: _use_case immediately after, before any route is served.
- dependency_overrides is a plain instance dict on that one app object, not shared class-level or module-level global state.
- Every test that exercises the router (test_router.py, test_analyze_endpoint_e2e.py) constructs its own separate FastAPI() instance with its own dependency_overrides dict. There is zero shared mutable state between the production bootstrap.app.app singleton and any test app instance.
- The one test that touches bootstrap.app.app directly only calls .openapi(), a read-only call that never mutates dependency_overrides.

Multi-worker risk assessed explicitly: under uvicorn with multiple workers, each worker is a separate OS process, so bootstrap/app.py is imported fresh per process, producing an independent app, use case, and override dict per worker; no cross-worker interference is possible. Under pytest running many modules in one process, Python module caching means bootstrap.app is imported at most once per session, and since no test mutates its dependency_overrides, there is no cross-test pollution, observed or theoretical.

Verdict: this pattern is stylistically backward and unconventional, but functionally correct with no actual runtime hazard, under single-worker or multi-worker deployment, and under the test suite as written. The idiomatic fix is to make get_use_case itself a real factory, or to add a small composition-root function that closes over the real instance, which would remove the reading friction the orchestrator correctly flagged, but this is a recommended follow-up refactor, not a merge blocker.

### 11. CORS gap, found while tracing the public-exposure boundary

Grep for CORSMiddleware or CORS anywhere in apps/api/src returns zero matches. openspec/specs/public-api-contract/spec.md, which is frozen, has a CORS allowlist requirement with two GWT scenarios: Allowed browser origin and Disallowed browser origin. Neither scenario has any implementation or covering test anywhere in this codebase.

This is not merely an unimplemented nice-to-have. openspec/changes/archive/2026-09-01-mvp-init-foundation/design.md, an already-accepted prior design, contains an explicit instruction under its rate-limiting decision stating that CORS middleware must wrap the rate limiter so a 429 still carries Access-Control-Allow-Origin, worded as part of the acceptance contract handed to the implementation change that ships the rate limiter. This PR is exactly that implementation change, since task 4.29 ships the rate limiter for the first time, yet only the rate limiter half of that paired instruction was implemented. The CORS half was not implemented, and unlike the ANALYZER_UNAVAILABLE gap, this omission is not mentioned anywhere: not in tasks.md, not in TDD.md Known deviations section, not in the PR body.

Practical consequence: POST /v1/receipts/analyze is now genuinely public with no auth, for the first time. multipart/form-data is a CORS-safelisted content type, so a cross-origin browser POST from any third-party site executes server-side, consuming rate-limit budget and compute, even though the response would be unreadable to the calling page without a matching Access-Control-Allow-Origin header. This is a real, if narrow, availability and abuse consideration on a launch whose only other access control is the per-IP token bucket. It also means the web client own legitimate cross-origin calls, if the SvelteKit UI is ever served from a different origin per docs/ARCHITECTURE.md, would currently be silently blocked by the browser rather than allowed, since no origin is ever allowlisted.

Issue 1, the most significant finding of this verify pass: public-api-contract CORS allowlist requirement has zero implementation and zero test coverage on the exact PR that makes the endpoint public for the first time, despite a prior accepted design document specifically pairing it with the rate limiter this PR does ship. Unlike the ANALYZER_UNAVAILABLE gap, this is an undisclosed gap against a still-frozen, unmodified spec requirement. Recommend either adding CORSMiddleware wired from an env-configurable allowlist before merge, matching docs/API.md section 5b own claim that CORS wraps the rate limiter, or explicitly documenting this as an accepted disclosed MVP1 gap and filing a tracked follow-up before this PR merges. The silence is the actual defect here, not necessarily the missing code by itself.

### 12. extracted_data and analyzer_statuses nested-shape drift vs docs/API.md, found independently

test_analyze_response_schema_matches_docs_api_md_field_for_field (task 4.18) only asserts the top-level response key set matches docs/API.md; it does not assert nested field shapes. Reading docs/API.md section 3 example against adapters/api/schemas.py and mappers.py directly surfaces three drifts:

1. docs/API.md extracted_data.amount example includes a currency field; ExtractedFieldModel has no currency field at all, so it can never appear in a real response.
2. docs/API.md extracted_data.destination_cbu example shows is_checksum_valid populated as false; mappers.py never sets is_checksum_valid on any ExtractedFieldModel, so it is always null in the real response.
3. docs/API.md analyzer_statuses analyzer example shows generic role names such as ocr; the real mapper emits concrete adapter names such as paddleocr-onnx, exiftool, c2pa, confirmed by my own smoke test actual response body above.

WARNING, non-blocking: these are genuine documentation and implementation contract mismatches that would confuse a third-party integrator coding against the documented example literally, for example filtering analyzer_statuses by ocr would never match. Task 4.28 found and fixed one drift (recommended_action) but the top-level-only contract test could not surface these nested ones. Recommend a fast-follow to either implement currency and is_checksum_valid, or correct docs/API.md example to match the real shape, and to either emit the documented generic role name or update the docs to show the concrete adapter name.

### 13. request_id hardcoded, SUGGESTION only

errors.py and middleware/rate_limit.py both hardcode request_id to a constant placeholder rather than generating a real per-request correlation ID. No spec scenario in any of the four read specs mandates real request-ID generation, so this is not a spec violation, but it reduces the practical debugging value of request_id for support and log correlation across concurrent requests.

### 14. git diff --stat against dev, independently run

37 files changed, 2442 insertions, 34 deletions. File set matches design.md Slice 4 File Changes and Slice Boundaries tables exactly, plus the disclosed rate-limiting addition (task 4.29). No file beyond this set appears; there is no slice 5.

### 15. PR metadata

gh pr view 11 confirms baseRefName dev, headRefName feat/receipt-analysis-risk-engine, and the PR body contains the literal text Closes #1, which is correct for the final slice.

### Summary

- Most significant finding: Issue 1, the CORS allowlist requirement from the frozen public-api-contract spec is wholly unimplemented and untested on the exact PR that makes the endpoint public for the first time, and unlike every other deviation in this slice it is undisclosed anywhere, despite a prior accepted design document explicitly pairing it with the rate limiter this PR does ship.
- WARNING: the docs/API.md 503 ANALYZER_UNAVAILABLE row is genuinely unreachable through the router, correctly disclosed as a locked-decision consequence, but the docs should still be corrected in a fast-follow.
- WARNING: extracted_data and analyzer_statuses nested shape drifts vs docs/API.md literal example, undetected by task 4.18 top-level-only contract test.
- SUGGESTION: request_id is hardcoded to a constant placeholder rather than generated per request.
- The bootstrap/app.py dependency_overrides production-wiring pattern is unconventional but functionally correct with no actual runtime hazard, since each FastAPI instance owns an independent dependency_overrides dict with zero shared mutable state; recommend a follow-up refactor for maintainability, not a merge blocker.
- All independently-constructed determinism, INCONCLUSIVE-coverage, CORE_FIELD_EXTRACTION_FAILED-contributes-to-risk, and rate-limit-429 checks passed on real runtime execution, not on trusting the existing tests assertions alone.
- uv run pytest (122 passed, 4 skipped, same pre-existing environment-driven skip pattern as slices 2 and 3b), ruff check, and ruff format --check all independently re-run clean.
- PR body correctly says Closes #1.

## Key Learnings

1. domain.assessment.assemble worked example from design.md, OCR fails while metadata and provenance complete giving coverage 0.50 and confidence 50 and not INCONCLUSIVE, reproduces exactly under independent direct construction.
2. A prior accepted design document can hand an explicit paired acceptance contract to a future implementation change, and when only half of that pair ships without disclosure it becomes a silent spec gap even though the other half is fully implemented and tested.
3. A field-for-field contract test that only asserts top-level response keys can pass while nested field shapes silently drift from the documented example, so top-level key-set equality is not sufficient proof of full contract compliance.
4. dependency_overrides used in production bootstrap code is safe in this codebase specifically because exactly one FastAPI instance is created per process and every test constructs its own separate instance with its own override dict; the pattern safety depends on that per-instance isolation holding.
5. multipart form-data is a CORS-safelisted content type, so a public endpoint accepting multipart uploads without CORS middleware can still be triggered cross-origin by any third-party page even though the response body would be unreadable to that page.
