# Tasks: Classification-Band Coverage + Untrusted-Signer Parity

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~750-800 |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |
| Chain strategy | size-exception |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Fix generate.py drift + alias digests + manifest entries | PR 1 (single) | `python samples/generate.py --check` | `python samples/generate.py` regen diff review | samples/generate.py, samples/manifest.json |
| 2 | e2e band coverage (REVIEW_RECOMMENDED/HIGH_RISK/INCONCLUSIVE/SUSPICIOUS assertions) | PR 1 (single) | `pytest apps/api/tests/integration/test_analyze_endpoint_e2e.py -k classification` | e2e suite, mocked ports only | test_analyze_endpoint_e2e.py |
| 3 | Untrusted-signer unit parity | PR 1 (single) | `pytest apps/api/tests/unit -k untrusted_signer` | unit suite | test_domain_signals.py, test_assessment.py, test_scoring.py |

All three units ship in one PR (size:exception, per proposal's ~800-line Low-risk single-PR budget). Ask user to confirm size:exception before apply.

## Phase 1: generate.py Fix + Alias Digests

- [x] 1.1 RED: In `samples/generate.py::main`, run `--check`; confirm it currently fails once new ids are referenced (baseline, no code change yet — skip if not yet reproducible; proceed to fix).
- [x] 1.2 GREEN: Fix `_build_manifest()` — change `invalid_cbu_check_digit` expected_classification from `REVIEW_RECOMMENDED` to `SUSPICIOUS`.
- [x] 1.3 GREEN: In `generate()`, add alias digests: `digests["synthetic_band_review_recommended"] = digests["clean_valid_transfer"]`, `digests["synthetic_band_high_risk"] = digests["clean_valid_transfer"]`.
- [x] 1.4 GREEN: Add two `_build_manifest()` entries: `synthetic_band_review_recommended` (REVIEW_RECOMMENDED) and `synthetic_band_high_risk` (HIGH_RISK), reusing `clean_valid_transfer` path/sha256/declared_fields, each with explicit `notes` naming the shared bytes and its purpose.
- [x] 1.5 VERIFY: Run `python samples/generate.py --check` — passes with no drift; run `python samples/generate.py` and diff `samples/manifest.json` — no unintended changes.

## Phase 2: e2e Port Extension + Band Tests

- [x] 2.1 RED: Write failing test asserting `_FixtureNeutralPort` emits `ValidationSignal`s from a fixture's `expected_signals` for the `metadata` role (test should fail — port currently only sets status).
- [x] 2.2 GREEN: Add `_CATEGORY_ROLE` mapping and signal-construction logic to `_FixtureNeutralPort` (metadata/provenance/visual -> own role only; financial_consistency/data_quality emitted by no port). Build `ValidationSignal(SignalCode(e["code"]), SignalCategory(e["category"]), Severity(e["severity"]), Decimal(str(e.get("confidence","1.00"))), description fallback)`.
- [x] 2.3 VERIFY: Existing tests with empty `expected_signals` still pass unchanged (no signal emission regression).
- [x] 2.4 RED: Add assertion for `classification == "SUSPICIOUS"` and `ruleset_version == "2026-09-06"` to the existing invalid_cbu_check_digit e2e test — fails until Phase 1 fix + response wiring confirmed.
- [x] 2.5 GREEN: Confirm test passes post Phase 1 fix (no e2e code change expected beyond assertions).
- [x] 2.6 RED: New test `test_review_recommended_classification` using `synthetic_band_review_recommended` fixture — asserts classification `REVIEW_RECOMMENDED`, score `39`, ruleset `2026-09-06`. Fails pre-2.2.
- [x] 2.7 GREEN: Confirm passes after port extension (2.2).
- [x] 2.8 RED: New test `test_high_risk_classification` using `synthetic_band_high_risk` fixture — asserts classification `HIGH_RISK`, score `85`, ruleset `2026-09-06`.
- [x] 2.9 GREEN: Confirm passes after port extension.
- [x] 2.10 RED: New test `test_inconclusive_classification` using `dataclasses.replace(load_fixture("clean_valid_transfer"), expected_analyzer_statuses={"ocr":"failed","metadata":"failed","provenance":"failed","vision":"completed"})` — asserts classification `INCONCLUSIVE` (coverage 0.15 < 0.35).
- [x] 2.11 GREEN: Confirm passes with existing coverage-gate logic (no production code change).

## Phase 3: Untrusted-Signer Unit Parity

- [x] 3.1 RED: In `apps/api/tests/unit/test_domain_signals.py`, add `AI_GENERATED_CLAIM_UNTRUSTED_SIGNER` test(s) mirroring every `VALID_AI_GENERATED_CLAIM` case 1:1 — fails (no coverage yet).
- [x] 3.2 GREEN: Confirm assertions pass against existing domain signal behavior (no production change expected).
- [x] 3.3 RED: In `apps/api/tests/unit/test_assessment.py`, add `RULESET_2026_09_06` import and mirrored `AI_GENERATED_CLAIM_UNTRUSTED_SIGNER` severity/action-mapping test(s) paralleling `VALID_AI_GENERATED_CLAIM`.
- [x] 3.4 GREEN: Confirm passes (RULESET_2026_09_04 has no entry for this signal — must use 2026_09_06).
- [x] 3.5 RED: In `apps/api/tests/unit/test_scoring.py`, add `RULESET_2026_09_06` import and mirrored scoring-floor test(s) for `AI_GENERATED_CLAIM_UNTRUSTED_SIGNER` (critical floor, confidence 0.85 -> int(50*2.0*0.85)=85).
- [x] 3.6 GREEN: Confirm passes.
- [x] 3.7 VERIFY: Full suite green (`pytest apps/api/tests`); no file under `apps/api/src/` modified; `python samples/generate.py --check` still passes.
