# Design: C2PA AI-Claim Detection — claim-v2 parsing + untrusted-signer tier

## Technical Approach

Four layered edits, one new active ruleset version, no new module and no port/contract change:

1. **Dual-path source-type extraction** — `_has_algorithmic_source_claim` gains a second lookup path over `assertions[].data.actions[].digitalSourceType` (the `c2pa.actions.v2` claim-v2 shape) while keeping the existing flat `data["Iptc4xmpExt:DigitalSourceType"]` path untouched. Strictly additive: a manifest matching either shape is an AI claim.
2. **Validation-status tiering** — a module-level fail-closed allowlist splits `validation_status` into three outcomes (empty / all-allowlisted / any-non-allowlisted), driving three distinct signals from the single existing `_derive_signals` branch point.
3. **Policy** — new `SignalCode.AI_GENERATED_CLAIM_UNTRUSTED_SIGNER` priced in a new frozen ruleset `v2026_09_06` (copy-forward of `v2026_09_05`), wired at three `bootstrap/app.py` sites.
4. **Engine identity** — `ENGINE_VERSION` `0.2.0` → `0.3.0`, because edits 1 and 2 live in shared adapter code applied unconditionally under every registered ruleset version.

The architecture boundary is unchanged: parsing/classification stays in the adapter (`adapters/provenance/c2pa_reader.py`), pricing stays in `domain/rulesets/`, and `domain/scoring.py` is not touched at all. No new dependency, no new API field, no schema change.

## Architecture Decisions

### Decision: The adapter fix is unconditional shared code, tracked by `ENGINE_VERSION` (not by ruleset)

**Choice**: Fix `_has_algorithmic_source_claim` and `_derive_signals` unconditionally in the adapter. Do **not** make either version-aware. Bump `ENGINE_VERSION` from `"0.2.0"` to `"0.3.0"` in `application/analyze_receipt.py`.

**Alternatives considered**:

| Option | Tradeoff | Verdict |
|---|---|---|
| Version-gate parsing on `ruleset.version` inside the adapter | The adapter has no `ScoringRuleset` reference at all — `ProvenancePort.inspect(image)` takes only a `SafeImageRef`. Threading a ruleset into an adapter to gate a *parsing defect* inverts the layering (`docs/ARCHITECTURE.md` §5) and makes signal *detection* a policy input | Rejected |
| A per-version `source_type_paths` / `status_allowlist` field on `ScoringRuleset` | Leaks parsing schema knowledge into the pure pricing data module, exactly the failure mode rejected by the `scoring-confidence-calibration` precedent for `completeness_strategy`. Also permanently preserves a defect that silently misses real AI claims | Rejected |
| Unconditional fix + `ENGINE_VERSION` bump | A historical replay of `2026-09-01` under engine `0.3.0` can now emit a signal it did not emit under `0.2.0` | **Chosen** |

**Rationale**: This is the identical shape to the `scoring-confidence-calibration` precedent (`ENGINE_VERSION` `0.1.0` → `0.2.0` for the `_completeness` provenance fix). `ruleset_version` freezes **policy** — which codes exist and what they are worth. `engine_version` tracks **formulas and detection**, which are corrected retroactively and unconditionally. Missing a genuine AI-generation claim is a detection defect, not a policy preference, so preserving it per-version would be preserving a bug. The two-version tuple `(engine_version, ruleset_version)` in `/version` and in every assessment stays the complete replay key.

### Decision: Allowlist (not denylist) for `validation_status`, with worst-case multi-entry precedence

**Choice**: A frozen module constant `_CA_TRUST_ONLY_STATUS_CODES = frozenset({"signingCredential.untrusted"})`. The new untrusted-signer signal fires only when `validation_status` is non-empty **and every entry's `code` is in that set**. One non-allowlisted entry sends the whole result to the existing strict `PROVENANCE_VALIDATION_FAILED` bucket.

**Alternatives considered**:

