"""Versioned scoring ruleset — a frozen declarative data module, not
hardcoded weights in scoring logic.

Design decision ("Versioned ruleset as a frozen declarative data module,
not a JSON file", design.md): `ScoringRuleset` is a frozen dataclass;
concrete versions live under `domain/rulesets/` and register themselves
into `domain.rulesets.RULESETS`. `score()` (see `domain/scoring.py`) always
receives a `ScoringRuleset` instance as a parameter and never reads a
module global, so determinism is structural: same inputs + same ruleset
object -> same output.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from receipt_risk.domain.analysis import AnalyzerStatus
from receipt_risk.domain.signals import Severity, SignalCode


class Classification(StrEnum):
    LOW_RISK = "LOW_RISK"
    REVIEW_RECOMMENDED = "REVIEW_RECOMMENDED"
    SUSPICIOUS = "SUSPICIOUS"
    HIGH_RISK = "HIGH_RISK"
    INCONCLUSIVE = "INCONCLUSIVE"


class RecommendedAction(StrEnum):
    STANDARD_MANUAL_RECONCILIATION = "STANDARD_MANUAL_RECONCILIATION"
    PRIORITY_MANUAL_RECONCILIATION = "PRIORITY_MANUAL_RECONCILIATION"
    DO_NOT_RELY_ON_RECEIPT = "DO_NOT_RELY_ON_RECEIPT"


@dataclass(frozen=True, slots=True)
class ScoringRuleset:
    """A single versioned set of scoring weights. Never mutated after
    construction; `score()` receives an instance as a parameter (see
    design.md "Versioned ruleset")."""

    version: str
    weights: Mapping[SignalCode, int]
    severity_multiplier: Mapping[Severity, Decimal]
    critical_floor: Mapping[SignalCode, int]
    combination_floors: Mapping[frozenset[SignalCode], int]
    """Risk-score floors keyed by a SET of co-occurring codes. Deliberately
    severity-agnostic (unlike `critical_floor`): the targeted codes never
    reach CRITICAL, and it is the co-occurrence that carries the meaning."""
    analyzer_evidence_weights: Mapping[str, Decimal]
    status_quality: Mapping[AnalyzerStatus, Decimal]
    inconclusive_coverage_threshold: Decimal
    bands: tuple[tuple[int, Classification], ...]
