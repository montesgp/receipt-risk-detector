# Verify Report: generic-receipt-field-extraction

**Mode**: openspec (hybrid: Engram + file)
**Pass**: RE-VERIFY (2nd pass, after Batch 2 CRITICAL fix)
**Verdict**: PASS

## Completeness

All 26 checkable tasks in Phases 1-7 (unchanged from the prior verify pass) plus the new Phase 8 (8.1-8.3, "Batch 2 -- CRITICAL fix from sdd-verify") are marked done in tasks.md. Phase 8 claims were independently cross-checked against source and test runs (see below) and are accurate: the regex change is present exactly as described, the 3 new tests exist and pass, and the full suite + ruff were genuinely re-run clean.

## Test / Build Evidence (independently re-run, not trusted from apply report)

| Command | Result |
|---|---|
| uv run --project apps/api pytest apps/api/tests -v | 189 passed, 14 skipped, 1 warning (skips are the same pre-existing model-dir-gated integration tests, unrelated to this change) |
| uv run --project apps/api ruff check apps/api | All checks passed |
| uv run --project apps/api pytest apps/api/tests/unit/test_ocr_field_parsers.py -v | 41 passed (37 from batch 1 + 3 new batch-2 date-shape-gate tests), including test_scan_date_candidates_wide_format_coverage_same_instant (all 3 original tested date variants, unchanged) |
| uv run --project apps/api pytest apps/api/tests/unit/test_financial_validation_fixture.py -k invalid_cbu | 1 passed -- test_invalid_cbu_fixture_produces_expected_signal still fires INVALID_CBU_CHECK_DIGIT unchanged |

Test count delta: 186 -> 189 passed (+3), matching exactly the 3 new tests the apply report claims to have added (test_has_date_shape_accepts_year_glued_to_trailing_connector_text, test_scan_date_candidates_parses_year_glued_to_connector_text, test_extract_core_fields_real_mercado_pago_ocr_text_extracts_all_four_fields). No regressions anywhere else.

## Independent Re-Verification of the CRITICAL Finding

Prior CRITICAL: _has_date_shape's year regex (\b\d{4}\b) failed to match a year glued to trailing alphabetic OCR-dropped-space text ("2026alas20:53."), so _scan_date_candidates skipped the box and date_time was never extracted from the literal Mercado Pago OCR text ("$ 8.000", "CUIT/CUIL:20-34240499-6", "CVU:0000003100094065748023", "30/ag0sto/2026alas20:53.") -- only 3/4 core fields.

Code check: Read apps/api/src/receipt_risk/adapters/ocr/field_parsers.py directly. _FOUR_DIGIT_YEAR_RE is now defined as:

    _FOUR_DIGIT_YEAR_RE = re.compile(r"(?<!\d)\d{4}(?!\d)")

with an inline comment documenting the root cause and the digit-adjacency rationale. This matches the apply report's claim exactly (not just trusted from the report -- read the live source).