| Option | Tradeoff | Verdict |
|---|---|---|
| Denylist of known-tampering codes | Any code the C2PA spec adds later defaults to the *lenient* tier. Fails open on the exact axis that matters (tamper detection) | Rejected |
| Allowlist including `signingCredential.expired` | An expired cert is a weaker trust story than an unrecognized-but-current CA and can co-occur with a stale/replayed asset. Explicit product decision: stay strict for now, revisit on evidence | Rejected (this slice) |
| Per-entry signal emission (one signal per status code) | Multiple provenance signals would stack weights and make the score depend on how many codes the SDK happened to report — a scoring artifact, not evidence | Rejected |
| Allowlist + all-entries-must-match precedence | An untrusted-CA code co-occurring with a hash mismatch loses its own audit entry in `signals[]` | **Chosen** |

**Rationale**: Fail-closed is the only defensible default for a fraud signal. The precedence rule ("worst case wins") means the presence of any genuine integrity failure dominates, which is correct: once integrity is in doubt, the AI claim's own trustworthiness is moot and `PROVENANCE_VALIDATION_FAILED` is the honest description. Extending the allowlist later is a pure adapter edit (engine bump), not a ruleset change, because it changes *classification*, not price.

### Decision: The untrusted-signer tier is CRITICAL and verdict-forcing, identical in effect to the trusted case

**Choice**: `AI_GENERATED_CLAIM_UNTRUSTED_SIGNER` — category `PROVENANCE`, severity `CRITICAL`, confidence `0.85`, weight `50`, `critical_floor` `85`.

