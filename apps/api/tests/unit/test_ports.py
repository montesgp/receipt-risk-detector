"""Slice 1/2 port-shape tests.

Traces to design.md's `application/ports.py` contract: every port is a
`runtime_checkable` `Protocol` so adapters can be verified structurally in
tests without importing the concrete adapter class.
"""

from __future__ import annotations

from receipt_risk.adapters.image.pillow_decoder import PillowImageDecoder
from receipt_risk.adapters.metadata.exiftool import ExifToolMetadataAdapter
from receipt_risk.adapters.provenance.c2pa_reader import C2paProvenanceAdapter
from receipt_risk.application.models import SafeImageRef
from receipt_risk.application.ports import (
    ImageDecoderPort,
    MetadataPort,
    OcrPort,
    ProvenancePort,
)
from receipt_risk.domain.analysis import AnalyzerResult


def test_image_decoder_port_is_runtime_checkable() -> None:
    assert isinstance(PillowImageDecoder(), ImageDecoderPort)


class _FakeMetadataAnalyzer:
    name = "fake-metadata"
    version = "0.0.1"

    async def inspect(self, image: SafeImageRef) -> AnalyzerResult:
        return AnalyzerResult(analyzer=self.name, version=self.version, status="completed")


class _FakeProvenanceAnalyzer:
    name = "fake-provenance"
    version = "0.0.1"

    async def inspect(self, image: SafeImageRef) -> AnalyzerResult:
        return AnalyzerResult(analyzer=self.name, version=self.version, status="completed")


def test_metadata_port_protocol_shape() -> None:
    assert isinstance(_FakeMetadataAnalyzer(), MetadataPort)


def test_provenance_port_protocol_shape() -> None:
    assert isinstance(_FakeProvenanceAnalyzer(), ProvenancePort)


def test_exiftool_metadata_adapter_conforms_to_metadata_port() -> None:
    assert isinstance(ExifToolMetadataAdapter(), MetadataPort)


def test_c2pa_provenance_adapter_conforms_to_provenance_port() -> None:
    assert isinstance(C2paProvenanceAdapter(), ProvenancePort)


class _FakeOcrAnalyzer:
    name = "fake-ocr"
    version = "0.0.1"

    async def extract(self, image: SafeImageRef) -> AnalyzerResult:
        return AnalyzerResult(analyzer=self.name, version=self.version, status="completed")


def test_ocr_port_protocol_shape() -> None:
    assert isinstance(_FakeOcrAnalyzer(), OcrPort)
