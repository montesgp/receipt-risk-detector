# Design: Scoring Confidence Calibration

## Technical Approach

Three layered corrections, all inside `domain/`, with a single new active ruleset version:

1. **Evidence honesty** — `_completeness` stops equating `status == "completed"` with "informative" for the `provenance` role. The C2PA adapter reports whether a manifest actually existed via a new optional `AnalyzerResult.evidence_observed` flag.
2. **Defense-in-depth floor** — `score()` forces `INCONCLUSIVE` when OCR extracted zero core fields, unless a verdict-grade signal fired.
3. **Combination floor** — `ScoringRuleset` gains `combination_floors`, keyed by `frozenset[SignalCode]`, applied in `_risk_score` with the same `max()` pattern as `critical_floor`.

## Architecture Decisions

### Decision: The shared-code fix applies retroactively to ALL ruleset versions (the central question)

**Choice**: Fix `_completeness` unconditionally in `domain/scoring.py`. Do **not** make it version-aware. Bump `ENGINE_VERSION` in `application/analyze_receipt.py` from `"0.1.0"` to `"0.2.0"`.

**Alternatives considered**:
| Option | Tradeoff | Verdict |
|---|---|---|
| Version-gate on `ruleset.version` inside `scoring.py` | Directly violates the module's locked doctrine ("never reads a module global — `ruleset` fully parameterizes the computation"); a version `if` is exactly that hidden global | Rejected |
| New per-version `completeness_strategy` field on `ScoringRuleset` | Leaks engine *formulas* into the data module; v2026_09_04's docstring pins the split explicitly ("weights pinned here, not in `domain/scoring.py`"). Also permanently preserves a defect | Rejected |
| Unconditional fix + `ENGINE_VERSION` bump | Historical replays of `2026-09-01` under engine `0.2.0` differ from engine `0.1.0` | **Chosen** |

**Rationale**: `AnalyzeResponse` already carries **both** `engine_version` and `ruleset_version` (`adapters/api/schemas.py`), so the reproducibility contract is already the *pair*, not `ruleset_version` alone. The restated promise: **same `(engine_version, ruleset_version)` + same input → same output.** `ruleset_version` freezes *policy* (weights, floors, thresholds, bands); `ENGINE_VERSION` freezes *formulas*. CONTRIBUTING.md's "never mutate a shipped ruleset" governs the data object, which this change honours (v2026_09_01/v2026_09_04 keep every existing value and receive only an **empty** `combination_floors`). Freezing defects per ruleset version would require the engine to carry an unbounded switchboard of historical bugs, and every future engine fix would inherit the same gate. A defect fix in shared logic *should* apply retroactively; a deliberate policy change must not — hence the policy change ships only in `v2026_09_05`.

### Decision: Only `provenance` needs the completeness fix; `vision` and `metadata` are already correct

**Choice**: `_completeness` keeps status-based `1.0` for `vision` and `metadata`; only `provenance` can report `0` on a clean run.

**Rationale**: `mobilenet_embedder.py` always computes an embedding and takes a nearest-neighbour cosine distance against the reference set whenever it reaches `status == "completed"`; "no `VISUAL_ANOMALY_DETECTED`" is a *positive determination* ("within known-template distance"), i.e. real evidence. `exiftool.py` likewise always reads the EXIF/XMP block. `c2pa_reader.py` is the outlier: `_read_manifest` returning `None` (no manifest, or an undecodable one) still yields `status="completed"` while nothing whatsoever was evaluated. That is the exact conflation the bug report hit.

**Highest-flagged risk, quantified**: for a genuine receipt photo with no C2PA (the common case), provenance now contributes `0` instead of `0.25`. Remaining coverage is `metadata 0.17 + vision 0.15 = 0.32`, just under the `0.35` threshold. One single OCR core field adds `0.43 / 4 = 0.1075` → `0.4275` → conclusive. So the fix resolves to a precise, defensible rule: **a real receipt stays conclusive if it yields at least one core field, or carries a C2PA manifest.** A file that yields neither is genuinely inconclusive. No new tuning constant is introduced.

### Decision: "Strong signal" that overrides the OCR-zero floor = an active critical-floor signal

