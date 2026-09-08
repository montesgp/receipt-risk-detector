"""`FraudAssessment` assembly — the final domain object returned by the use
case, mirroring `docs/API.md` §3 field-for-field (transport mapping happens
in `adapters/api/mappers.py`, never here).
"""

from __future__ import annotations

import dataclasses
from collections.abc import Sequence
from dataclasses import dataclass

from receipt_risk.domain.analysis import AnalyzerResult
from receipt_risk.domain.ruleset import Classification, RecommendedAction, ScoringRuleset
from receipt_risk.domain.scoring import score, signal_contribution
from receipt_risk.domain.signals import ValidationSignal

LIMITATION_STATEMENT = (
    "This assessment analyzes the submitted artifact and does not confirm "
    "that a bank transfer exists or was credited."
)

# metadata-aigc-claim-detection follow-up: found via a real AI-edited receipt
# (ChatGPT/gpt-image) that scored LOW_RISK once sent through WhatsApp, which
# strips the C2PA manifest that made the same file score HIGH_RISK
# unmodified. Provenance metadata and checksum tampering are the only signals
# strong enough to force a verdict today; an edit that touches neither (no
# metadata survives transport, no CBU/CUIT digit corrupted) leaves no signal
# for this engine to detect. Always present, not just on LOW_RISK: the
# absence of contrary evidence is exactly the blind spot, so there is no
# reliable per-result condition to gate this on.
DETECTION_CEILING_STATEMENT = (
    "A LOW_RISK classification does not rule out an edit that leaves no "
    "detectable trace (no surviving provenance metadata, no corrupted "
    "check digit) -- confirm high-value transfers through another channel."
)

_ACTION_BY_CLASSIFICATION: dict[Classification, RecommendedAction] = {
    Classification.LOW_RISK: RecommendedAction.STANDARD_MANUAL_RECONCILIATION,
    Classification.REVIEW_RECOMMENDED: RecommendedAction.STANDARD_MANUAL_RECONCILIATION,
    Classification.SUSPICIOUS: RecommendedAction.PRIORITY_MANUAL_RECONCILIATION,
    Classification.INCONCLUSIVE: RecommendedAction.PRIORITY_MANUAL_RECONCILIATION,
    Classification.HIGH_RISK: RecommendedAction.DO_NOT_RELY_ON_RECEIPT,
}


@dataclass(frozen=True, slots=True)
class FraudAssessment:
    analysis_id: str
    engine_version: str
    ruleset_version: str
    classification: Classification
    risk_score: int
    confidence_score: int
    recommended_action: RecommendedAction
    signals: tuple[ValidationSignal, ...]
    analyzer_statuses: tuple[AnalyzerResult, ...]
    limitations: tuple[str, ...]
    duration_ms: int


def assemble(
    *,
    analysis_id: str,
    results: Sequence[AnalyzerResult],
    signals: Sequence[ValidationSignal],
    ruleset: ScoringRuleset,
    engine_version: str,
    duration_ms: int,
) -> FraudAssessment:
    """Score `signals`/`results` under `ruleset` and assemble the final,
    immutable `FraudAssessment`. Pure: no I/O, no clock reads (the caller
    supplies `duration_ms`)."""
    breakdown = score(signals, results, ruleset)
    scored_signals = tuple(
        dataclasses.replace(signal, score_contribution=signal_contribution(signal, ruleset))
        for signal in signals
    )
    return FraudAssessment(
        analysis_id=analysis_id,
        engine_version=engine_version,
        ruleset_version=ruleset.version,
        classification=breakdown.classification,
        risk_score=breakdown.risk_score,
        confidence_score=breakdown.confidence_score,
        recommended_action=_ACTION_BY_CLASSIFICATION[breakdown.classification],
        signals=scored_signals,
        analyzer_statuses=tuple(results),
        limitations=(LIMITATION_STATEMENT, DETECTION_CEILING_STATEMENT),
        duration_ms=duration_ms,
    )