Arithmetic (`domain/scoring.py`'s weighted formula, `int(weight × severity_multiplier × confidence)`): `int(50 × 2.0 × 0.85) = 85`. The `critical_floor` entry of `85` is therefore a **no-op restating the same number** on the single-signal path; it exists so the code cannot fall below HIGH_RISK if a future version retunes weight or confidence, matching `VALID_AI_GENERATED_CLAIM`'s existing floor pattern (`85`).

**Alternatives considered**:

| Option | Tradeoff | Verdict |
|---|---|---|
| Reuse `VALID_AI_GENERATED_CLAIM` for both cases | Identical verdict, but `signals[]` would lose the CA-trust distinction entirely — no audit trail, no independent retuning path | Rejected |
| HIGH severity / sub-floor weight (SUSPICIOUS tier) | Softens a cryptographically intact AI-generation claim into "review recommended". The signature verified; only the trust anchor is unfamiliar. The claim content is direct evidence | Rejected |
| Separate CRITICAL code, same effective verdict | No numeric distinction reaches the user; only the code and description differ | **Chosen** |

**Rationale**: The distinction being modelled is *who vouched for the claim*, not *whether the claim is evidence*. A manifest that passes every cryptographic check and declares `trainedAlgorithmicMedia` is direct evidence of AI generation regardless of whether our trust list happens to contain the issuing CA — CA-trust-list lag is our gap, not the asset's innocence. Keeping a distinct code buys explainability in `signals[]` and a clean future retuning surface (a new frozen ruleset version, no code change) if legitimate generators start tripping this from trust-list lag.

### Decision: Copy-forward `v2026_09_06`, `v2026_09_05` stays frozen and registered

**Choice**: New file `domain/rulesets/v2026_09_06.py`, a byte-for-value copy of `v2026_09_05` plus exactly two new dict entries. `v2026_09_05.py` is not edited. Both stay in `RULESETS`.

**Rationale**: CONTRIBUTING.md's rule — scoring changes bump `ruleset_version` rather than mutate a shipped one in place — so any request logged with `ruleset_version="2026-09-05"` stays reproducible. This is the third application of the pattern (`v2026_09_01` → `v2026_09_04` → `v2026_09_05`), so the file mirrors `v2026_09_05.py`'s docstring structure verbatim in shape: state what is superseded, state that the prior version is kept registered, state the single policy delta.

## Component Map

| Layer | Component | Change |
|---|---|---|
| Adapter | `c2pa_reader._ALGORITHMIC_SOURCE_MARKERS` | Add `compositesynthetic` |
| Adapter | `c2pa_reader._CA_TRUST_ONLY_STATUS_CODES` | New frozen allowlist constant |
| Adapter | `c2pa_reader._iter_source_types` | New private generator (dual-path extraction) |
| Adapter | `c2pa_reader._has_algorithmic_source_claim` | Rewritten over `_iter_source_types`; signature unchanged |
| Adapter | `c2pa_reader._is_ca_trust_only` | New predicate over `validation_status` |
| Adapter | `c2pa_reader._derive_signals` | Three-way branch; signature unchanged |
| Domain | `signals.SignalCode` | New member |
| Domain | `rulesets/v2026_09_06.py` | New frozen ruleset |
| Domain | `rulesets/__init__.py` | Register 4th entry |
| Application | `analyze_receipt.ENGINE_VERSION` | `"0.2.0"` → `"0.3.0"` |
| Bootstrap | `bootstrap/app.py` | 3 wiring sites repointed |

## Data Flow

Unchanged end to end. `C2paProvenanceAdapter.inspect` → `_read_manifest` (thread-offloaded `c2pa.Reader`) → `_derive_signals(manifest)` → `AnalyzerResult.signals` → `AnalyzeReceiptUseCase` fan-in → `domain/scoring.py` prices each signal against the active `ScoringRuleset` → `FraudAssessment`. The only delta is which `ValidationSignal` (if any) `_derive_signals` returns and what the active ruleset charges for it.

New decision table inside `_derive_signals` (evaluated only when `_has_algorithmic_source_claim(active)` is true; a non-AI manifest still returns `()` regardless of status):

| `validation_status` | Signal | Severity | Confidence |
|---|---|---|---|
| empty | `VALID_AI_GENERATED_CLAIM` | CRITICAL | `1.00` |
| every entry's `code` in `_CA_TRUST_ONLY_STATUS_CODES` | `AI_GENERATED_CLAIM_UNTRUSTED_SIGNER` | CRITICAL | `0.85` |
| any other entry present | `PROVENANCE_VALIDATION_FAILED` (unchanged) | MEDIUM | `0.60` |

## Integration Points / Proposed Code

### 1. `apps/api/src/receipt_risk/adapters/provenance/c2pa_reader.py`

Constants (module level, after the existing marker tuple):

```python
_ALGORITHMIC_SOURCE_MARKERS: Final[tuple[str, ...]] = (
    "trainedalgorithmicmedia",
    "compositewithtrainedalgorithmicmedia",
    "algorithmicmedia",
    "compositesynthetic",
)

# `validation_status` codes that mean "we do not recognize the signing CA",
# NOT "the asset or its signature is broken". Fail-closed allowlist: any code
# absent from this set keeps the whole manifest in the stricter
# PROVENANCE_VALIDATION_FAILED bucket. `signingCredential.expired` is
# deliberately NOT allowlisted this slice (design.md decision 2).
_CA_TRUST_ONLY_STATUS_CODES: Final[frozenset[str]] = frozenset(
    {"signingCredential.untrusted"}
)
```

Dual-path extraction — one generator, one predicate over it:

```python
def _iter_source_types(manifest_entry: dict[str, Any]) -> Iterator[str]:
    """Yield every lowercased `digitalSourceType` value declared by the
    manifest, across both shapes we have observed in the wild:

    * flat IPTC assertion data (`Iptc4xmpExt:DigitalSourceType`) — the
      original claim-v1 style shape the first three unit tests pin;
    * `c2pa.actions.v2` assertions, which nest the value per action under
      `data.actions[].digitalSourceType` — the shape a real Google Gemini
      `claim_version: 2` manifest actually uses.

    Additive by construction: a manifest declaring either shape (or both)
    yields all of its values, so no previously-detected claim is lost.
    """
    for assertion in manifest_entry.get("assertions", []):
        data = assertion.get("data", {})
        if not isinstance(data, dict):
            continue

        flat = data.get("Iptc4xmpExt:DigitalSourceType")
        if flat:
            yield str(flat).lower()

        actions = data.get("actions", [])
        if not isinstance(actions, list):
            continue
        for action in actions:
            if not isinstance(action, dict):
                continue
            nested = action.get("digitalSourceType")
            if nested:
                yield str(nested).lower()


def _has_algorithmic_source_claim(manifest_entry: dict[str, Any]) -> bool:
    return any(
        marker in source_type
        for source_type in _iter_source_types(manifest_entry)
        for marker in _ALGORITHMIC_SOURCE_MARKERS
    )
```

`Iterator` comes from `collections.abc` (add to the existing `from __future__ import annotations` file header imports). The `isinstance` guards exist because `manifest` is untrusted JSON decoded from an attacker-supplied file — a `data` that is a string or an `actions` that is a dict must not raise out of a pure function whose only documented failure mode is "returns nothing".

Status tiering:

```python
def _is_ca_trust_only(validation_status: list[dict[str, Any]]) -> bool:
    """True when EVERY reported status entry is a CA-trust-only code.

    Worst-case precedence: a single non-allowlisted entry (hash mismatch,
    broken signature, expired credential) makes this False, keeping the
    manifest in the strict `PROVENANCE_VALIDATION_FAILED` bucket. Callers
    must have already established `validation_status` is non-empty.
    """
    return all(
        str(entry.get("code", "")) in _CA_TRUST_ONLY_STATUS_CODES
        for entry in validation_status
        if isinstance(entry, dict)
    ) and any(isinstance(entry, dict) for entry in validation_status)
```

The trailing `any(...)` clause makes a `validation_status` that is non-empty but contains no dict entries (malformed input) fall through to the strict bucket rather than being vacuously "all allowlisted".

`_derive_signals` — the existing early returns for `manifest is None`, missing active manifest, and `not is_ai_claim` are unchanged; only the tail gains a branch:

```python
    if not validation_status:
        return (
            ValidationSignal(
                code=SignalCode.VALID_AI_GENERATED_CLAIM,
                ...  # unchanged
            ),
        )

    if _is_ca_trust_only(validation_status):
        return (
            ValidationSignal(
                code=SignalCode.AI_GENERATED_CLAIM_UNTRUSTED_SIGNER,
                category=SignalCategory.PROVENANCE,
                severity=Severity.CRITICAL,
                confidence=Decimal("0.85"),
                description=(
                    "A cryptographically intact Content Credentials (C2PA) "
                    "manifest declares this image as algorithmically "
                    "generated or composited, but it was signed by a "
                    "certificate authority this engine does not recognize."
                ),
                evidence={
                    "active_manifest": str(active_label),
                    "validation_status_codes": ",".join(
                        str(entry.get("code", "")) for entry in validation_status
                    ),
                },
            ),
        )

    return (
        ValidationSignal(
            code=SignalCode.PROVENANCE_VALIDATION_FAILED,
            ...  # unchanged: MEDIUM, Decimal("0.60"), same description/evidence
        ),
    )
```

`evidence` is `Mapping[str, str]`, so the status codes are joined into a single comma-separated string rather than passed as a list. The module docstring gains a paragraph describing the three-way tier and naming the allowlist decision as a design-time choice.

### 2. `apps/api/src/receipt_risk/domain/signals.py`

The enum is grouped by originating slice/change with a comment header per group, in chronological order. Follow it: append a new trailing group after the `visual-anomaly-detection` group.

```python
    # visual-anomaly-detection change
    VISUAL_ANOMALY_DETECTED = "VISUAL_ANOMALY_DETECTED"  # category VISUAL, LOW/MEDIUM, no floor
    # c2pa-ai-claim-detection change
    # category PROVENANCE, CRITICAL, confidence 0.85, critical_floor 85 --
    # an intact AI-generation claim signed by an unrecognized CA. Separate
    # from VALID_AI_GENERATED_CLAIM for audit/explainability only; the
    # verdict it forces is identical.
    AI_GENERATED_CLAIM_UNTRUSTED_SIGNER = "AI_GENERATED_CLAIM_UNTRUSTED_SIGNER"
```

Placement is append-only at the end of `SignalCode`. It is **not** inserted next to `VALID_AI_GENERATED_CLAIM` in the "slice 2" group: the existing convention groups by *when the code was introduced*, not by category, and every prior change (slices 3, 4, visual-anomaly-detection) appended. `StrEnum` member order is not semantically load-bearing anywhere in the codebase (no ordinal comparisons, no iteration-order dependence), so appending is safe.

### 3. `apps/api/src/receipt_risk/domain/rulesets/v2026_09_06.py` (new)

Mirror `v2026_09_05.py`'s structure exactly — same constant names, same order, same `ScoringRuleset(...)` keyword order:

```python
"""Ruleset version `2026-09-06` -- prices the untrusted-signer AI claim.

Supersedes `v2026_09_05` as the MVP1 default (c2pa-ai-claim-detection
change): copy-forward of every `v2026_09_05` value, plus a weight and a
critical floor for the new `AI_GENERATED_CLAIM_UNTRUSTED_SIGNER` code.
`v2026_09_05` is kept unmodified and still registered in
`rulesets/__init__.py` so any request logged with
`ruleset_version="2026-09-05"` stays reproducible (CONTRIBUTING.md: scoring
changes bump `ruleset_version` rather than mutate a shipped one in place).

Multipliers, bands, evidence weights, status quality, the coverage threshold
and `combination_floors` are unchanged from `v2026_09_05` -- this version's
only policy delta is the two new entries for the new code.
"""
```

`_WEIGHTS` — all ten `v2026_09_05` entries verbatim, plus:

```python
    # A cryptographically intact AI-generation claim from an unrecognized CA
    # is still direct evidence of AI generation -- only the trust anchor is
    # unfamiliar, not the claim. int(50 * 2.0 * 0.85) == 85, which already
    # lands in HIGH_RISK unaided; the floor below restates it for safety
    # under future retuning. Priced below VALID_AI_GENERATED_CLAIM's 90 so
    # the audit trail keeps a numeric trace of the trust gap even though the
    # verdict is identical.
    SignalCode.AI_GENERATED_CLAIM_UNTRUSTED_SIGNER: 50,
```

`_CRITICAL_FLOOR`:

```python
_CRITICAL_FLOOR: dict[SignalCode, int] = {
    SignalCode.VALID_AI_GENERATED_CLAIM: 85,
    SignalCode.AI_GENERATED_CLAIM_UNTRUSTED_SIGNER: 85,
}
```

`_SEVERITY_MULTIPLIER`, `_COMBINATION_FLOORS`, `_ANALYZER_EVIDENCE_WEIGHTS`, `_STATUS_QUALITY`, `_BANDS` and `inconclusive_coverage_threshold=Decimal("0.35")` are copied verbatim. Export name `RULESET_2026_09_06`, `version="2026-09-06"`.

### 4. `apps/api/src/receipt_risk/domain/rulesets/__init__.py`

Append-only, matching the existing alphabetical-by-date import and dict pattern:

```python
from receipt_risk.domain.rulesets.v2026_09_06 import RULESET_2026_09_06

RULESETS: Final[dict[str, ScoringRuleset]] = {
    RULESET_2026_09_01.version: RULESET_2026_09_01,
    RULESET_2026_09_04.version: RULESET_2026_09_04,
    RULESET_2026_09_05.version: RULESET_2026_09_05,
    RULESET_2026_09_06.version: RULESET_2026_09_06,
}
```

`RULESETS` grows from 3 to 4 entries — `test_ruleset.py` asserts this count and must be updated.

### 5. `apps/api/src/receipt_risk/bootstrap/app.py` — the 3 wiring sites

| Site | Current line | Current text | New text |
|---|---|---|---|
| Import | 34 | `from receipt_risk.domain.rulesets.v2026_09_05 import RULESET_2026_09_05` | `...v2026_09_06 import RULESET_2026_09_06` |
| Use-case construction | 85 | `ruleset=RULESET_2026_09_05,` | `ruleset=RULESET_2026_09_06,` |
| `/version` endpoint | 118 | `ruleset_version=RULESET_2026_09_05.version,` | `ruleset_version=RULESET_2026_09_06.version,` |

These are the only three occurrences of the symbol in the file; no other module imports a concrete ruleset (adapters and the use case take it by injection).

### 6. `apps/api/src/receipt_risk/application/analyze_receipt.py`

Module-level constant at **line 40**, with its rationale docstring immediately below (lines 41-45). Replace both:

```python
ENGINE_VERSION = "0.3.0"
"""Bumped 0.2.0 -> 0.3.0 by the c2pa-ai-claim-detection change: the
claim-v2 `digitalSourceType` parsing fix and the `validation_status`
allowlist in `adapters/provenance/c2pa_reader.py` are shared-adapter
detection corrections, applied unconditionally and retroactively under every
ruleset version, so they are tracked by `engine_version` rather than
`ruleset_version` (which freezes policy, not detection). Same reasoning as
the 0.1.0 -> 0.2.0 `_completeness` bump."""
```

The prior bump's docstring is replaced rather than appended to — that is what the `0.1.0 -> 0.2.0` bump did to the original.

## Test / Fixture Design

`apps/api/tests/unit/test_c2pa_reader.py` — the file's established style is one self-contained inline `manifest` dict literal per test, no shared fixtures, no parametrize, with `_derive_signals` called directly. Match it exactly; do not refactor the existing five tests into fixtures.

Four new tests, appended after `test_c2pa_valid_manifest_without_ai_claim_emits_no_signal`:

**(a) claim-v2 nested actions, clean validation → `VALID_AI_GENERATED_CLAIM`** (proves the parsing defect is fixed):

```python
def test_c2pa_claim_v2_nested_action_source_type_emits_critical_signal() -> None:
    manifest = {
        "active_manifest": "urn:uuid:gemini-v2",
        "manifests": {
            "urn:uuid:gemini-v2": {
                "claim_version": 2,
                "validation_status": [],
                "assertions": [
                    {
                        "label": "c2pa.actions.v2",
                        "data": {
                            "actions": [
                                {
                                    "action": "c2pa.created",
                                    "digitalSourceType": (
                                        "http://cv.iptc.org/newscodes/"
                                        "digitalsourcetype/trainedAlgorithmicMedia"
                                    ),
                                    "softwareAgent": {"name": "Google Gemini"},
                                }
                            ]
                        },
                    }
                ],
            }
        },
    }

    signals = _derive_signals(manifest)

    assert len(signals) == 1
    assert signals[0].code == SignalCode.VALID_AI_GENERATED_CLAIM
    assert signals[0].severity == Severity.CRITICAL
```

**(b) claim-v2 nested actions + untrusted-signer-only status → new code**:

```python
def test_c2pa_untrusted_signer_only_emits_critical_untrusted_signer_signal() -> None:
    manifest = {
        "active_manifest": "urn:uuid:gemini-untrusted",
        "manifests": {
            "urn:uuid:gemini-untrusted": {
                "claim_version": 2,
                "validation_state": "Valid",
                "validation_status": [
                    {
                        "code": "signingCredential.untrusted",
                        "url": "self#jumbf=/c2pa/urn:uuid:gemini-untrusted/c2pa.signature",
                        "explanation": "signing certificate untrusted",
                    }
                ],
                "assertions": [
                    {
                        "label": "c2pa.actions.v2",
                        "data": {
                            "actions": [
                                {
                                    "action": "c2pa.created",
                                    "digitalSourceType": (
                                        "http://cv.iptc.org/newscodes/"
                                        "digitalsourcetype/trainedAlgorithmicMedia"
                                    ),
                                }
                            ]
                        },
                    }
                ],
            }
        },
    }

    signals = _derive_signals(manifest)

    assert len(signals) == 1
    assert signals[0].code == SignalCode.AI_GENERATED_CLAIM_UNTRUSTED_SIGNER
    assert signals[0].severity == Severity.CRITICAL
    assert signals[0].category == SignalCategory.PROVENANCE
    assert signals[0].confidence == Decimal("0.85")
```

**(c) mixed status — untrusted signer PLUS a hash mismatch → strict bucket** (pins worst-case precedence):

same manifest as (b) with `validation_status` set to

```python
                "validation_status": [
                    {"code": "signingCredential.untrusted", "explanation": "untrusted CA"},
                    {"code": "assertion.dataHash.mismatch", "explanation": "hash mismatch"},
                ],
```

asserting `signals[0].code == SignalCode.PROVENANCE_VALIDATION_FAILED`.

**(d) non-allowlisted trust code alone → strict bucket** (pins fail-closed and the explicit `expired` decision): same manifest with `validation_status` of a single `{"code": "signingCredential.expired", ...}`, asserting `PROVENANCE_VALIDATION_FAILED`.

Also required:
- `from decimal import Decimal` added to the test module imports (for (b)).
- The five existing tests are asserted **unchanged** — they pin the flat-field path and are the regression guard on the "additive, not replacement" decision.
- `test_ruleset.py`: `len(RULESETS) == 4`, `RULESET_2026_09_06.version == "2026-09-06"`, and `RULESET_2026_09_05` still exposes its original weights/floors (frozen-forward guard).
- Golden regeneration across `test_assessment.py`, `test_analyze_receipt.py`, `test_api_schemas.py`, `test_api_error_contract.py`, `test_router.py`, `test_log_privacy.py`, and `tests/integration/test_analyze_endpoint_e2e.py` for `engine_version` → `0.3.0` and `ruleset_version` → `2026-09-06`. Per the two prior precedents, golden values are **recomputed by hand from the formulas and pasted**, never copied from a failing run. Weights themselves are unchanged for every pre-existing code, so only the two version strings should move; any golden `risk_score`/`confidence_score` that shifts is a defect, not a regeneration.

## Migration / Rollout

No data migration. Rollout is config-first: `bootstrap/app.py` selects the active ruleset.

**Rollback**: repoint the three `bootstrap/app.py` sites (34, 85, 118) back to `RULESET_2026_09_05`. `v2026_09_06` stays registered and inert, so any assessment already logged under `2026-09-06` remains replayable.

**Rollback boundary (explicit)**: that repoint does **not** revert the adapter fix or the `ENGINE_VERSION` bump. Both are shared engine code by design (decision 1). After a repoint-only rollback the engine still detects claim-v2 nested `digitalSourceType` and still classifies untrusted-signer-only status separately — but under `v2026_09_05` the new code has **no weight entry** and **no floor entry**.

Verified against `domain/scoring.py`: the price lookup is `Decimal(ruleset.weights.get(signal.code, 0))` (line 54) and the floor lookup is guarded by `if ... signal.code in ruleset.critical_floor` (lines 64-66). Both default cleanly, so a repoint-only rollback is **safe**: an untrusted-signer manifest under `v2026_09_05` emits the signal into `signals[]` with `score_contribution == 0` and forces no floor. No `KeyError`, no crash. The degraded behavior is "the new evidence is visible in the audit trail but priced at nothing" — an under-flagging, not a failure. A full revert of the detection fix still requires reverting the commit.

## Documentation

| Doc | Action | When |
|---|---|---|
| `docs/API.md` lines 29-30, 65-66 | `"engine_version": "0.3.0"`, `"ruleset_version": "2026-09-06"` in both `/version` and analyze-response examples | This change |
| `openspec/changes/c2pa-ai-claim-detection/specs/receipt-analysis/spec.md` | Delta spec: the provenance requirement recognizes claim-v2 nested `digitalSourceType`, and distinguishes the untrusted-signer AI claim from structural/cryptographic failure | **`sdd-spec` phase**, not this design phase |
| `openspec/specs/receipt-analysis/spec.md` (main) | **Not touched now.** Repo convention (every archived change: `mvp-init-foundation`, `generic-receipt-field-extraction`, `scoring-confidence-calibration`) is that the change dir carries the delta spec and the main spec is merged at **archive** time | Archive step |

The proposal's "Affected Areas" row listing `openspec/specs/receipt-analysis/spec.md` should be read as "eventually modified via archive merge", not as a file this change's commits edit directly.

## Threat Matrix

N/A for new attack surface — no routing, shell, subprocess, VCS automation, executable-file classification, or process-integration boundary is added or altered. The `c2pa.Reader` surface is unchanged (still read-only, still thread-offloaded, still exception-swallowed to `None`).

One input-handling note inside the existing surface: `_iter_source_types` and `_is_ca_trust_only` now walk deeper into attacker-controlled JSON (`data.actions[]`, `validation_status[].code`). Both are written defensively with `isinstance` guards so a malformed manifest degrades to "no signal" / "strict bucket" rather than raising out of `_derive_signals`, preserving the adapter's contract that a bad manifest is neutral, never an error.

## Open Questions

- [x] ~~Does `domain/scoring.py` default safely for an unpriced `SignalCode`?~~ **Resolved during design**: yes — `weights.get(code, 0)` and a `in ruleset.critical_floor` membership guard. Repoint-only rollback is safe.
- [ ] None blocking. The `signingCredential.expired` allowlist question is deliberately deferred (decision 2) and, if reopened on evidence, becomes an adapter edit plus an `ENGINE_VERSION` bump — not a new ruleset version.
