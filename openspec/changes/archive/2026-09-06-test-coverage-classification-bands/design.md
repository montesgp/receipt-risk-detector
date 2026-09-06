# Design: Classification-Band Coverage + Untrusted-Signer Parity

## Technical Approach

Verification-only change. No file under `apps/api/src/` is touched. Every band is
reached by feeding the existing mocked-port e2e harness richer fixture metadata:
`_FixtureNeutralPort` starts emitting `ValidationSignal`s, which
`AnalyzeReceiptUseCase.execute` already chains verbatim (`chain.from_iterable(result.signals)`)
into `assemble` → `score` → response `classification`.

## Architecture Decisions

### Decision: route `expected_signals` to neutral ports by `category`, not broadcast

**Choice**: `_FixtureNeutralPort` receives the whole `fixture.expected_signals` list and emits
only entries whose `category` maps to its own role:
`metadata→metadata`, `provenance→provenance`, `visual→vision`. Other categories
(`financial_consistency`, `data_quality`) are emitted by no neutral port.
**Alternatives**: (a) every neutral port emits the whole list — 3x duplicate signals, wrong scores;
(b) a single designated emitter port — works, but emits provenance/visual signals from `exiftool`.
**Rationale**: Category routing is the only option that is both non-duplicating and
semantically honest. It also subsumes the proposal's "only emit when non-empty" guard and,
critically, keeps `invalid_cbu_check_digit` unchanged: its lone `financial_consistency`
signal routes to no port, so `validate_financials()` remains the single source of that
signal and no double-count occurs. Existing fixtures all carry `expected_signals: []`.

### Decision: manifest entries must also be emitted by `generate.py`, not hand-added

**Choice**: `generate()` registers alias digests (`digests["<new_id>"] = digests["clean_valid_transfer"]`,
no new file written) and `_build_manifest()` gains the two matching entries.
**Alternatives**: hand-edit `manifest.json` only.
**Rationale**: **Blocking defect found during design.** `main(--check)` compares
`generate()`'s digest dict to `{f["id"]: f["sha256"] for f in committed_manifest["fixtures"]}`
by full-dict equality. Two manifest-only ids would make `--check` fail immediately, and the
next `python samples/generate.py` would silently delete them. The proposal's assumption that
`--check` stays untouched is wrong; aliasing restores it.

### Decision: INCONCLUSIVE via `dataclasses.replace`, no manifest entry

**Choice**: `replace(load_fixture("clean_valid_transfer"), expected_analyzer_statuses={"ocr": "failed",
"metadata": "failed", "provenance": "failed", "vision": "completed"})` → coverage `0.15 < 0.35`.
**Alternatives**: all-four-failed (coverage `0.00` — proves nothing about the threshold);
a new manifest entry (would need generate.py plumbing for zero benefit).
**Rationale**: `Fixture` is a frozen slotted dataclass, so `replace` is safe. A non-zero
coverage below threshold proves the gate, not a degenerate zero.

## Score Arithmetic (RULESET_2026_09_06, bands 24/49/74/100)

| New fixture id | Injected signals | `int(weight × sev × conf)` | Band |
|---|---|---|---|
| `synthetic_band_review_recommended` | `METADATA_EDITOR_SOFTWARE` (metadata/low/0.80) + `PROVENANCE_VALIDATION_FAILED` (provenance/medium/1.00) + `VISUAL_ANOMALY_DETECTED` (visual/medium/1.00) | 4 + 15 + 20 = **39** | REVIEW_RECOMMENDED |
| `synthetic_band_high_risk` | `AI_GENERATED_CLAIM_UNTRUSTED_SIGNER` (provenance/critical/0.85) | 50×2.0×0.85 = **85** (= `critical_floor`) | HIGH_RISK |

Both reuse `images/clean_valid_transfer.png` + its sha256 and copy its `declared_fields`
verbatim (valid CBU/CUIT/date), so `validate_financials()` contributes **0** and the injected
signals are the sole score driver. Existing `invalid_cbu_check_digit` = `40×1.5×1.00` = 60 → SUSPICIOUS.

