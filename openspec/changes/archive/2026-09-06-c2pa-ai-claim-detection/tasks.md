# Tasks: C2PA AI-Claim Detection — claim-v2 parsing + untrusted-signer tier

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 400-550 (adapter+domain ~180-220; new ruleset file ~100 additive; test fixtures ~180; golden version-string sweep across 7 modules ~20; docs ~4) |
| Session review budget (cached) | 800 lines |
| 400-line budget risk | Low (estimate sits within the session's cached 800-line budget; would be Medium against the skill's generic 400-line default) |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Whole change: dual-path parsing, untrusted-signer tier, new ruleset, wiring, tests, docs | PR 1 | `uv run pytest apps/api/tests/unit/test_c2pa_reader.py apps/api/tests/unit/test_ruleset.py apps/api/tests/unit/test_bootstrap_app.py -q` | N/A — pure domain/adapter unit logic, no external service; manifest fixtures are inline dicts | Revert commit; repointing `bootstrap/app.py`'s 3 sites to `RULESET_2026_09_05` alone is a safe partial rollback (adapter fix stays retroactive per design) |

Estimate is within the cached 800-line budget, so no chaining or exception is required before `sdd-apply`.

## Phase 1: Domain Foundation

- [x] 1.1 `domain/signals.py`: append `AI_GENERATED_CLAIM_UNTRUSTED_SIGNER` as the new trailing member of `SignalCode`, after the `visual-anomaly-detection` group, with the `c2pa-ai-claim-detection` group comment (category PROVENANCE, CRITICAL, confidence 0.85, critical_floor 85) — do not insert next to `VALID_AI_GENERATED_CLAIM`.
- [x] 1.2 RED: `tests/unit/test_ruleset.py` — assert `len(RULESETS) == 4`; `RULESET_2026_09_06.version == "2026-09-06"`; `RULESET_2026_09_06.weights[SignalCode.AI_GENERATED_CLAIM_UNTRUSTED_SIGNER] == 50` and `critical_floor[...] == 85`; `RULESET_2026_09_05` still exposes its original weights/floors unchanged (frozen-forward guard).
- [x] 1.3 GREEN: create `domain/rulesets/v2026_09_06.py` — byte-for-value copy-forward of `v2026_09_05` (all weights, severity multipliers, combination floors, analyzer evidence weights, status quality, bands, `inconclusive_coverage_threshold`) plus the two new `AI_GENERATED_CLAIM_UNTRUSTED_SIGNER` entries (`_WEIGHTS`, `_CRITICAL_FLOOR`); docstring mirrors `v2026_09_05.py`'s structure; export `RULESET_2026_09_06`, `version="2026-09-06"`. `v2026_09_05.py` stays untouched.
- [x] 1.4 GREEN: `domain/rulesets/__init__.py` — import and register `RULESET_2026_09_06` as the 4th entry in `RULESETS` (append-only, alphabetical-by-date order preserved).

## Phase 2: Adapter Parsing + Classification

- [x] 2.1 RED: `tests/unit/test_c2pa_reader.py` — new test: claim-v2 manifest with `digitalSourceType` only inside `assertions[].data.actions[].digitalSourceType` (nested, `trainedAlgorithmicMedia`), empty `validation_status` → `_derive_signals` returns exactly `VALID_AI_GENERATED_CLAIM`, `Severity.CRITICAL`.
- [x] 2.2 RED: `tests/unit/test_c2pa_reader.py` — new test: same claim-v2 shape with `validation_status == [{"code": "signingCredential.untrusted", ...}]` → `AI_GENERATED_CLAIM_UNTRUSTED_SIGNER`, `Severity.CRITICAL`, `SignalCategory.PROVENANCE`, `confidence == Decimal("0.85")` (add `from decimal import Decimal` to test imports).
- [x] 2.3 RED: `tests/unit/test_c2pa_reader.py` — new test: `validation_status` mixing `signingCredential.untrusted` with `assertion.dataHash.mismatch` → `PROVENANCE_VALIDATION_FAILED` (pins worst-case precedence).
- [x] 2.4 RED: `tests/unit/test_c2pa_reader.py` — new test: `validation_status` with only `signingCredential.expired` → `PROVENANCE_VALIDATION_FAILED` (pins fail-closed allowlist and the deliberate non-inclusion of `expired`).
- [x] 2.5 GREEN: `c2pa_reader.py` — add `"compositesynthetic"` to `_ALGORITHMIC_SOURCE_MARKERS`; add frozen `_CA_TRUST_ONLY_STATUS_CODES: Final[frozenset[str]] = frozenset({"signingCredential.untrusted"})` module constant with rationale comment.
- [x] 2.6 GREEN: `c2pa_reader.py` — add `_iter_source_types(manifest_entry)` generator yielding lowercased values from both the flat `Iptc4xmpExt:DigitalSourceType` field and nested `assertions[].data.actions[].digitalSourceType`, with `isinstance` guards for malformed `data`/`actions`/`action`; rewrite `_has_algorithmic_source_claim` over it (signature unchanged); add `Iterator` to the `collections.abc` imports.
- [x] 2.7 GREEN: `c2pa_reader.py` — add `_is_ca_trust_only(validation_status)` predicate: `True` only when every dict entry's `code` is in `_CA_TRUST_ONLY_STATUS_CODES` AND at least one dict entry exists.
- [x] 2.8 GREEN: `c2pa_reader.py::_derive_signals` — extend the tail to a three-way branch: empty `validation_status` → `VALID_AI_GENERATED_CLAIM` (unchanged); `_is_ca_trust_only(...)` → new `AI_GENERATED_CLAIM_UNTRUSTED_SIGNER` signal (evidence: `active_manifest`, comma-joined `validation_status_codes`); else → `PROVENANCE_VALIDATION_FAILED` (unchanged). Update the module docstring to describe the three-way tier and the allowlist decision.
- [x] 2.9 Verify: run the 5 pre-existing `test_c2pa_reader.py` tests unchanged and green (flat-field regression guard on "additive, not replacement").

