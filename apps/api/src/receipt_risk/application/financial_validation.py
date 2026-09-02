"""Orchestrates all `domain.financial` validators over already-extracted OCR
fields, producing `ValidationSignal`s.

Pure over `Sequence[ExtractedField]` — the only application-layer concern
here is wiring the deterministic domain validators together and masking any
financial value before it reaches a `ValidationSignal.evidence` mapping
(never raw CBU/CUIT/amount — data-retention log-masking scenario). Zero
framework imports, zero I/O.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

from receipt_risk.domain.analysis import ExtractedField
from receipt_risk.domain.financial.cbu import ChecksumFailure, validate_cbu
from receipt_risk.domain.financial.contradictions import detect_contradictions
from receipt_risk.domain.financial.cuit import validate_cuit
from receipt_risk.domain.financial.dates import is_within_date_bounds
from receipt_risk.domain.signals import Severity, SignalCategory, SignalCode, ValidationSignal

_CBU_CHECK_DIGIT_FAILURES = frozenset(
    {ChecksumFailure.BLOCK1_CHECK_DIGIT, ChecksumFailure.BLOCK2_CHECK_DIGIT}
)


def _mask(value: str) -> str:
    """Mask all but the last 4 characters of a financial value. Never emit a
    raw CBU/CUIT/amount into a signal's evidence."""
    if len(value) <= 4:
        return "*" * len(value)
    return "*" * (len(value) - 4) + value[-4:]


def _parse_datetime(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def validate_financials(
    fields: Sequence[ExtractedField],
    *,
    reference: datetime | None = None,
) -> list[ValidationSignal]:
    """Run every slice-3a domain validator over `fields` and return the
    resulting signals, in a stable order: CBU, CUIT, date bounds, then
    contradictions."""
    signals: list[ValidationSignal] = []
    fields_by_name = {field.name: field for field in fields}

    cbu_field = fields_by_name.get("destination_cbu")
    if cbu_field is not None and cbu_field.normalized:
        result = validate_cbu(cbu_field.normalized)
        if not result.is_valid and result.failure in _CBU_CHECK_DIGIT_FAILURES:
            signals.append(
                ValidationSignal(
                    code=SignalCode.INVALID_CBU_CHECK_DIGIT,
                    category=SignalCategory.FINANCIAL_CONSISTENCY,
                    severity=Severity.HIGH,
                    confidence=cbu_field.confidence,
                    description="Extracted CBU/CVU fails its check-digit algorithm.",
                    evidence={
                        "destination_cbu": _mask(cbu_field.normalized),
                        "failure": result.failure.value,
                    },
                )
            )

    cuit_field = fields_by_name.get("cuit")
    if cuit_field is not None and cuit_field.normalized:
        result = validate_cuit(cuit_field.normalized)
        if not result.is_valid and result.failure is ChecksumFailure.CHECK_DIGIT:
            signals.append(
                ValidationSignal(
                    code=SignalCode.INVALID_CUIT_CHECK_DIGIT,
                    category=SignalCategory.FINANCIAL_CONSISTENCY,
                    severity=Severity.HIGH,
                    confidence=cuit_field.confidence,
                    description="Extracted CUIT/CUIL fails its check-digit algorithm.",
                    evidence={"cuit": _mask(cuit_field.normalized)},
                )
            )

    date_field = fields_by_name.get("date_time")
    if date_field is not None and date_field.normalized:
        parsed = _parse_datetime(date_field.normalized)
        if parsed is not None:
            effective_reference = reference if reference is not None else datetime.now(UTC)
            if not is_within_date_bounds(parsed, reference=effective_reference):
                signals.append(
                    ValidationSignal(
                        code=SignalCode.DATE_OUT_OF_BOUNDS,
                        category=SignalCategory.FINANCIAL_CONSISTENCY,
                        severity=Severity.MEDIUM,
                        confidence=date_field.confidence,
                        description="Extracted date falls outside the plausibility window.",
                        evidence={"date_time": _mask(date_field.normalized)},
                    )
                )

    for name in detect_contradictions(fields):
        signals.append(
            ValidationSignal(
                code=SignalCode.AMOUNT_DATE_CONTRADICTION,
                category=SignalCategory.FINANCIAL_CONSISTENCY,
                severity=Severity.MEDIUM,
                confidence=Decimal("1.00"),
                description=f"Multiple extracted occurrences of '{name}' disagree.",
                evidence={"field": name},
            )
        )

    return signals
