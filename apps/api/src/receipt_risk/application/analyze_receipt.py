"""Orchestrates ingestion, bounded-concurrency analyzer fan-out, financial
validation, and scoring into a `FraudAssessment`.

Traces to design.md's "Data Flow" and "a failed analyzer produces a signal,
never an aborted request" decision: every port call is wrapped by
`_guarded`, which converts any exception or per-analyzer timeout into an
`AnalyzerResult(status="failed" | "timed_out")` carrying an explicit
signal. The only abort path left is the HARD ingestion gate (raises
`IngestionError` before any analyzer runs) and whole-request budget
exhaustion (`AnalysisTimeoutError`, mapped to `504` by the API adapter).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from itertools import chain

import anyio

from receipt_risk.application.clock import Clock, SystemClock
from receipt_risk.application.financial_validation import validate_financials
from receipt_risk.application.ingestion import IngestionService
from receipt_risk.application.models import SafeImageRef
from receipt_risk.application.ports import MetadataPort, OcrPort, ProvenancePort, VisionPort
from receipt_risk.domain.analysis import AnalyzerResult
from receipt_risk.domain.assessment import FraudAssessment, assemble
from receipt_risk.domain.ruleset import ScoringRuleset
from receipt_risk.domain.signals import (
    ExtractionFailureReason,
    Severity,
    SignalCategory,
    SignalCode,
    ValidationSignal,
)

log = logging.getLogger(__name__)

ENGINE_VERSION = "0.2.0"
"""Bumped 0.1.0 -> 0.2.0 by the scoring-confidence-calibration change: the
`_completeness` provenance fix in `domain/scoring.py` is a shared-engine
formula correction, applied unconditionally and retroactively to every
ruleset version, so it is tracked by `engine_version` rather than
`ruleset_version` (which freezes policy, not formulas)."""


@dataclass(frozen=True, slots=True)
class TimeBudget:
    whole_request_s: float = 10.0  # NFR-001 p95
    ocr_s: float = 6.0  # includes the single OCR preprocessing retry
    metadata_s: float = 2.0
    provenance_s: float = 2.0
    vision_s: float = 3.0
    max_concurrent_analyzers: int = 2


class AnalysisTimeoutError(Exception):
    """Raised when the whole-request time budget is exhausted. Mapped to
    the documented `504 ANALYSIS_TIMEOUT` by the API adapter."""


def _unavailable_signal(analyzer_role: str) -> ValidationSignal:
    """A tool outage is not evidence of fraud -- it only lowers
    `confidence_score` through the coverage formula's `status_quality`
    term (design.md)."""
    return ValidationSignal(
        code=SignalCode.ANALYZER_UNAVAILABLE,
        category=SignalCategory.DATA_QUALITY,
        severity=Severity.INFO,
        confidence=Decimal("1.00"),
        description=f"The {analyzer_role} analyzer could not complete this request.",
        evidence={"analyzer": analyzer_role},
    )


def _ocr_failure_signal(reason: ExtractionFailureReason) -> ValidationSignal:
    """An unreadable receipt is itself suspicious, never a silent no-op
    (locked product decision, proposal.md)."""
    return ValidationSignal(
        code=SignalCode.CORE_FIELD_EXTRACTION_FAILED,
        category=SignalCategory.DATA_QUALITY,
        severity=Severity.MEDIUM,
        confidence=Decimal("1.00"),
        description="OCR extraction did not complete for this request.",
        evidence={"reason": reason.value},
    )


class AnalyzeReceiptUseCase:
    def __init__(
        self,
        *,
        ocr: OcrPort,
        metadata: MetadataPort,
        provenance: ProvenancePort,
        vision: VisionPort,
        ingestion: IngestionService,
        ruleset: ScoringRuleset,
        budget: TimeBudget | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._ocr = ocr
        self._metadata = metadata
        self._provenance = provenance
        self._vision = vision
        self._ingestion = ingestion
        self._ruleset = ruleset
        self._budget = budget if budget is not None else TimeBudget()
        self._clock = clock if clock is not None else SystemClock()

    async def execute(
        self, data: bytes, *, declared_filename: str | None = None
    ) -> FraudAssessment:
        safe = self._ingestion.ingest(
            data, declared_filename=declared_filename
        )  # HARD gate; raises IngestionError -> 4xx, no analyzer runs
        try:
            started = self._clock.monotonic_ms()
            try:
                with anyio.fail_after(self._budget.whole_request_s):
                    results = await self._run_analyzers(safe)
            except TimeoutError as exc:
                raise AnalysisTimeoutError("Whole-request analysis budget exhausted.") from exc

            ocr_result = next((r for r in results if r.analyzer == self._ocr.name), None)
            signals = list(chain.from_iterable(result.signals for result in results))
            if ocr_result is not None:
                signals.extend(validate_financials(ocr_result.extracted_fields))

            duration_ms = self._clock.monotonic_ms() - started
            return assemble(
                analysis_id=f"sha256:{safe.sha256}",
                results=results,
                signals=signals,
                ruleset=self._ruleset,
                engine_version=ENGINE_VERSION,
                duration_ms=duration_ms,
            )
        finally:
            self._ingestion.cleanup(safe)  # success, error, timeout, cancellation

    async def _run_analyzers(self, safe: SafeImageRef) -> list[AnalyzerResult]:
        semaphore = anyio.Semaphore(self._budget.max_concurrent_analyzers)
        results: dict[str, AnalyzerResult] = {}

        async def _run(role: str, port: object, run_budget_s: float) -> None:
            async with semaphore:
                results[role] = await self._guarded(port, role, run_budget_s, safe)

        async with anyio.create_task_group() as task_group:
            task_group.start_soon(_run, "ocr", self._ocr, self._budget.ocr_s)
            task_group.start_soon(_run, "metadata", self._metadata, self._budget.metadata_s)
            task_group.start_soon(_run, "provenance", self._provenance, self._budget.provenance_s)
            task_group.start_soon(_run, "vision", self._vision, self._budget.vision_s)

        # Vision listed first per spec's "Vision listed first in signal
        # ordering" scenario -- this is a presentation ordering only, all
        # four analyzers still ran concurrently in the one task group above.
        return [results["vision"], results["ocr"], results["metadata"], results["provenance"]]

    async def _guarded(
        self, port: object, role: str, budget_s: float, safe: SafeImageRef
    ) -> AnalyzerResult:
        """Wrap one port call so no adapter exception or timeout can ever
        abort the request — the "failed analyzer produces a signal, never
        an aborted request" contract."""
        started = self._clock.monotonic_ms()
        try:
            with anyio.fail_after(budget_s):
                if role == "ocr":
                    return await port.extract(safe)  # type: ignore[attr-defined]
                return await port.inspect(safe)  # type: ignore[attr-defined]
        except TimeoutError:
            duration_ms = self._clock.monotonic_ms() - started
            signals = (
                (_ocr_failure_signal(ExtractionFailureReason.TIMEOUT),)
                if role == "ocr"
                else (_unavailable_signal(role),)
            )
            return AnalyzerResult(
                analyzer=port.name,  # type: ignore[attr-defined]
                version=port.version,  # type: ignore[attr-defined]
                status="timed_out",
                signals=signals,
                error_code="ANALYZER_TIMEOUT",
                duration_ms=duration_ms,
            )
        except Exception:  # noqa: BLE001 -- never leaks a tool exception upward
            duration_ms = self._clock.monotonic_ms() - started
            log.warning("analyzer_failed", extra={"analyzer": role})  # no payload, no raw text
            signals = (
                (_ocr_failure_signal(ExtractionFailureReason.NO_TEXT_DETECTED),)
                if role == "ocr"
                else (_unavailable_signal(role),)
            )
            return AnalyzerResult(
                analyzer=port.name,  # type: ignore[attr-defined]
                version=port.version,  # type: ignore[attr-defined]
                status="failed",
                signals=signals,
                error_code="ANALYZER_FAILED",
                duration_ms=duration_ms,
            )
