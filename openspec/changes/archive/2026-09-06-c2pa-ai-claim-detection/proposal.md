# Proposal: C2PA AI-Claim Detection — claim-v2 parsing + untrusted-signer tier

## Intent

Two confirmed defects in `adapters/provenance/c2pa_reader.py`, verified against a real Google Gemini manifest (`claim_version: 2`):

1. `_has_algorithmic_source_claim` reads only the flat `data["Iptc4xmpExt:DigitalSourceType"]`. Real claim-v2 producers nest `digitalSourceType` inside `c2pa.actions.v2` → `data.actions[]`. A genuine AI-generation claim is silently missed — no signal at all.
2. `_derive_signals` maps ANY non-empty `validation_status` to `PROVENANCE_VALIDATION_FAILED` (MEDIUM, 0.60). The real manifest carried only `signingCredential.untrusted` while `validation_state: "Valid"` and every cryptographic check passed. An unrecognized signing CA is being scored like tampering.

## Scope

### In Scope
- Dual-path parsing: keep the flat field, add `assertions[].data.actions[].digitalSourceType`.
- Add `compositesynthetic` to `_ALGORITHMIC_SOURCE_MARKERS`.
- New `SignalCode.AI_GENERATED_CLAIM_UNTRUSTED_SIGNER` (PROVENANCE, CRITICAL, confidence 0.85, `critical_floor` 85 — forces HIGH_RISK, same as the fully-trusted case).
- Allowlist split of `validation_status` codes; new ruleset `v2026_09_06`; `ENGINE_VERSION` 0.2.0 → 0.3.0.
- Unit fixtures for claim-v2 nested actions and untrusted-signer-only status; docs/API.md version examples.

### Out of Scope
- A generic cross-vendor AI-watermark detector. This is C2PA-only — C2PA is the standard Google/OpenAI/Adobe converged on.
- Proprietary invisible pixel/statistical watermarks (SynthID and peers): no generic public detector exists.
- Custom C2PA trust anchors. "AI claim from an unrecognized CA" is a deliberate signal tier, not something to launder into full trust.
- Committing a real signed claim-v2 binary to `samples/`; unit-level mocked manifests only this slice.
- Refactoring substring matching into exact-match URI matching.

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `receipt-analysis`: the provenance requirement must recognize claim-v2 nested `digitalSourceType`, and must distinguish an untrusted-signer AI claim (CRITICAL, verdict-forcing HIGH_RISK — a cryptographically intact AI-generation claim is direct evidence regardless of CA trust) from structural/cryptographic failure (still `PROVENANCE_VALIDATION_FAILED`, non-verdict-forcing).

## Approach

| Decision | Choice | Reasoning |
|---|---|---|
| Parsing | Additive dual-path | Strictly additive; the 3 existing flat-field tests stay green |
| Status split | Allowlist (`signingCredential.untrusted`) | Fail-closed: unknown codes keep the stricter `PROVENANCE_VALIDATION_FAILED` bucket |
| Multi-entry precedence | Worst case wins | New code only when EVERY entry is allowlisted |
| Severity/weight | CRITICAL, weight 50, confidence 0.85, `critical_floor` 85 | `int(50 × 2.0 × 0.85) = 85` already lands in HIGH_RISK on its own — the floor is a no-op restating the same number, kept only for consistency with `VALID_AI_GENERATED_CLAIM`'s pattern. A cryptographically intact AI-claim is direct evidence regardless of CA trust (product decision: the untrusted-CA distinction is for audit/explainability in `signals[]`, not for softening the verdict) |
| Ruleset | New `v2026_09_06` (copy-forward, `v2026_09_05` frozen) | New weight is a policy change (CONTRIBUTING.md) |
| Engine | `ENGINE_VERSION` → `0.3.0` | Adapter parsing/classification is shared, unconditional logic — it changes replays under every ruleset version, exactly the `scoring-confidence-calibration` precedent |

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `apps/api/src/receipt_risk/adapters/provenance/c2pa_reader.py` | Modified | Dual-path parsing, marker set, status allowlist, docstring |
| `apps/api/src/receipt_risk/domain/signals.py` | Modified | New `SignalCode` member |
| `apps/api/src/receipt_risk/domain/rulesets/v2026_09_06.py` | New | Copy-forward + new weight |
| `apps/api/src/receipt_risk/domain/rulesets/__init__.py` | Modified | Register new ruleset |
| `apps/api/src/receipt_risk/bootstrap/app.py` | Modified | Repoint 3 wiring sites |
| `apps/api/src/receipt_risk/application/analyze_receipt.py` | Modified | `ENGINE_VERSION = "0.3.0"` |
| `apps/api/tests/unit/test_c2pa_reader.py` | Modified | New claim-v2 and status-tier fixtures |
| `docs/API.md`, `openspec/specs/receipt-analysis/spec.md` | Modified | Version examples, provenance requirement |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Allowlist misses a benign CA-trust code, over-flagging as tampering | Med | Fail-closed by design; extend the allowlist on evidence |
| No real signed fixture — unit mocks may drift from the real schema | Med | Fixtures derived from the captured real Gemini manifest shape |
| Golden regeneration across API tests from the version bumps | High | Hand-recompute per the prior change's rule |
| Untrusted-signer tier forces HIGH_RISK same as fully-trusted — no numeric distinction reaches the user, only the `signals[]` code/description differ | Low | Confirmed by design: this is intentional (direct evidence, not softened); a future retune (e.g. if legitimate generators trip this from CA-trust-list lag) is a new frozen ruleset version, not a code change |

## Rollback Plan

Repoint `bootstrap/app.py` to `RULESET_2026_09_05` (3 sites); the new ruleset stays registered and inert. The adapter fix and `ENGINE_VERSION` bump are shared engine code and are NOT covered by that repoint — reverting them requires reverting the commit.

## Dependencies

- None. `c2pa-python==0.37.8` already installed; no new API surface used.

## Success Criteria

- [ ] A claim-v2 manifest with nested `trainedAlgorithmicMedia` and empty `validation_status` emits `VALID_AI_GENERATED_CLAIM`.
- [ ] The same manifest with only `signingCredential.untrusted` emits `AI_GENERATED_CLAIM_UNTRUSTED_SIGNER` (CRITICAL, 0.85, score 85 alone → HIGH_RISK, same verdict as the fully-trusted case).
- [ ] Any unrecognized or structural status code still emits `PROVENANCE_VALIDATION_FAILED`.
- [ ] The 5 existing `test_c2pa_reader.py` tests pass unchanged.
- [ ] `/version` reports `engine_version: 0.3.0`, `ruleset_version: 2026-09-06`.
