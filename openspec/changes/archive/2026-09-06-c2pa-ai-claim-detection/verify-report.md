# Verify Report: c2pa-ai-claim-detection

## Verdict: CLEAN
0 CRITICAL, 0 WARNING, 0 SUGGESTION.

## Test Run
`uv run pytest -q` from `apps/api/` — exit code **0**. Summary line was not
printed by pytest in this Windows/Git-Bash environment (a quirk, not a
failure); progress markers were parsed directly (ANSI-stripped, character
counted): **207 passed, 14 skipped, 0 failed, 0 errors**.

## Checks Performed (independent source read, not trusting apply-progress)

1. **`c2pa_reader.py` dual-path parsing** — `_iter_source_types` reads both
   the flat `Iptc4xmpExt:DigitalSourceType` field and the nested
   `assertions[].data.actions[].digitalSourceType` (claim-v2) shape, both
   lowercased, both `isinstance`-guarded. `compositesynthetic` present in
   `_ALGORITHMIC_SOURCE_MARKERS`. Confirmed.
2. **3-way validation_status branch** — empty → `VALID_AI_GENERATED_CLAIM`;
   `_is_ca_trust_only` true (only `signingCredential.untrusted`) →
   `AI_GENERATED_CLAIM_UNTRUSTED_SIGNER`; anything else (including
   `signingCredential.expired`, or untrusted mixed with a hash mismatch) →
   `PROVENANCE_VALIDATION_FAILED`. Confirmed.
3. **`signals.py`** — `AI_GENERATED_CLAIM_UNTRUSTED_SIGNER` appended as the
   final `SignalCode` member, correctly commented, not inserted next to
   `VALID_AI_GENERATED_CLAIM`. Confirmed.
4. **`v2026_09_06.py` copy-forward** — direct diff against `v2026_09_05.py`
   confirms severity multipliers, combination floors, analyzer evidence
   weights, status quality, bands, and coverage threshold are byte-for-value
   identical; only delta is the new `_WEIGHTS`/`_CRITICAL_FLOOR` entries
   (weight 50, floor 85). `v2026_09_05.py` confirmed NOT modified (absent
   from `git status --short`'s modified-file list; only `v2026_09_06.py` is
   new/untracked).
5. **`rulesets/__init__.py`** — 4 rulesets registered (09_01, 09_04, 09_05,
   09_06), append-only, alphabetical-by-date. Confirmed.
6. **`bootstrap/app.py`** — all 3 wiring sites (import, use-case
   `ruleset=`, `/version` endpoint `ruleset_version=`) repointed to
   `RULESET_2026_09_06`. Confirmed.
7. **`analyze_receipt.py`** — `ENGINE_VERSION == "0.3.0"`, docstring
   replaced (not appended), matching the prior `0.1.0 -> 0.2.0` precedent
   shape. Confirmed.
8. **Arithmetic** — `int(50 * 2.0 * 0.85) == 85`. `v2026_09_06._BANDS`:
   `(24, LOW_RISK), (49, REVIEW_RECOMMENDED), (74, SUSPICIOUS), (100,
   HIGH_RISK)`. 85 > 74 → the new signal alone forces `HIGH_RISK`, matching
   the proposal's closed decision and the delta spec's scenario. Confirmed.
9. **Main spec untouched** — `openspec/specs/receipt-analysis/spec.md`
   absent from `git status --short`; a grep for `DigitalSourceType` in that
   file returns no matches. Consistent with "merges at archive time only".
   Confirmed.
10. **Two flagged apply-progress deviations** — both sound, neither masks a
    regression:
    - `test_ruleset_declares_weights_for_every_defined_signal_code`
      retargeted from `RULESET_2026_09_04` to `RULESET_2026_09_06`: correct,
      since the new `SignalCode` is genuinely new and only the
      latest/active ruleset is expected to price every defined code; a
      companion assertion in the same file explicitly pins that
      `RULESET_2026_09_05` does **not** define the new code.
    - `test_analyze_endpoint_e2e.py` switched from `RULESET_2026_09_05` to
      `RULESET_2026_09_06`: sound, uses dynamic imports/attributes (not
      hardcoded literals), now matches actual production wiring; no
      pre-existing weight assertion was weakened.

## Out-of-Scope Observations (not defects of this change)
`README.md` and a new `docker-compose.yml` carry unrelated local-dev-tooling
edits (exiftool/Docker guidance) that predate/are outside this change's
tasks and proposal. Left untouched by this verify pass.

## Tasks vs Code State
All 20 tasks in `tasks.md` are marked `[x]` and match the verified code
state across all 4 phases (domain foundation, adapter, wiring, golden
regeneration/docs).
