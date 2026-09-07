# Proposal: Scoring Confidence Calibration

## Intent

Two confirmed scoring defects undermine the product's core promise (evidence-based risk, never absolute verdicts):

1. **Bug**: a non-receipt image with **zero OCR text** returns `LOW_RISK` / `STANDARD_MANUAL_RECONCILIATION`. Root cause: `domain/scoring.py::_completeness` treats any non-OCR analyzer (`provenance`, `vision`) with `status == "completed"` as full completeness (`1.0`), so `evidence_coverage` clears the `inconclusive_coverage_threshold` (0.35) even when OCR found nothing at all.
2. **Calibration**: an AI-generated receipt correctly raises `CORE_FIELD_EXTRACTION_FAILED` + `DATE_OUT_OF_BOUNDS` yet lands at ~29/100 (`REVIEW_RECOMMENDED`) — correct signals, insufficient aggregate. Both are fixed in one pass to avoid touching the ruleset twice in a row.

## Scope

### In Scope

- Fix `_completeness` for `provenance`/`vision`: "ran cleanly, found nothing" must not count as full evidence.
- Defense-in-depth hard floor in `score()`: force `INCONCLUSIVE` when OCR completeness is `0` and no other strong signal exists.
- New signal-**combination** floor on `ScoringRuleset` (generalizing the existing single-code `critical_floor`), used for `CORE_FIELD_EXTRACTION_FAILED` + `DATE_OUT_OF_BOUNDS`.
- New registered ruleset `domain/rulesets/v2026_09_05.py`; register in `rulesets/__init__.py`; repoint `bootstrap/app.py`. `v2026_09_01`/`v2026_09_04` get the new field as an **empty mapping** (frozen dataclass, no defaults) to preserve reproducibility.
- Web copy: `ScoreSummary.svelte` selects a more specific INCONCLUSIVE message when a signal carries `evidence.reason === "no_text_detected"` (already on the wire). New `en`/`es` i18n keys, hedged wording ("no pudimos identificar los datos de una transferencia en este archivo") — never an absolute verdict.
- Golden/expected-value regeneration across 9+ backend test files (visual-anomaly-detection precedent).

### Out of Scope

- New `Classification` enum value (breaking change to a documented closed enum; `INCONCLUSIVE` already covers it).
- New `SignalCode` (e.g. `NO_DOCUMENT_DETECTED`) — deferred follow-up if API/bot consumers need a documented code instead of an `evidence.reason` string.
- Raising `CORE_FIELD_EXTRACTION_FAILED` / `DATE_OUT_OF_BOUNDS` weights globally (false-alarm risk on genuinely low-quality real receipts).
- Re-litigating visual-anomaly-detection (PR #29) or generic-receipt-field-extraction (PR #31); backend schema/OpenAPI changes; the known raw-English `limitations[]`/`description` locale gap.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `receipt-analysis`: "Explainable, deterministic scoring" gains evidence-coverage/INCONCLUSIVE-floor and signal-combination-floor requirements.
- `receipt-analysis-web-client`: "Successful result display" gains a no-text-detected INCONCLUSIVE messaging scenario.

## Approach

Keep `evidence_coverage` as the primary gate but stop conflating *completed* with *informative*; add one explicit, separately-named OCR-zero floor for the exact reported bug. For calibration, reuse the proven `critical_floor` shape keyed by a frozen set of signal codes so only the co-occurrence is punished, not either signal in isolation. All behavior deltas ship inside one new ruleset version; older versions stay byte-for-byte reproducible.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `apps/api/src/receipt_risk/domain/scoring.py` | Modified | `_completeness` fix, OCR-zero floor, combination-floor application |
| `apps/api/src/receipt_risk/domain/ruleset.py` | Modified | New combination-floor field |
| `apps/api/src/receipt_risk/domain/rulesets/v2026_09_05.py` | New | Active ruleset with floors |
| `.../rulesets/{__init__,v2026_09_01,v2026_09_04}.py` | Modified | Register; empty mapping for history |
| `apps/api/src/receipt_risk/bootstrap/app.py` | Modified | Repoint active ruleset |
| `apps/web/.../ScoreSummary.svelte`, `i18n/messages/{en,es}.json` | Modified | Specific INCONCLUSIVE copy |
| `apps/api/tests/**`, `apps/web/tests/unit/key-parity.test.ts` | Modified | Golden regeneration, key parity |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Legitimate low-quality receipts flip to `INCONCLUSIVE` | High | Golden fixture for "real receipt, no C2PA, partial OCR" alongside the zero-text case |
| Combination floor over-punishes a real bad scan with an odd date | Med | Floor targets co-occurrence only; band chosen conservatively, documented as a reasoned default |
| Frontend couples to undocumented `evidence.reason` | Med | Documented as a soft contract; promotable to a real `SignalCode` follow-up |
| Wide golden surface silently missed | Med | Dedicated test-update work unit, not incidental fixups |
| Ruleset dataclass change alters historical runs | Low | Empty mapping for `v2026_09_01`/`v2026_09_04`, asserted in tests |

## Rollback Plan

Config-first: repoint `bootstrap/app.py` back to `RULESET_2026_09_04` to restore prior scores exactly (the new ruleset stays registered and inert). Full revert is a single commit revert; the `ScoringRuleset` field and web copy are additive and independently revertible.

## Dependencies

- None external. Builds on merged PR #29 and in-review PR #31.

## Success Criteria

- [ ] Zero-OCR-text image returns `INCONCLUSIVE` / `PRIORITY_MANUAL_RECONCILIATION`, never `LOW_RISK`.
- [ ] `CORE_FIELD_EXTRACTION_FAILED` + `DATE_OUT_OF_BOUNDS` co-occurrence lands in a clearly alarming band; either signal alone keeps today's score.
- [ ] A real receipt with partial OCR and no C2PA keeps its prior classification.
- [ ] `v2026_09_01` / `v2026_09_04` reproduce their previous outputs exactly.
- [ ] Web shows the specific hedged `no_text_detected` message in `es` and `en`; no forbidden authenticity language.
