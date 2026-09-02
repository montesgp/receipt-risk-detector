"""Application-layer request/reference models.

Pure data holders; no I/O and no framework imports per `docs/ARCHITECTURE.md`
§5.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DecodedImageInfo:
    """Result of `ImageDecoderPort.probe`: everything the ingestion gates
    need to know about an image without persisting decoded pixel data."""

    media_type: str
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class SafeImageRef:
    """A reference to a decoded, validated image stored at a private,
    server-generated temp path. Never carries the client-supplied filename —
    that is discarded at ingestion (see the ExifTool subprocess-safety
    threat, slice 2)."""

    path: Path
    sha256: str
    media_type: str
    width: int
    height: int
    byte_size: int
