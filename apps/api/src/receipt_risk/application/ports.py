"""Application ports (protocols) implemented by adapters.

Slice 1 defines only `ImageDecoderPort`. `MetadataPort` and `ProvenancePort`
are added by slice 2; `OcrPort` is added by slice 3. Every port returns a
domain type (never `dict`, JSON, or a tool-specific type) so raw tool output
can never cross this boundary — see design.md "Application — ports".
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from receipt_risk.application.models import DecodedImageInfo, SafeImageRef
from receipt_risk.domain.analysis import AnalyzerResult


@runtime_checkable
class ImageDecoderPort(Protocol):
    def probe(self, data: bytes) -> DecodedImageInfo:
        """Sniff `data`'s real content type and dimensions without trusting
        any client-declared filename or MIME type. Raises
        `receipt_risk.application.errors.IngestionError` (code
        `UNSUPPORTED_IMAGE`) when `data` cannot be decoded as JPEG, PNG, or
        WebP."""
        ...


@runtime_checkable
class MetadataPort(Protocol):
    """Embedded EXIF/metadata inspection (slice 2). `inspect` never raises:
    tool failures and timeouts are converted to `AnalyzerResult(status=
    "failed" | "timed_out")` at the adapter boundary."""

    name: str
    version: str

    async def inspect(self, image: SafeImageRef) -> AnalyzerResult: ...


@runtime_checkable
class ProvenancePort(Protocol):
    """C2PA / Content Credentials inspection (slice 2). `inspect` never
    raises: absence of a manifest is a neutral, completed result, never an
    error (spec.md "Missing metadata is neutral")."""

    name: str
    version: str

    async def inspect(self, image: SafeImageRef) -> AnalyzerResult: ...
