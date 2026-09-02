"""Pillow-backed `ImageDecoderPort` adapter.

Adapters own every framework/tool import per `docs/ARCHITECTURE.md` §5;
Pillow is allowed here via the `TID251` per-file-ignore on `adapters/**`.
Content type is sniffed from the decoded bytes themselves (`Image.open` +
`Image.verify`/`load`), never trusted from a client-declared filename or
`Content-Type` header.
"""

from __future__ import annotations

import io

from PIL import Image, UnidentifiedImageError

from receipt_risk.application.errors import IngestionError, IngestionErrorCode
from receipt_risk.application.models import DecodedImageInfo

_ALLOWED_FORMATS: dict[str, str] = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


class PillowImageDecoder:
    """Concrete `ImageDecoderPort` implementation."""

    def probe(self, data: bytes) -> DecodedImageInfo:
        try:
            with Image.open(io.BytesIO(data)) as img:
                image_format = img.format
                width, height = img.size
                # Force full decode (not just header parse) so a truncated
                # or otherwise corrupt body is caught here, before any
                # analyzer runs.
                img.load()
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise IngestionError(
                IngestionErrorCode.UNSUPPORTED_IMAGE,
                "The uploaded content could not be decoded as JPEG, PNG or WebP.",
            ) from exc

        media_type = _ALLOWED_FORMATS.get(image_format or "")
        if media_type is None:
            raise IngestionError(
                IngestionErrorCode.UNSUPPORTED_IMAGE,
                "The uploaded content could not be decoded as JPEG, PNG or WebP.",
            )

        return DecodedImageInfo(media_type=media_type, width=width, height=height)
