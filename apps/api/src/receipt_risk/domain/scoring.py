"""Pure risk-score / evidence-coverage scoring engine.

Traces to design.md's "Domain — ruleset and scoring" formulas. All
arithmetic is `Decimal`, never `float`; `int()` truncation happens only at
the final step, so the result is bit-for-bit reproducible for a given
ruleset object (design.md's "Deterministic score for identical input"
scenario).

`INCONCLUSIVE` is a single whole-request evidence-coverage number computed
across ALL analyzers together — there is no per-analyzer override anywhere
in this module (the exact bug the product owner locked out, proposal.md).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

from receipt_risk.domain.analysis import AnalyzerResult
from receipt_risk.domain.ruleset import Classification, ScoringRuleset
from receipt_risk.domain.signals import Severity, ValidationSignal

# The four core fields the OCR completeness formula is computed over.
# Deliberately duplicated from `adapters/ocr/field_parsers.CORE_FIELD_NAMES`
# rather than imported: domain/ must never import adapters/ (documented
# apply-time deviation — both tuples must be kept in sync by hand).
_CORE_FIELD_NAMES: tuple[str, ...] = ("amount", "destination_cbu", "cuit", "date_time")

# Adapter name (AnalyzerResult.analyzer) -> analyzer *role* used as the key
# into `ScoringRuleset.analyzer_evidence_weights`. Scoring reasons about
# roles (ocr/metadata/provenance), never concrete adapter implementations.
_ADAPTER_ROLE: Mapping[str, str] = {
    "paddleocr-onnx": "ocr",
    "exiftool": "metadata",
    "c2pa": "provenance",
    "mobilenetv3-embedding": "vision",
}


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    risk_score: int
    confidence_score: int
    classification: Classification
    evidence_coverage: Decimal


def signal_contribution(signal: ValidationSignal, ruleset: ScoringRuleset) -> int:
    """`int(weight * severity_multiplier * confidence)` for one signal under
    `ruleset` — public so `domain/assessment.py` can fill each returned
    signal's `score_contribution` (design.md: "filled by the scorer, not by
    adapters")."""
    weight = Decimal(ruleset.weights.get(signal.code, 0))
    multiplier = ruleset.severity_multiplier[signal.severity]
    return int(weight * multiplier * signal.confidence)


def _risk_score(signals: Sequence[ValidationSignal], ruleset: ScoringRuleset) -> int:
    total = min(100, sum(signal_contribution(signal, ruleset) for signal in signals))
    critical_floors = [
        ruleset.critical_floor[signal.code]
        for signal in signals
        if signal.severity is Severity.CRITICAL and signal.code in ruleset.critical_floor
    ]
    if critical_floors:
        total = max(total, max(critical_floors))
    return min(100, total)


def _completeness(role: str, result: AnalyzerResult) -> Decimal:
    if role != "ocr":
        return Decimal("1") if result.status == "completed" else Decimal("0")
    hits = sum(
        1
        for field in result.extracted_fields
        if field.name in _CORE_FIELD_NAMES and field.normalized is not None
    )
    return Decimal(hits) / Decimal(len(_CORE_FIELD_NAMES))


def _evidence_coverage(results: Sequence[AnalyzerResult], ruleset: ScoringRuleset) -> Decimal:
    coverage = Decimal("0")
    for result in results:
        role = _ADAPTER_ROLE.get(result.analyzer)
        if role is None:
            continue
        weight = ruleset.analyzer_evidence_weights.get(role, Decimal("0"))
        quality = ruleset.status_quality.get(result.status, Decimal("0"))
        coverage += weight * quality * _completeness(role, result)
    return coverage.quantize(Decimal("0.01"))


def _band_for(risk_score: int, ruleset: ScoringRuleset) -> Classification:
    for threshold, classification in ruleset.bands:
        if risk_score <= threshold:
            return classification
    return ruleset.bands[-1][1]


def score(
    signals: Sequence[ValidationSignal],
    statuses: Sequence[AnalyzerResult],
    ruleset: ScoringRuleset,
) -> ScoreBreakdown:
    """Compute the deterministic `(risk_score, confidence_score,
    classification)` triple for one request. Never reads a module global —
    `ruleset` fully parameterizes the computation."""
    risk_score_value = _risk_score(signals, ruleset)
    evidence_coverage = _evidence_coverage(statuses, ruleset)
    confidence_score = int(Decimal(100) * evidence_coverage)

    if evidence_coverage < ruleset.inconclusive_coverage_threshold:
        classification = Classification.INCONCLUSIVE
    else:
        classification = _band_for(risk_score_value, ruleset)

    return ScoreBreakdown(
        risk_score=risk_score_value,
        confidence_score=confidence_score,
        classification=classification,
        evidence_coverage=evidence_coverage,
    )
