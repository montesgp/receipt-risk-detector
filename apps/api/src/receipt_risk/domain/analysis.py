"""Domain analyzer result types.

Pure, I/O-free per `docs/ARCHITECTURE.md` §5. Every analyzer port (slices
2-4) returns `AnalyzerResult` so raw tool output never crosses the
application boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from receipt_risk.domain.signals import ValidationSignal

AnalyzerStatus = Literal["completed", "partial", "failed", "timed_out"]


@dataclass(frozen=True, slots=True)
class ExtractedField:
    name: str
    raw_text: str
    normalized: str | None
    confidence: Decimal


@dataclass(frozen=True, slots=True)
class AnalyzerResult:
    analyzer: str
    version: str
    status: AnalyzerStatus
    signals: tuple[ValidationSignal, ...] = ()
    extracted_fields: tuple[ExtractedField, ...] = ()
    duration_ms: int = 0
    error_code: str | None = None
