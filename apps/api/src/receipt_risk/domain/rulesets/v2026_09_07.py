"""Ruleset version `2026-09-07` -- prices the metadata TC260 AI-claim.

Supersedes `v2026_09_06` as the MVP1 default (metadata-aigc-claim-detection
change): copy-forward of every `v2026_09_06` value, plus a weight and a
critical floor for the new `METADATA_AI_GENERATED_CLAIM` code -- found via a
real Qwen-generated fake receipt that scored `LOW_RISK` (5/100) because the
`exiftool` adapter only ever checked `Software`/`CreatorTool`, ignoring the
XMP-TC260 `Aigc` tag Qwen writes to declare AI generation. `v2026_09_06` is
kept unmodified and still registered in `rulesets/__init__.py` so any request
logged with `ruleset_version="2026-09-06"` stays reproducible
(CONTRIBUTING.md: scoring changes bump `ruleset_version` rather than mutate a
shipped one in place).

Multipliers, bands, evidence weights, status quality, the coverage threshold
and `combination_floors` are unchanged from `v2026_09_06` -- this version's
only policy delta is the two new entries for the new code.
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
    # A cryptographically intact AI-generation claim from an unrecognized CA
    # is still direct evidence of AI generation -- only the trust anchor is
    # unfamiliar, not the claim. int(50 * 2.0 * 0.85) == 85, which already
    # lands in HIGH_RISK unaided; the floor below restates it for safety
    # under future retuning. Priced below VALID_AI_GENERATED_CLAIM's 90 so
    # the audit trail keeps a numeric trace of the trust gap even though the
    # verdict is identical.
    SignalCode.AI_GENERATED_CLAIM_UNTRUSTED_SIGNER: 50,
    # A TC260 `Aigc` self-declaration is unsigned EXIF/XMP data (unlike
    # C2PA's cryptographic manifest), so it is priced like the
    # untrusted-signer claim above rather than the fully-trusted one:
    # int(50 * 2.0 * 0.90) == 90, and the floor below restates 85 for safety
    # under future retuning.
    SignalCode.METADATA_AI_GENERATED_CLAIM: 50,
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
    SignalCode.AI_GENERATED_CLAIM_UNTRUSTED_SIGNER: 85,
    SignalCode.METADATA_AI_GENERATED_CLAIM: 85,
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
# translation. Unchanged from v2026_09_06.
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

RULESET_2026_09_07 = ScoringRuleset(
    version="2026-09-07",
    weights=_WEIGHTS,
    severity_multiplier=_SEVERITY_MULTIPLIER,
    critical_floor=_CRITICAL_FLOOR,
    combination_floors=_COMBINATION_FLOORS,
    analyzer_evidence_weights=_ANALYZER_EVIDENCE_WEIGHTS,
    status_quality=_STATUS_QUALITY,
    inconclusive_coverage_threshold=Decimal("0.35"),
    bands=_BANDS,
)