**Choice**: The floor is overridden when a fired signal is `Severity.CRITICAL` **and** its code has an entry in `ruleset.critical_floor` — the identical predicate `_risk_score` already uses. Today that is exactly `VALID_AI_GENERATED_CLAIM`.

**Rationale**: Reuses the codebase's existing, already-versioned definition of "evidence strong enough to force a verdict on its own"; introduces no new concept and no new ruleset field, and stays version-parameterized (a future ruleset can add entries without touching `scoring.py`). Concretely: an AI-generated image with zero readable text and a validating C2PA manifest must stay `HIGH_RISK` / `DO_NOT_RELY_ON_RECEIPT` — downgrading cryptographic provenance evidence to `INCONCLUSIVE` would be a regression.

**Scope containment**: the override applies **only** to the new OCR-zero floor. The pre-existing `evidence_coverage < threshold` gate is left byte-identical (still unconditional), so no currently-passing classification flips through this branch.

### Decision: `{CORE_FIELD_EXTRACTION_FAILED, DATE_OUT_OF_BOUNDS}` floors at **55** → `SUSPICIOUS`

**Choice**: `55`. Bands are `≤24 LOW`, `≤49 REVIEW_RECOMMENDED`, `≤74 SUSPICIOUS`, `≤100 HIGH_RISK`.

**Alternatives considered**: `75+` (`HIGH_RISK`) — rejected; `HIGH_RISK` maps to `DO_NOT_RELY_ON_RECEIPT`, effectively an absolute verdict, and the product's core promise forbids that on circumstantial evidence. The only existing floor at that strength is `VALID_AI_GENERATED_CLAIM: 85`, backed by a *cryptographic* claim. `50` — rejected as sitting one point off the band edge, where a severity-multiplier change could silently re-cross it.

**Rationale (reasoned default, not benchmarked — same stance as `_CRITICAL_FLOOR` and `_EDITOR_SOFTWARE_MARKERS`)**: unreadable core fields *plus* an implausible date is strongly consistent with a fabricated render, but also reachable by a badly-scanned old receipt. `SUSPICIOUS` → `PRIORITY_MANUAL_RECONCILIATION` is the honest response: escalate the human check, assert nothing. `55` sits 6 points clear of the `49` boundary and 20 clear of `75`, so the floor can never *by itself* reach `HIGH_RISK`, while additional signals can still push the total there.

### Decision: `evidence_observed` on `AnalyzerResult`, not an `ExtractedField` marker

**Choice**: add `evidence_observed: bool | None = None` (last field, after `error_code`) to the frozen `AnalyzerResult`.

**Alternatives considered**: encoding a synthetic `ExtractedField(name="c2pa_manifest", ...)` — rejected as semantic abuse of an OCR-shaped type; returning `status="partial"` from the C2PA adapter — rejected: it corrupts the `AnalyzerStatus` vocabulary, leaks into `AnalyzerStatusModel` in the API response, and arithmetically fails to fix the bug (`0.17 + 0.125 + 0.15 = 0.445`, still above `0.35`).

**Rationale**: `None` means "not reported → fall back to status", so `exiftool`, `paddleocr-onnx` and `mobilenetv3-embedding` need **zero** changes. `AnalyzerStatusModel` serializes only `analyzer`/`status`/`duration_ms`, and `mappers._extracted_data` reads only the OCR analyzer, so **no API schema or OpenAPI change** results.

## Data Flow

    c2pa_reader.inspect ──→ AnalyzerResult(evidence_observed = manifest is not None)
                                     │
    paddleocr / exiftool / vision ────┼──→ score(signals, statuses, ruleset)
                                     │        │
                                     │        ├─ _evidence_coverage → _completeness (provenance fix)
                                     │        ├─ _risk_score → critical_floor, then combination_floors
                                     │        └─ OCR-zero floor  ─ unless _verdict_signals(...)
                                     ▼
                            ScoreBreakdown → assessment → mappers → AnalyzeResponse
                                                                          │
                                     signals[].evidence.reason ──────────▶ ResultView → ScoreSummary

## File Changes

