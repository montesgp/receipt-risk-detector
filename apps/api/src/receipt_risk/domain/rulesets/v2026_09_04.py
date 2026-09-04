"""Ruleset version `2026-09-04` — adds the vision analyzer role.

Supersedes `v2026_09_01` as the MVP1 default (visual-anomaly-detection
change): adds `SignalCode.VISUAL_ANOMALY_DETECTED` and rebalances
`_ANALYZER_EVIDENCE_WEIGHTS` for the new `vision` role. `v2026_09_01`
is kept unmodified and still registered in `rulesets/__init__.py` so any
request logged with `ruleset_version="2026-09-01"` stays reproducible
(CONTRIBUTING.md: scoring changes bump `ruleset_version` rather than
mutate a shipped one in place).

Weights, multipliers and the evidence-coverage threshold are reasoned
defaults, not benchmarked values (proposal.md: "reasonable defaults, not
fake precision"; design.md Open Questions). They are pinned here, not in
`domain/scoring.py`, so a future ruleset version can change them without
touching the scoring engine.
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

# Keyed by analyzer *role* (ocr/metadata/provenance/vision), not by adapter
# name (`paddleocr-onnx`/`exiftool`/`c2pa`/`mobilenetv3-embedding`) — see
# `domain/scoring.py`'s `_ADAPTER_ROLE` mapping for the adapter-name -> role
# translation.
#
# The pre-vision triple (ocr 0.50 / metadata 0.20 / provenance 0.30) is
# scaled by 0.85 and rounded to 2dp so the four roles sum to exactly 1.00
# once vision's 0.15 is added (design.md "Evidence-weight rebalance"):
# ocr rounds up (0.425 -> 0.43) and provenance rounds down (0.255 -> 0.25)
# because ocr is the only role with fractional `_completeness`.
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

RULESET_2026_09_04 = ScoringRuleset(
    version="2026-09-04",
    weights=_WEIGHTS,
    severity_multiplier=_SEVERITY_MULTIPLIER,
    critical_floor=_CRITICAL_FLOOR,
    analyzer_evidence_weights=_ANALYZER_EVIDENCE_WEIGHTS,
    status_quality=_STATUS_QUALITY,
    inconclusive_coverage_threshold=Decimal("0.35"),
    bands=_BANDS,
)
