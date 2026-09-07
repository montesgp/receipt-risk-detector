"""Ruleset version `2026-09-05` — adds the combination-floor policy.

Supersedes `v2026_09_04` as the MVP1 default (scoring-confidence-calibration
change): copy-forward of every `v2026_09_04` value, plus a non-empty
`combination_floors` entry. `v2026_09_04` is kept unmodified and still
registered in `rulesets/__init__.py` so any request logged with
`ruleset_version="2026-09-04"` stays reproducible (CONTRIBUTING.md: scoring
changes bump `ruleset_version` rather than mutate a shipped one in place).

Weights, multipliers and the evidence-coverage threshold are unchanged from
`v2026_09_04` — this version's only policy delta is `combination_floors`.
"""

from __future__ import annotations

from decimal import Decimal

from receipt_risk.domain.ruleset import Classification, ScoringRuleset
from receipt_risk.domain.signals import Severity, SignalCode

_WEIGHTS: dict[SignalCode, int] = {
    SignalCode.METADATA_EDITOR_SOFTWARE: 10,
    SignalCode.VALID_AI_GENERATED_CLAIM: 90,
    SignalCode.PROVENANCE_VALIDATION_FAILED: 15,
    SignalCode.INVALID_CBU_CHECK_DIGIT: 40,
    SignalCode.INVALID_CUIT_CHECK_DIGIT: 30,
    SignalCode.AMOUNT_DATE_CONTRADICTION: 20,
    SignalCode.DATE_OUT_OF_BOUNDS: 15,
    SignalCode.CORE_FIELD_EXTRACTION_FAILED: 15,
    # A tool outage is not evidence of fraud -- it only lowers
    # `confidence_score` through `status_quality` (design.md).
    SignalCode.ANALYZER_UNAVAILABLE: 0,
    # A pixel-space outlier is weak, unbenchmarked evidence -- it can raise
    # a score, never force a verdict (no _CRITICAL_FLOOR entry below).
    SignalCode.VISUAL_ANOMALY_DETECTED: 20,
}

_SEVERITY_MULTIPLIER: dict[Severity, Decimal] = {
    Severity.INFO: Decimal("0.0"),
    Severity.LOW: Decimal("0.5"),
    Severity.MEDIUM: Decimal("1.0"),
    Severity.HIGH: Decimal("1.5"),
    Severity.CRITICAL: Decimal("2.0"),
}

_CRITICAL_FLOOR: dict[SignalCode, int] = {
    SignalCode.VALID_AI_GENERATED_CLAIM: 85,
}

# Unreadable core fields AND an implausible date is strongly consistent with
# a fabricated render, but also reachable by a bad scan of an old receipt --
# so this floors into SUSPICIOUS (PRIORITY_MANUAL_RECONCILIATION), never
# HIGH_RISK (DO_NOT_RELY_ON_RECEIPT), which stays reserved for cryptographic
# evidence (VALID_AI_GENERATED_CLAIM: 85). 55 sits clear of both band edges
# (49 / 75). A reasoned default, not a benchmarked value (design.md).
_COMBINATION_FLOORS: dict[frozenset[SignalCode], int] = {
    frozenset({SignalCode.CORE_FIELD_EXTRACTION_FAILED, SignalCode.DATE_OUT_OF_BOUNDS}): 55,
}

# Keyed by analyzer *role* (ocr/metadata/provenance/vision), not by adapter
# name (`paddleocr-onnx`/`exiftool`/`c2pa`/`mobilenetv3-embedding`) — see
# `domain/scoring.py`'s `_ADAPTER_ROLE` mapping for the adapter-name -> role
# translation. Unchanged from v2026_09_04.
_ANALYZER_EVIDENCE_WEIGHTS: dict[str, Decimal] = {
    "ocr": Decimal("0.43"),
    "metadata": Decimal("0.17"),
    "provenance": Decimal("0.25"),
    "vision": Decimal("0.15"),
}

_STATUS_QUALITY: dict[str, Decimal] = {
    "completed": Decimal("1.0"),
    "partial": Decimal("0.5"),
    "failed": Decimal("0.0"),
    "timed_out": Decimal("0.0"),
}

_BANDS: tuple[tuple[int, Classification], ...] = (
    (24, Classification.LOW_RISK),
    (49, Classification.REVIEW_RECOMMENDED),
    (74, Classification.SUSPICIOUS),
    (100, Classification.HIGH_RISK),
)

RULESET_2026_09_05 = ScoringRuleset(
    version="2026-09-05",
    weights=_WEIGHTS,
    severity_multiplier=_SEVERITY_MULTIPLIER,
    critical_floor=_CRITICAL_FLOOR,
    combination_floors=_COMBINATION_FLOORS,
    analyzer_evidence_weights=_ANALYZER_EVIDENCE_WEIGHTS,
    status_quality=_STATUS_QUALITY,
    inconclusive_coverage_threshold=Decimal("0.35"),
    bands=_BANDS,
)
