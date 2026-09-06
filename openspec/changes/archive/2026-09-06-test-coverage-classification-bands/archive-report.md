# Archive Report: test-coverage-classification-bands

**Date**: 2026-09-06
**Status**: CLOSED — All 23 implementation tasks complete, verification PASS, change archived.

## Executive Summary

Closed two confirmed test-coverage gaps found during the 2026-09-06 docs/scoring audit:

1. End-to-end coverage for classification bands SUSPICIOUS, REVIEW_RECOMMENDED, HIGH_RISK,
   and INCONCLUSIVE (only LOW_RISK had a real e2e assertion before this change).
2. Unit-test parity for `SignalCode.AI_GENERATED_CLAIM_UNTRUSTED_SIGNER` across
   `test_domain_signals.py`, `test_assessment.py`, and `test_scoring.py`, mirroring its
   sibling `VALID_AI_GENERATED_CLAIM`.

Also fixed a live drift bug in `samples/generate.py::_build_manifest()` (hardcoded
`REVIEW_RECOMMENDED` for `invalid_cbu_check_digit`, contradicting the committed
`manifest.json`'s `SUSPICIOUS`, which `--check` could not catch since it only hashes
image bytes).

Real EXIF injection / signed C2PA manifest embedding was explicitly evaluated and
rejected for this change (see proposal.md "Out of Scope"): a self-signed certificate
can only ever reach the already-covered `untrusted-signer` tier, never
`VALID_AI_GENERATED_CLAIM`, and signed C2PA output is not reproducible across SDK
versions, conflicting with `generate.py`'s byte-determinism invariant.

## Task Completeness

All 23 tasks across 3 phases in `tasks.md` are checked `[x]`, independently confirmed
against source (not the apply agent's self-report) during verification.

## Verification

**Verdict: PASS** (0 CRITICAL, 0 WARNING, 0 SUGGESTION)

- `uv run pytest -q` (apps/api): 229 passed, 14 skipped, 0 failed.
- `python samples/generate.py --check`: passes.
- `git diff --stat`: 6 files, 417 insertions(+), 2 deletions(-).
- No file under `apps/api/src/` touched (verification-only constraint upheld).
- Score arithmetic independently verified against `RULESET_2026_09_06`:
  REVIEW_RECOMMENDED=39, HIGH_RISK=85 (= critical_floor), SUSPICIOUS=60.
- `_FixtureNeutralPort` signal emission confirmed category-routed (metadata/provenance/
  vision only; never `financial_consistency`/`data_quality`, never broadcast).

## Capabilities

None new, none modified. Verification-only change — no `openspec/specs/` deltas.

## Delivered Files

| File | Change |
|------|--------|
| `apps/api/tests/integration/test_analyze_endpoint_e2e.py` | Category-routed signal emission in `_FixtureNeutralPort`; classification/ruleset assertions; 3 new band tests |
| `apps/api/tests/unit/test_domain_signals.py` | Untrusted-signer severity/shape mirror |
| `apps/api/tests/unit/test_assessment.py` | `RULESET_2026_09_06` import + action-mapping mirror |
| `apps/api/tests/unit/test_scoring.py` | `RULESET_2026_09_06` import + critical-floor/no-floor-under-04/OCR-zero mirrors |
| `samples/generate.py` | Classification drift fix; alias-digest registration for 2 new fixture ids |
| `samples/manifest.json` | 2 new fixture entries reusing existing image bytes |

## Delivery

- Issue: #51 (`type:chore`, `area:api`, `status:approved`)
- Branch: `test/classification-band-coverage`
- PR: against `dev`
