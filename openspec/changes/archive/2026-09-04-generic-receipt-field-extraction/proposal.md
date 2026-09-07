# Proposal: Generic (label-independent) receipt field extraction

## Intent

`adapters/ocr/field_parsers.py` only recognizes the synthetic label vocabulary from `samples/generate.py` ("monto", "cbu destino", "cuit", "fecha y hora") in a label-above/value-below layout. Verified against a real Mercado Pago receipt: OCR read all text correctly at high confidence, yet **0/4 core fields matched**. Real banks use different wording, inline `label: value`, or no label at all — so extraction fails on effectively every real receipt, not just Mercado Pago. Every fixture reuses one vocabulary, so this bug class was structurally invisible to existing tests.

## Scope

### In Scope
- Rewrite core-field extraction to be **vocabulary-independent**: detect by value shape + validator, never by matching a label.
- CUIT/CUIL: boundary-anchored 11-digit candidates validated by existing `domain.financial.cuit.validate_cuit`.
- CBU/CVU: boundary-anchored 22-digit candidates validated by existing `domain.financial.cbu.validate_cbu`.
- Amount: currency-pattern scan (AR and US separator conventions) via existing `domain.financial.money.normalize_amount`.
- Date/time: widest practical coverage via `python-dateutil` (`dayfirst=True`), preceded by a month-typo normalization pass for OCR artifacts (e.g. `ag0sto` → `agosto`), backstopped by existing `domain.financial.dates.is_within_date_bounds`.
- Origin-vs-destination disambiguation that **selects among already-valid candidates only**.
- New fixtures in `samples/generate.py` / `samples/manifest.json` proving genericity.
- Add `python-dateutil` to `apps/api/pyproject.toml`.

### Out of Scope
- Non-Argentine identifier formats — CUIT (11-digit mod-11) and CBU (22-digit mod-10) stay Argentina-specific. This change is about wording independence, not country scope.
- Anything from merged PR #29 (vision adapter, ruleset weights).
- Extraction of non-core fields (names, institution, operation ID).
- Changes to `ExtractedField`, scoring/completeness, signals, or `application/financial_validation.py`.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `receipt-analysis`: the "Local OCR extraction" requirement must state that core-field extraction is independent of issuer label wording and layout, and that exactly one destination CBU and one destination CUIT are emitted when several candidates exist.

## Approach

1. **Detect by validation, not by label.** Scan every OCR text box for shape-valid candidates; checksum/normalizer success is the detection signal.
2. **Labels are used only to disambiguate.** Keywords ("destino", "beneficiario", …) choose *which* valid candidate is the destination; they never decide whether a candidate exists. Order: single-candidate fast path → keyword proximity → positional fallback (origin first, destination second, per the one confirmed real sample). Collapse to exactly one `ExtractedField` per name, so `detect_contradictions` cannot spuriously fire.
3. **Locked resolution of the exploration's open fork.** Checksum validity gates *selection among multiple candidates only*. When a field slot has exactly **one** candidate, it is surfaced with `normalized` populated even if the checksum fails. This preserves the existing `invalid_cbu_check_digit` fixture and keeps `INVALID_CBU_CHECK_DIGIT` / `INVALID_CUIT_CHECK_DIGIT` detection as `financial_validation.py`'s job, unchanged.
4. **Prove genericity with new fixtures**: distinct label vocabulary; inline `label: value`; no-label; two CBU/CUIT pairs; typo'd month name.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `apps/api/src/receipt_risk/adapters/ocr/field_parsers.py` | Modified | Replace label-map + nearest-below pairing with validator-driven scanning and disambiguation |
| `apps/api/tests/unit/test_ocr_field_parsers.py` | Modified | New cases: inline, no-label, alt date formats, two-pair disambiguation |
| `samples/generate.py`, `samples/manifest.json` | Modified | New real-world-shaped templates + regenerated sha256 digests |
| `apps/api/pyproject.toml` | Modified | Add `python-dateutil` (adapters/** already has `TID251` per-file-ignore) |
| `openspec/specs/receipt-analysis/spec.md` | Modified | Delta for label-independent extraction |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Stray 11-digit run (phone, order ID) passes mod-11 by chance (~9–10%) | Med | Word/punctuation-boundary anchoring; keyword proximity as tie-break; CBU collision far lower (~1%) |
| `dayfirst=True` misparses a genuinely US-formatted date | Med | AR-first is the stated domain; `is_within_date_bounds` backstop; explicit format-priority tests |
| Positional fallback backwards for a bank listing destination first | Med | Keyword signal always wins; fallback used only when no candidate has keyword context |
| Fixture regeneration produces a large binary diff | High | Isolate fixture regeneration as its own task/commit slice |

## Rollback Plan

Single-commit revert of `field_parsers.py`, its tests, the fixture/manifest regeneration, and the `pyproject.toml` dependency line. No persisted data, no API contract change, no migration — `ExtractedField` output shape is identical before and after, so all downstream consumers are unaffected by a revert.

## Dependencies

- `python-dateutil` (pure-Python, no C extension) added to `apps/api` runtime dependencies.

## Success Criteria

- [ ] All 4 core fields extract from a Mercado-Pago-shaped receipt whose wording appears nowhere in the code.
- [ ] Extraction succeeds for inline `label: value` and for no-label layouts.
- [ ] With two CBU/CUIT pairs present, exactly one `destination_cbu` and one `cuit` field are emitted, and they are the destination ones.
- [ ] `ag0sto`-style OCR-typo month dates parse correctly.
- [ ] The existing `invalid_cbu_check_digit` fixture still yields `INVALID_CBU_CHECK_DIGIT` + `REVIEW_RECOMMENDED` (no behavior change).
- [ ] No changes required in `domain/analysis.py`, `domain/scoring.py`, `domain/signals.py`, `application/financial_validation.py`, or `adapters/ocr/paddle_onnx.py`.