## Data Flow

    manifest.json expected_signals
        └─ conftest.fixture() ─→ _FixtureNeutralPort(role) ─ category filter ─→ AnalyzerResult.signals
                                                                                     │
    declared_fields ─→ _FixtureOcrPort ─→ extracted_fields ─→ validate_financials ─┤
                                                                                     ▼
                       expected_analyzer_statuses ─→ status ─→ score() ─→ classification ─→ HTTP body

## File Changes

| File | Action | Description |
|---|---|---|
| `apps/api/tests/integration/test_analyze_endpoint_e2e.py` | Modify | `_FixtureNeutralPort` gains `_CATEGORY_ROLE` routing + `_signals_from(fixture)`; add classification + `ruleset_version` asserts to the SUSPICIOUS test; add 3 tests (REVIEW_RECOMMENDED, HIGH_RISK, INCONCLUSIVE) + reuse comment |
| `samples/generate.py` | Modify | `_build_manifest()` `invalid_cbu_check_digit` `"REVIEW_RECOMMENDED"` → `"SUSPICIOUS"`; `generate()` alias digests; two new `_build_manifest()` entries |
| `samples/manifest.json` | Modify | Two reuse entries with explicit `notes` naming the shared path/sha256 |
| `apps/api/tests/unit/test_domain_signals.py` | Modify | Mirror `test_valid_ai_generated_claim_signal_is_critical_severity` for the untrusted-signer code |
| `apps/api/tests/unit/test_assessment.py` | Modify | Add `RULESET_2026_09_06` import; mirror `test_recommended_action_maps_high_risk_to_do_not_rely` |
| `apps/api/tests/unit/test_scoring.py` | Modify | Add `RULESET_2026_09_06` import; mirror critical-floor + OCR-zero-override tests |

`RULESET_2026_09_04` has **no** weight or floor for `AI_GENERATED_CLAIM_UNTRUSTED_SIGNER`;
the mirrored assertions in `test_assessment.py` / `test_scoring.py` MUST use `RULESET_2026_09_06`.

## Interfaces / Contracts

```python
class _FixtureNeutralPort:
    _CATEGORY_ROLE = {"metadata": "metadata", "provenance": "provenance", "visual": "vision"}

    def __init__(self, role: str, fixture: Fixture) -> None:
        self.name = self._NAMES.get(role, "stub")
        self._status = fixture.expected_analyzer_statuses.get(role, "completed")
        self._signals = tuple(
            ValidationSignal(
                code=SignalCode(e["code"]),
                category=SignalCategory(e["category"]),
                severity=Severity(e["severity"]),
                confidence=Decimal(str(e.get("confidence", "1.00"))),
                description=e.get("description", "fixture-injected signal"),
            )
            for e in fixture.expected_signals
            if self._CATEGORY_ROLE.get(e["category"]) == role
        )
```

`ValidationSignal.confidence` has no default, so the manifest entries carry an explicit
`confidence` string; `0.85` for the untrusted-signer entry mirrors the real c2pa reader.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | Untrusted-signer severity/category shape | Mirror `test_domain_signals.py` valid-claim test |
| Unit | Critical floor 85, HIGH_RISK band, OCR-zero override | Mirror `test_scoring.py` tests under `RULESET_2026_09_06` |
| Unit | `DO_NOT_RELY_ON_RECEIPT` action mapping | Mirror `test_assessment.py` high-risk test |
| Integration | Manifest/`--check` still consistent | `python samples/generate.py --check` + existing `test_manifest_integrity.py` |
| E2E | All four bands + `ruleset_version` | `TestClient` POST per band through the real router |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or
process-integration boundary. `generate.py` is invoked manually, unchanged in its CLI surface.

## Migration / Rollout

No migration required. Revert-the-commit rollback; tests and fixture metadata only.

## Open Questions

- [ ] None blocking. `--check` alias handling (Decision 2) supersedes the proposal's claim that
      `generate.py`'s check path needs no change; flag for reviewer awareness.
