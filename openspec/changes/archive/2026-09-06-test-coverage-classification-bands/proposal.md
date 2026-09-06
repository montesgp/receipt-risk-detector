# Proposal: Classification-Band Coverage + Untrusted-Signer Parity

## Intent

Three confirmed gaps let real regressions ship silently:

1. **Classification bands are unverified end-to-end.** `test_analyze_endpoint_e2e.py` never asserts `body["classification"]`. REVIEW_RECOMMENDED, HIGH_RISK and INCONCLUSIVE have no e2e test at all — the router → use-case → scoring → response band wiring is untested, so a band-boundary or serialization regression would ship green.
2. **`SignalCode.AI_GENERATED_CLAIM_UNTRUSTED_SIGNER` has partial coverage.** It has emission coverage in `test_c2pa_reader.py` but no severity, action-mapping or scoring-floor tests, unlike its twin `VALID_AI_GENERATED_CLAIM`. The two signals were added together and are expected to behave as a pair; only one of them is pinned.
3. **Live drift bug.** `samples/generate.py::_build_manifest()` hardcodes `expected_classification: "REVIEW_RECOMMENDED"` for `invalid_cbu_check_digit` while the committed `manifest.json` says `"SUSPICIOUS"`. `--check` only hashes image bytes, so it cannot catch metadata drift. Anyone regenerating samples silently rewrites the expectation.

Success looks like: every classification band the API can return has an e2e test that asserts it, the untrusted-signer signal is pinned exactly like its twin, and regenerating samples reproduces the committed manifest.

## Scope

### In Scope

- Assert `classification` and `ruleset_version == "2026-09-06"` in the existing SUSPICIOUS e2e test.
- Extend `_FixtureNeutralPort` to emit `ValidationSignal`s from `fixture.expected_signals` (today it sets only `status`).
- New `samples/manifest.json` entries reusing committed image bytes under new ids (same `path` + same `sha256`, explicit `notes` explaining the reuse) to drive REVIEW_RECOMMENDED and HIGH_RISK.
- INCONCLUSIVE e2e test driven purely by `expected_analyzer_statuses` (evidence coverage < 0.35) — no new fixture needed.
- Fix the `generate.py` `_build_manifest()` classification drift, in this same PR.
- Mirror `VALID_AI_GENERATED_CLAIM`'s tests 1:1 for `AI_GENERATED_CLAIM_UNTRUSTED_SIGNER` in `test_domain_signals.py`, `test_assessment.py` and `test_scoring.py` (the latter two need a `RULESET_2026_09_06` import).

### Out of Scope

- **Real EXIF injection in `samples/generate.py`.** Deferred on research findings, not on size alone. Pillow-only EXIF writing is feasible and deterministic, but it only pays off as part of the real-provenance fixture track below, and that track is blocked. Keeping it out preserves this change as a pure verification slice.
- **Real signed C2PA manifest embedding in `samples/generate.py`.** Deferred on concrete research findings:
  - A self-signed cert **cannot** reach `VALID_AI_GENERATED_CLAIM`. An empty `validation_status` requires a cert chained to an anchor in the C2PA SDK's default trust list; self-signing always yields `signingCredential.untrusted`. Injecting a test trust anchor would mean changing production reader configuration.
  - Therefore the only reachable real signal is `AI_GENERATED_CLAIM_UNTRUSTED_SIGNER`, which existing mock-level tests already cover — the marginal coverage gain is small.
  - Signed C2PA output is **not byte-reproducible** (SDK version, COSE serialization, `instanceID`), which breaks `generate.py`'s byte-determinism invariant and forces a `--check` split into deterministic-sha256 vs. structural verification.
  - It requires a **committed test-only private key**, with secret-scanner allowlisting and a new dependency surface for the samples toolchain.

  Any future proposal for this must scope it as **untrusted-signer-only fixture support** and explicitly address the determinism carve-out and the `--check` split as first-class design decisions, not incidental details.
- Non-mocked, real-adapter e2e tests through the HTTP router.
- CLI overrides for arbitrary declared receipt fields.
- Any production code, ruleset, or scoring change. No file under `apps/api/src/` is touched.

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- None — verification only. No requirement changes, no `openspec/specs/` deltas. (Confirmed with the user.)

## Approach

Extend the sanctioned mocked-port pattern rather than introducing real bytes.