Independent reconstruction (own script, not the apply/test file's exact code, built directly against boxes_from_engine_output + extract_core_fields using the same literal raw OCR text and box geometry pattern the original verify pass used):

    field count: 4 names: {amount, date_time, cuit, destination_cbu} == core: {amount, date_time, cuit, destination_cbu}
    amount -> ($ 8.000, 8000)
    destination_cbu -> (0000003100094065748023, 0000003100094065748023)
    cuit -> (20-34240499-6, 20342404996)
    date_time -> (30/ag0sto/2026alas20:53., 2026-08-30T20:53:00)

All 4/4 core fields extract with normalized populated, date_time correctly resolves to 2026-08-30 20:53:00. The CRITICAL is genuinely resolved -- verified independently, not by trusting the apply report's claim.

Adversarial false-positive check (own script, isolated regex testing): tested the new (?<!\d)\d{4}(?!\d) pattern against digit runs glued to letters on both sides, simulating a CUIT/CBU digit run immediately adjacent to non-digit text:

    CUIT20342404996fin           -> None   (11-digit CUIT run, no false 4-digit slice)
    CVU0000003100094065748023fin -> None   (22-digit CBU run, no false 4-digit slice)
    abc20342404996                -> None
    N20342404996                  -> None
    2026glued / glued2026          -> 2026   (correctly matches a real glued year)

Reasoning confirmed: within any contiguous digit run longer than 4 (e.g. an 11-digit CUIT or 22-digit CBU), every interior or edge 4-digit substring still has a digit neighbor immediately before or after it inside the run, so (?<!\d) / (?!\d) never both succeed simultaneously except at the true edges of a run whose total length is exactly 4. Since CUIT (11) and CBU (22) runs are never 4 digits long, the original false-positive guard the \b boundary was presumably protecting (never slicing a spurious "year" out of a longer identifier run) is fully preserved by the new lookaround-only regex, while the letter-adjacency false-negative (the actual defect) is fixed. No new false-positive risk introduced.

## Spec Scenario Compliance Matrix (delta from prior pass)

| Scenario | Prior Verdict | Current Verdict | Evidence |
|---|---|---|---|
| Wide date/time format coverage including an OCR-typo month name | FAIL | PASS | test_scan_date_candidates_wide_format_coverage_same_instant (4 original variants, unchanged, still passing) + the new end-to-end real-OCR-text test, both independently re-run |

All other 7 scenarios from the prior pass remain PASS (unchanged code paths in batch 2; re-confirmed by the full-suite green run and by git-status scope below).

## Re-confirmation of Prior WARNING and SUGGESTIONs

Batch 2 touched only field_parsers.py, test_ocr_field_parsers.py, and tasks.md (confirmed via git status --short -- samples/generate.py/samples/manifest.json are unchanged since the prior pass, still showing the same batch-1 modifications). Therefore:

- WARNING 1 (ORIGIN_CBU/ORIGIN_CUIT are static string literals in samples/generate.py, guarded by a separate runtime test rather than computed inline at generation time) -- still accurate, unchanged. Not touched by batch 2. Remains a non-functional documentation-wording nitpick; the guard test (test_origin_identifiers_checksum_valid.py) still exists and still passes as part of the 189.
- SUGGESTION 1 (add a regression test using glued-text date sample) -- RESOLVED. This is exactly what batch 2 added (test_scan_date_candidates_parses_year_glued_to_connector_text and the end-to-end real-OCR test). No longer an open suggestion; recorded here as closed rather than carried forward.
- SUGGESTION 2 (loosen _has_date_shape's four-digit-year detection to tolerate a glued year) -- RESOLVED. This is precisely the fix implemented in batch 2. No longer open.

## Design Coherence

Design decisions map to code faithfully across all areas, including batch 2. The regex fix is a narrow, targeted change to a single named constant with no ripple into _try_parse_date, _to_english_date_text, _repair_month_tokens, or _select_date (confirmed by reading the surrounding code -- those functions are byte-for-byte unchanged from the prior pass's already-verified state). This matches the apply report's stated scope exactly.

## Tasks.md Phase 8 Addendum Accuracy

Phase 8 (8.1-8.3) is present in tasks.md and accurately reflects what was actually done:
- 8.1 (RED, 3 new tests added and confirmed failing pre-fix) -- accurate; the 3 named tests exist in the test file and pass now.
- 8.2 (GREEN, regex change with root-cause rationale) -- accurate; matches the live source exactly, including the inline comment's reasoning.
- 8.3 (full suite + ruff re-run clean, no regressions in the other 3 date scenarios or invalid_cbu_check_digit) -- accurate; independently re-confirmed above with fresh command runs, not trusted from the claim.

## Issues

### CRITICAL

None. The previously blocking finding is resolved and independently re-verified against the exact literal production OCR text.

### WARNING

1. (Carried forward, unchanged, non-functional) samples/generate.py's ORIGIN_CBU/ORIGIN_CUIT are static string literals; checksum validity is enforced by a separate guard test (test_origin_identifiers_checksum_valid.py), not computed inline in the generator itself. Not a defect -- the guard test does its job and runs as part of the passing suite -- but the apply report's original phrasing ("computed, not hand-typed") describes how the values were derived offline, not what generate.py does at runtime. No action required to archive.

### SUGGESTION

None outstanding -- both prior suggestions were resolved by the batch-2 fix itself (see above).

## Final Verdict: PASS

CRITICAL: 0, WARNING: 1 (carried forward, non-functional, does not block archive), SUGGESTION: 0. The change now meets its own stated acceptance bar (4/4 core fields extracted, date_time correctly normalized, from the literal production Mercado Pago OCR text), with no regressions in the full 189-test suite or ruff check. Ready to route to sdd-archive.

## Key Learnings

1. _FOUR_DIGIT_YEAR_RE was changed from \b\d{4}\b to (?<!\d)\d{4}(?!\d) in apps/api/src/receipt_risk/adapters/ocr/field_parsers.py (~line 337), and this single targeted change fully resolves the prior CRITICAL finding -- independently reconstructed against the exact literal production OCR text and confirmed 4/4 core fields extract with normalized populated.
2. The digit-adjacency lookaround preserves the original false-positive guard against slicing a spurious 4-digit "year" out of a longer CUIT/CBU digit run, because any interior or edge 4-digit substring inside an 11- or 22-digit run still has a digit neighbor on at least one side; adversarial testing against letter-glued 11- and 22-digit runs confirms no new false-positive match is introduced.
3. Test count increased from 186 to 189 passed (14 skipped unchanged, same pre-existing model-dir-gated integration tests), exactly matching the 3 new regression tests the apply report claims to have added for this fix.
4. Batch 2 touched only field_parsers.py, test_ocr_field_parsers.py, and tasks.md -- confirmed via git status --short that samples/generate.py/samples/manifest.json are unchanged since the prior verify pass, so the prior WARNING about ORIGIN_CBU/ORIGIN_CUIT being static literals remains accurate and unaffected by this fix.
5. Both prior SUGGESTIONs (add a glued-text regression test; loosen the four-digit-year shape gate) are resolved by the batch-2 fix itself and are recorded here as closed rather than carried forward as open items.
