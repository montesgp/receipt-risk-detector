"""Tests for `domain/ruleset.py` and `domain/rulesets/v2026_09_01.py`.

Traces to design.md's "Versioned ruleset as a frozen declarative data
module" decision: `ScoringRuleset` is a frozen dataclass keyed by version
string in a registry, never hardcoded weights in scoring logic.
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal

from receipt_risk.domain.ruleset import Classification, RecommendedAction, ScoringRuleset
from receipt_risk.domain.rulesets import RULESETS
from receipt_risk.domain.rulesets.v2026_09_01 import RULESET_2026_09_01
from receipt_risk.domain.signals import Severity, SignalCode


def test_scoring_ruleset_is_frozen_dataclass_keyed_by_version() -> None:
    assert dataclasses.is_dataclass(ScoringRuleset)
    assert ScoringRuleset.__dataclass_params__.frozen is True
    assert RULESET_2026_09_01.version == "2026-09-01"
    assert RULESETS[RULESET_2026_09_01.version] is RULESET_2026_09_01


def test_ruleset_declares_weights_for_every_defined_signal_code() -> None:
    for code in SignalCode:
        assert code in RULESET_2026_09_01.weights, f"missing weight for {code}"


def test_ruleset_declares_severity_multiplier_for_every_severity() -> None:
    for severity in Severity:
        assert severity in RULESET_2026_09_01.severity_multiplier


def test_ruleset_analyzer_evidence_weights_sum_to_one() -> None:
    total = sum(RULESET_2026_09_01.analyzer_evidence_weights.values())
    assert total == Decimal("1.00")


def test_evidence_weights_sum_to_one_across_four_roles() -> None:
    weights = RULESET_2026_09_01.analyzer_evidence_weights
    assert set(weights) == {"ocr", "metadata", "provenance", "vision"}
    assert weights["ocr"] == Decimal("0.43")
    assert weights["metadata"] == Decimal("0.17")
    assert weights["provenance"] == Decimal("0.25")
    assert weights["vision"] == Decimal("0.15")
    assert sum(weights.values()) == Decimal("1.00")


def test_visual_anomaly_detected_weight_20_no_critical_floor_entry() -> None:
    assert RULESET_2026_09_01.weights[SignalCode.VISUAL_ANOMALY_DETECTED] == 20
    assert SignalCode.VISUAL_ANOMALY_DETECTED not in RULESET_2026_09_01.critical_floor


def test_ruleset_inconclusive_threshold_is_decimal() -> None:
    assert RULESET_2026_09_01.inconclusive_coverage_threshold == Decimal("0.35")


def test_ruleset_bands_are_ordered_ascending() -> None:
    thresholds = [threshold for threshold, _classification in RULESET_2026_09_01.bands]
    assert thresholds == sorted(thresholds)
    assert thresholds[-1] == 100


def test_classification_and_recommended_action_enums_match_docs_api() -> None:
    assert {c.value for c in Classification} == {
        "LOW_RISK",
        "REVIEW_RECOMMENDED",
        "SUSPICIOUS",
        "HIGH_RISK",
        "INCONCLUSIVE",
    }
    assert {a.value for a in RecommendedAction} == {
        "STANDARD_MANUAL_RECONCILIATION",
        "PRIORITY_MANUAL_RECONCILIATION",
        "DO_NOT_RELY_ON_RECEIPT",
    }