| File | Action | Description |
|---|---|---|
| `apps/api/src/receipt_risk/domain/analysis.py` | Modify | `AnalyzerResult.evidence_observed: bool \| None = None` |
| `apps/api/src/receipt_risk/domain/scoring.py` | Modify | `_completeness` provenance fix; `_verdict_signals`; `_ocr_core_fields_empty`; combination floor in `_risk_score`; OCR-zero branch in `score()` |
| `apps/api/src/receipt_risk/domain/ruleset.py` | Modify | New `combination_floors` field after `critical_floor` |
| `apps/api/src/receipt_risk/domain/rulesets/v2026_09_05.py` | Create | Copy-forward of v2026_09_04 + `_COMBINATION_FLOORS` |
| `.../rulesets/v2026_09_01.py`, `.../v2026_09_04.py` | Modify | Explicit `combination_floors={}` (frozen dataclass, no defaults) |
| `.../rulesets/__init__.py` | Modify | Register `RULESET_2026_09_05` |
| `apps/api/src/receipt_risk/bootstrap/app.py` | Modify | Import + wire `RULESET_2026_09_05` (3 sites: use case, `/version`) |
| `apps/api/src/receipt_risk/adapters/provenance/c2pa_reader.py` | Modify | Set `evidence_observed=manifest is not None`; docstring note |
| `apps/api/src/receipt_risk/application/analyze_receipt.py` | Modify | `ENGINE_VERSION = "0.2.0"` |
| `apps/web/src/lib/components/ResultView.svelte` | Modify | Derive `noTextDetected`, pass to `ScoreSummary` |
| `apps/web/src/lib/components/ScoreSummary.svelte` | Modify | `noTextDetected` prop selects the note key |
| `apps/web/src/lib/i18n/messages/{es,en}.json` | Modify | New `result.inconclusiveNoTextNote` key |

## Interfaces / Contracts

```python
# domain/analysis.py — additive, last field
evidence_observed: bool | None = None
"""Did this analyzer actually have something to evaluate? `None` = not
reported (fall back to `status`). Only `provenance` reports it today:
a clean C2PA run with no manifest observed nothing."""

# domain/ruleset.py — after `critical_floor`
combination_floors: Mapping[frozenset[SignalCode], int]
"""Risk-score floors keyed by a SET of co-occurring codes. Deliberately
severity-agnostic (unlike `critical_floor`): the targeted codes never
reach CRITICAL, and it is the co-occurrence that carries the meaning."""

# domain/scoring.py
def _completeness(role: str, result: AnalyzerResult) -> Decimal:
    if role != "ocr":
        if result.status != "completed" or result.evidence_observed is False:
            return Decimal("0")
        return Decimal("1")
    ...  # unchanged core-field fraction

def _verdict_signals(signals, ruleset) -> list[int]:
    """Signals strong enough to force a verdict alone: CRITICAL severity
    with a `critical_floor` entry. Shared by `_risk_score` and `score()`."""

def _ocr_core_fields_empty(statuses: Sequence[AnalyzerResult]) -> bool:
    """True when an ocr-role result is present and yielded zero core fields."""

def _risk_score(signals, ruleset) -> int:
    total = min(100, sum(...))
    floors = _verdict_signals(signals, ruleset)
    fired = {s.code for s in signals}
    floors += [f for codes, f in ruleset.combination_floors.items() if codes <= fired]
    if floors:
        total = max(total, max(floors))
    return min(100, total)
```

```python
# domain/rulesets/v2026_09_05.py
_COMBINATION_FLOORS: dict[frozenset[SignalCode], int] = {
    # Unreadable core fields AND an implausible date is strongly consistent
    # with a fabricated render, but also reachable by a bad scan of an old
    # receipt -- so this floors into SUSPICIOUS (PRIORITY_MANUAL_
    # RECONCILIATION), never HIGH_RISK (DO_NOT_RELY_ON_RECEIPT), which stays
    # reserved for cryptographic evidence (VALID_AI_GENERATED_CLAIM: 85).
    # 55 sits clear of both band edges (49 / 75). A reasoned default, not a
    # benchmarked value.
    frozenset({SignalCode.CORE_FIELD_EXTRACTION_FAILED, SignalCode.DATE_OUT_OF_BOUNDS}): 55,
}
```

