"""Ingestion orchestration: the HARD gate before any analyzer runs.

Traces to spec.md scenarios "Valid image accepted", "Oversized or corrupt
image rejected", "Excessive dimensions rejected", and "Temp files removed on
all paths" (receipt-analysis), plus data-retention's "Temp files deleted
after processing". Zero framework/tool imports here — `ImageDecoderPort` is
injected so this module never touches Pillow directly.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path

from receipt_risk.application.errors import IngestionError, IngestionErrorCode
from receipt_risk.application.models import SafeImageRef
from receipt_risk.application.ports import ImageDecoderPort

MAX_BYTES: int = 10 * 1024 * 1024
MAX_DIMENSION: int = 8000
MAX_PIXELS: int = 40_000_000


class IngestionService:
    """Validates, decodes, and persists an uploaded image to a private
    temp path; guarantees cleanup via `cleanup()`."""

    def __init__(
        self,
        *,
        temp_dir: Path,
        decoder: ImageDecoderPort,
        max_bytes: int = MAX_BYTES,
        max_dimension: int = MAX_DIMENSION,
        max_pixels: int = MAX_PIXELS,
    ) -> None:
        self._temp_dir = temp_dir
        self._decoder = decoder
        self._max_bytes = max_bytes
        self._max_dimension = max_dimension
        self._max_pixels = max_pixels

    def ingest(self, data: bytes, *, declared_filename: str | None = None) -> SafeImageRef:
        """Validate `data` end to end and persist it to a private temp path.

        `declared_filename` is accepted only for error messages/telemetry
        and is never used to derive the stored path or trusted for content
        type (content sniffing only, per FR-001/FR-002).
        """
        del declared_filename  # never used for path derivation or type trust

        if not data:
            raise IngestionError(
                IngestionErrorCode.UNSUPPORTED_IMAGE,
                "The uploaded content could not be decoded as JPEG, PNG or WebP.",
            )

        if len(data) > self._max_bytes:
            raise IngestionError(
                IngestionErrorCode.FILE_TOO_LARGE,
                f"The uploaded file exceeds the maximum size of {self._max_bytes} bytes.",
            )

        info = self._decoder.probe(data)  # raises IngestionError(UNSUPPORTED_IMAGE)

        if info.width > self._max_dimension or info.height > self._max_dimension:
            raise IngestionError(
                IngestionErrorCode.IMAGE_DIMENSIONS_EXCEEDED,
                f"Image dimensions exceed the maximum of {self._max_dimension}px per side.",
            )

        if info.width * info.height > self._max_pixels:
            raise IngestionError(
                IngestionErrorCode.IMAGE_DIMENSIONS_EXCEEDED,
                f"Image pixel count exceeds the maximum of {self._max_pixels}.",
            )

        digest = hashlib.sha256(data).hexdigest()
        self._temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = self._temp_dir / f"{uuid.uuid4().hex}.bin"
        temp_path.write_bytes(data)

        return SafeImageRef(
            path=temp_path,
            sha256=digest,
            media_type=info.media_type,
            width=info.width,
            height=info.height,
            byte_size=len(data),
        )

    def cleanup(self, safe: SafeImageRef) -> None:
        """Delete the temp file for `safe`. Idempotent: safe to call more
        than once, and safe to call even if the file was already removed.
        Must be called from a `finally` block by every caller so cleanup
        runs on success, error, timeout, and cancellation alike."""
        try:
            os.remove(safe.path)
        except FileNotFoundError:
            pass
