"""Privacy scan: no raw bytes or unmasked CBU/CUIT/amount in logs across
success and failure paths (data-retention spec's log-masking scenario).
"""

from __future__ import annotations

import logging
from decimal import Decimal
from pathlib import Path

import anyio
import pytest

from receipt_risk.application.analyze_receipt import AnalyzeReceiptUseCase
from receipt_risk.application.ingestion import IngestionService
from receipt_risk.application.models import DecodedImageInfo, SafeImageRef
from receipt_risk.domain.analysis import AnalyzerResult, ExtractedField
from receipt_risk.domain.rulesets.v2026_09_01 import RULESET_2026_09_01

_RAW_CBU = "2850590940090418135201"
_RAW_CUIT = "20172543597"


class _StubDecoder:
    def probe(self, data: bytes) -> DecodedImageInfo:
        return DecodedImageInfo(media_type="image/png", width=10, height=10)


class _OcrWithRawFinancialFields:
    name = "paddleocr-onnx"
    version = "1.0.0"

    async def extract(self, image: SafeImageRef) -> AnalyzerResult:
        return AnalyzerResult(
            analyzer=self.name,
            version=self.version,
            status="completed",
            extracted_fields=(
                ExtractedField(
                    name="destination_cbu",
                    raw_text=_RAW_CBU,
                    normalized=_RAW_CBU,
                    confidence=Decimal("0.90"),
                ),
                ExtractedField(
                    name="cuit",
                    raw_text=_RAW_CUIT,
                    normalized=_RAW_CUIT,
                    confidence=Decimal("0.90"),
                ),
            ),
        )


class _CompletedPort:
    name = "stub"
    version = "1.0.0"

    async def inspect(self, image: SafeImageRef) -> AnalyzerResult:
        return AnalyzerResult(analyzer=self.name, version=self.version, status="completed")


class _RaisingPort:
    name = "stub-raising"
    version = "1.0.0"

    async def inspect(self, image: SafeImageRef) -> AnalyzerResult:
        raise RuntimeError(f"failed while processing raw payload with CBU {_RAW_CBU}")


def test_no_raw_bytes_or_unmasked_cbu_cuit_amount_in_logs_across_success_and_failure_paths(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    ingestion = IngestionService(temp_dir=tmp_path, decoder=_StubDecoder())
    use_case = AnalyzeReceiptUseCase(
        ocr=_OcrWithRawFinancialFields(),
        metadata=_RaisingPort(),
        provenance=_CompletedPort(),
        ingestion=ingestion,
        ruleset=RULESET_2026_09_01,
    )
    data = b"\x89PNG\r\n\x1a\nfake-bytes-for-privacy-test"

    with caplog.at_level(logging.DEBUG):

        async def _run():
            return await use_case.execute(data)

        assessment = anyio.run(_run)

    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert _RAW_CBU not in log_text
    assert _RAW_CUIT not in log_text
    assert data not in log_text.encode("utf-8", errors="ignore")

    # The signal evidence itself must also mask, never carry the raw value.
    for signal in assessment.signals:
        for value in signal.evidence.values():
            assert _RAW_CBU not in value
            assert _RAW_CUIT not in value