`_FixtureOcrPort`/`_FixtureNeutralPort` already inject fixture-derived data into `AnalyzerResult`. `AnalyzeReceiptUseCase` chains `result.signals` verbatim into scoring, so once the neutral port emits the signals declared in `fixture.expected_signals`, every classification band becomes reachable from manifest metadata alone — no new image bytes, no new tooling, no new dependencies.

The two new manifest entries deliberately reuse committed image files: the images are irrelevant to band selection here, and reusing them keeps `--check` and `test_manifest_integrity.py` unchanged. Each reuse entry carries an explicit `notes` field, plus a comment in the e2e file, so a future reader is not confused by two ids sharing one `sha256`.

The `generate.py` drift fix rides along because it is a one-line correction to the same manifest surface the new entries touch; splitting it would leave a known-wrong value in the tree for no benefit.

The untrusted-signer parity work is a mechanical mirror of the existing `VALID_AI_GENERATED_CLAIM` tests — same three files, same assertions, adjusted expectations.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `apps/api/tests/integration/test_analyze_endpoint_e2e.py` | Modified | Classification + ruleset assertions; `_FixtureNeutralPort` signal emission; 3 new band tests |
| `samples/manifest.json` | Modified | 2 reuse entries (REVIEW_RECOMMENDED, HIGH_RISK) with explicit `notes` |
| `samples/generate.py` | Modified | `_build_manifest()` classification drift fix |
| `apps/api/tests/unit/domain/test_domain_signals.py` | Modified | Untrusted-signer severity/metadata parity |
| `apps/api/tests/unit/domain/test_assessment.py` | Modified | Untrusted-signer action mapping (+ `RULESET_2026_09_06` import) |
| `apps/api/tests/unit/domain/test_scoring.py` | Modified | Untrusted-signer scoring floor (+ `RULESET_2026_09_06` import) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Two fixture ids sharing one `path`/`sha256` confuses future readers | Med | Explicit `notes` per manifest entry plus a comment in the e2e file |
| `generate.py` classification fix is unverifiable via `--check` (it hashes image bytes only) | Med | Manual diff of the regenerated `manifest.json` against committed bytes during review |
| Extending `_FixtureNeutralPort` alters behavior of existing tests that rely on it emitting no signals | Low | Only emit when `expected_signals` is non-empty; run the full suite |
| Mocked ports mean band coverage does not prove real-adapter behavior | Low (accepted) | Explicitly accepted: this slice verifies the wiring, not the adapters; real-adapter coverage stays a separate future proposal |

## Rollback Plan

Revert the commit. This change touches tests and sample fixture metadata only — no production code, no API surface, no dependencies, no CI configuration. There is no deploy-time rollback path because nothing deployable changes.

## Dependencies

None. No new packages, no new binaries, no CI changes. Uses the existing Pillow-only `generate.py` and the existing test toolchain.

## Success Criteria

- [ ] E2E tests assert `classification` for SUSPICIOUS, REVIEW_RECOMMENDED, HIGH_RISK and INCONCLUSIVE.
- [ ] Each new e2e test asserts `ruleset_version == "2026-09-06"`.
- [ ] `python samples/generate.py` reproduces the committed `manifest.json` with no classification drift.
- [ ] `AI_GENERATED_CLAIM_UNTRUSTED_SIGNER` has parity with `VALID_AI_GENERATED_CLAIM` across `test_domain_signals.py`, `test_assessment.py` and `test_scoring.py`.
- [ ] `--check` still passes for all fixtures.
- [ ] Full existing suite stays green; no file under `apps/api/src/` is modified.

## Delivery Forecast

**Risk level: Low.** Tests and fixture metadata only; no production code, no dependencies, no CI changes, clean single-commit revert.

**Review budget: ~800 lines.**

**400-line budget risk: Medium. Chained PRs recommended: No. Delivery strategy: single PR.**

## Resolved Decisions

1. **Fixture reuse with a shared `sha256`** for the REVIEW_RECOMMENDED and HIGH_RISK entries is acceptable — confirmed by the user; mitigated with explicit `notes`.
2. **No `openspec/specs/` deltas** — this change adds no requirements and modifies none; confirmed by the user.
3. **The `generate.py` drift fix ships in this same PR** rather than as a separate change — confirmed by the user.
4. **INCONCLUSIVE needs no new fixture** — it is reachable purely through `expected_analyzer_statuses` driving evidence coverage below 0.35.
