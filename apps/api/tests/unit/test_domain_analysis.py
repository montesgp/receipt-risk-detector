"""Unit tests for `domain.analysis` result types.

Traces to spec.md's "Explainable, deterministic scoring" requirement: domain
result types must be immutable value objects so a computed assessment can
never be mutated after the fact.
"""

import dataclasses

import pytest

from receipt_risk.domain.analysis import AnalyzerResult


def test_analyzer_result_is_frozen_immutable_dataclass() -> None:
    result = AnalyzerResult(analyzer="ocr", version="1.0.0", status="completed")

    assert dataclasses.is_dataclass(result)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.status = "failed"  # type: ignore[misc]
