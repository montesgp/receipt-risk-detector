"""Application ports (protocols) implemented by adapters.

Slice 1 defines only `ImageDecoderPort`. `MetadataPort`, `ProvenancePort`,
and `OcrPort` are added by slices 2 and 3. Every port returns a domain type
(never `dict`, JSON, or a tool-specific type) so raw tool output can never
cross this boundary — see design.md "Application — ports".
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from receipt_risk.application.models import DecodedImageInfo


@runtime_checkable
class ImageDecoderPort(Protocol):
    def probe(self, data: bytes) -> DecodedImageInfo:
        """Sniff `data`'s real content type and dimensions without trusting
        any client-declared filename or MIME type. Raises
        `receipt_risk.application.errors.IngestionError` (code
        `UNSUPPORTED_IMAGE`) when `data` cannot be decoded as JPEG, PNG, or
        WebP."""
        ...