## Phase 3: Engine/Ruleset Wiring

- [x] 3.1 GREEN: `application/analyze_receipt.py` — bump `ENGINE_VERSION = "0.2.0"` → `"0.3.0"` at line 40; replace the rationale docstring (lines 41-45) per design, citing the claim-v2 parsing fix and validation_status allowlist as unconditional shared-adapter detection corrections.
- [x] 3.2 GREEN: `bootstrap/app.py` — repoint all 3 sites from `RULESET_2026_09_05` to `RULESET_2026_09_06`: import (line ~34), use-case construction `ruleset=` (line ~85), `/version` endpoint `ruleset_version=` (line ~118).
- [x] 3.3 RED/GREEN: `tests/unit/test_bootstrap_app.py` — assert the active ruleset is `RULESET_2026_09_06`.

## Phase 4: Golden Regeneration and Docs

- [x] 4.1 Hand-recompute (never copy from a failing run) and update the two version-string literals (`engine_version` → `"0.3.0"`, `ruleset_version` → `"2026-09-06"`) across: `tests/unit/test_assessment.py`, `tests/unit/test_analyze_receipt.py`, `tests/unit/test_api_schemas.py`, `tests/unit/test_api_error_contract.py`, `tests/unit/test_router.py`, `tests/unit/test_log_privacy.py`, `tests/integration/test_analyze_endpoint_e2e.py`. Weights for all pre-existing codes are unchanged — any `risk_score`/`confidence_score` that shifts is a bug to investigate, not a value to "fix" by regenerating.
- [x] 4.2 Run full suite: `uv run pytest -q` (API) — confirm all green, and diff each touched golden file to confirm only the two version strings moved.
- [x] 4.3 GREEN: `docs/API.md` — update `"engine_version": "0.2.0"` → `"0.3.0"` and `"ruleset_version": "2026-09-05"` → `"2026-09-06"` in both the `/version` and analyze-response examples (lines ~29-30, ~65-66).
- [x] 4.4 Confirm `openspec/specs/receipt-analysis/spec.md` (main spec) is NOT edited by this change — the delta spec at `openspec/changes/c2pa-ai-claim-detection/specs/receipt-analysis/spec.md` merges at archive time only, per repo convention.

## Key Learnings

1. Claim-v2 C2PA manifests nest `digitalSourceType` inside `assertions[].data.actions[].digitalSourceType` rather than the flat IPTC field the adapter originally read.
2. A fail-closed allowlist for `validation_status` codes must default unknown codes to the stricter bucket rather than the lenient one, to avoid fading real tamper signals.
3. Detection/parsing corrections applied unconditionally across all rulesets are tracked by `ENGINE_VERSION`, while priced policy changes are tracked by a new frozen `ruleset_version`.
4. The new ruleset file is a byte-for-value copy-forward of the prior frozen ruleset plus exactly the new code's weight and floor entries, keeping historical replay reproducible.
5. This change's estimated diff size fits inside the session's cached 800-line review budget, so no chained-PR decision is required before `sdd-apply`.