```svelte
<!-- ResultView.svelte (container) -->
const noTextDetected = $derived(
  result.signals.some(
    (s) => s.code === 'CORE_FIELD_EXTRACTION_FAILED' && s.evidence?.reason === 'no_text_detected'
  )
);

<!-- ScoreSummary.svelte (presentational) -->
let { /* ... */ noTextDetected = false }: { /* ... */ noTextDetected?: boolean } = $props();
const inconclusiveKey = $derived(
  noTextDetected ? 'result.inconclusiveNoTextNote' : 'result.inconclusiveNote'
);
```

**i18n** (Spanish primary, English mirror; inserted directly after `result.inconclusiveNote` at line 149 in both files). Replaces, not augments — the string already carries the confidence and priority sentences:

- `es`: `"result.inconclusiveNoTextNote": "No pudimos identificar los datos de una transferencia en este archivo. La confianza del análisis ({confidence}%) es baja; priorizá la conciliación manual."`
- `en`: `"result.inconclusiveNoTextNote": "We could not identify transfer data in this file. The analysis confidence ({confidence}%) is low; prioritize manual reconciliation."`

Never "this is not a transfer" / "no es un comprobante" — hedged phrasing only, per the no-absolute-verdict rule.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | `_completeness` provenance `evidence_observed=False` → `0`; vision/metadata unchanged at `1` | `tests/unit/test_scoring.py` |
| Unit | **(a)** zero-OCR + no manifest → `INCONCLUSIVE` (coverage `0.32`); the OCR-zero floor also fires independently | `test_scoring.py` new fixtures |
| Unit | **(b)** real receipt, 1/4 core fields, no C2PA → coverage `0.43`, classification **unchanged** (regression guard for the top risk) | `test_scoring.py` |
| Unit | Zero-OCR + valid AI claim → stays `HIGH_RISK` (verdict-signal override) | `test_scoring.py` |
| Unit | **(c)** combination floor: both codes → `55`; each alone → today's score; empty mapping is a no-op | `test_scoring.py`, `test_ruleset.py` |
| Unit | `v2026_09_01`/`v2026_09_04` assert `combination_floors == {}`; `RULESETS` has 3 entries; `v2026_09_05.version == "2026-09-05"` | `test_ruleset.py` |
| Unit | `C2paProvenanceAdapter` sets `evidence_observed` True/False | `tests/unit/test_c2pa_reader.py` |
| Unit | Golden regeneration (`risk_score`, `confidence_score`, `classification`, `ruleset_version` → `2026-09-05`, `engine_version` → `0.2.0`) | `test_assessment.py`, `test_analyze_receipt.py`, `test_api_schemas.py`, `test_api_error_contract.py`, `test_router.py`, `test_log_privacy.py` |
| Integration | End-to-end response carries the new ruleset/engine versions and floored scores | `tests/integration/test_analyze_endpoint_e2e.py` |
| Unit (web) | **(d)** `INCONCLUSIVE` + `no_text_detected` renders the hedged copy; `INCONCLUSIVE` without it renders the generic note; non-`INCONCLUSIVE` renders neither | `tests/unit/ScoreSummary.test.ts`, `ResultView.test.ts` |
| Unit (web) | `es`/`en` key parity for the new key; no forbidden authenticity language | `tests/unit/key-parity.test.ts`, `literal-audit.test.ts` |

Golden values must be **recomputed by hand from the formulas and pasted**, not copied from a failing run — the visual-anomaly-detection precedent.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary is added or altered. The existing ExifTool subprocess surface is untouched.

## Migration / Rollout

No data migration. Rollout is config-first: `bootstrap/app.py` selects the active ruleset. Rollback = repoint to `RULESET_2026_09_04` (one line, three sites); the new ruleset stays registered and inert. Note that the `_completeness` fix and `ENGINE_VERSION` bump are **not** covered by that rollback (shared engine code, by design — see the first decision); a full revert of the defect fix requires reverting the commit.

## Open Questions

- [ ] None blocking. `evidence.reason` remains a documented **soft** contract between backend and web; promoting it to a real `SignalCode` (e.g. `NO_DOCUMENT_DETECTED`) is the deferred follow-up already recorded as out of scope.
