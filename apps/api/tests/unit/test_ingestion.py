"""Unit tests for `application.ingestion`.

Traces to spec.md scenarios: "Valid image accepted", "Oversized or corrupt
image rejected", "Excessive dimensions rejected", "Temp files removed on all
paths" (receipt-analysis capability), plus the data-retention capability's
"Temp files deleted after processing" scenario.
"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path

import pytest
from PIL import Image

from conftest import fixture as load_fixture
from receipt_risk.adapters.image.pillow_decoder import PillowImageDecoder
from receipt_risk.application.errors import IngestionError
from receipt_risk.application.ingestion import IngestionService

MAX_BYTES = 10 * 1024 * 1024
MAX_DIMENSION = 8000
MAX_PIXELS = 40_000_000


def _service(tmp_path: Path) -> IngestionService:
    return IngestionService(temp_dir=tmp_path, decoder=PillowImageDecoder())


def _jpeg_bytes(width: int = 100, height: int = 100) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color="white").save(buf, format="JPEG")
    return buf.getvalue()


def _png_bytes(width: int = 100, height: int = 100) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color="white").save(buf, format="PNG")
    return buf.getvalue()


def test_valid_jpeg_under_max_size_accepted(tmp_path: Path) -> None:
    data = _jpeg_bytes()
    service = _service(tmp_path)

    safe = service.ingest(data, declared_filename="receipt.jpg")

    assert safe.media_type == "image/jpeg"
    assert safe.byte_size == len(data)
    assert safe.sha256 == hashlib.sha256(data).hexdigest()
    assert safe.path.exists()

    service.cleanup(safe)


def test_valid_png_accepted(tmp_path: Path) -> None:
    data = _png_bytes()
    service = _service(tmp_path)

    safe = service.ingest(data, declared_filename="receipt.png")

    assert safe.media_type == "image/png"
    service.cleanup(safe)


def test_oversized_image_rejected_4xx(tmp_path: Path) -> None:
    service = _service(tmp_path)
    oversized = b"\xff" * (MAX_BYTES + 1)

    with pytest.raises(IngestionError) as exc_info:
        service.ingest(oversized, declared_filename="huge.jpg")

    assert exc_info.value.code == "FILE_TOO_LARGE"
    assert exc_info.value.status_code == 413


def test_corrupt_content_fails_decode_rejected_4xx(tmp_path: Path) -> None:
    service = _service(tmp_path)
    garbage = b"this is not an image" * 10

    with pytest.raises(IngestionError) as exc_info:
        service.ingest(garbage, declared_filename="receipt.jpg")

    assert exc_info.value.code == "UNSUPPORTED_IMAGE"
    assert exc_info.value.status_code == 415


def test_wrong_format_masquerading_as_allowed_extension_rejected(tmp_path: Path) -> None:
    """A `.jpg`-named file whose bytes are not a JPEG/PNG/WebP must be
    rejected by content sniffing, not by trusting the declared extension."""
    service = _service(tmp_path)
    fake_jpeg = b"GIF89a" + b"\x00" * 100  # GIF bytes, disallowed format

    with pytest.raises(IngestionError) as exc_info:
        service.ingest(fake_jpeg, declared_filename="receipt.jpg")

    assert exc_info.value.code == "UNSUPPORTED_IMAGE"


def test_zero_byte_file_rejected(tmp_path: Path) -> None:
    service = _service(tmp_path)

    with pytest.raises(IngestionError) as exc_info:
        service.ingest(b"", declared_filename="empty.jpg")

    assert exc_info.value.code == "UNSUPPORTED_IMAGE"


def test_excessive_dimensions_rejected(tmp_path: Path) -> None:
    service = _service(tmp_path)
    data = _png_bytes(width=MAX_DIMENSION + 1, height=10)

    with pytest.raises(IngestionError) as exc_info:
        service.ingest(data, declared_filename="wide.png")

    assert exc_info.value.code == "IMAGE_DIMENSIONS_EXCEEDED"
    assert exc_info.value.status_code == 422


def test_excessive_pixel_count_rejected(tmp_path: Path) -> None:
    service = _service(tmp_path)
    # Both dimensions individually legal, but width * height exceeds MAX_PIXELS.
    side = 6350
    assert side <= MAX_DIMENSION
    assert side * side > MAX_PIXELS
    data = _png_bytes(width=side, height=side)

    with pytest.raises(IngestionError) as exc_info:
        service.ingest(data, declared_filename="huge_pixels.png")

    assert exc_info.value.code == "IMAGE_DIMENSIONS_EXCEEDED"


def test_temp_file_cleanup_runs_on_success_error_and_exception(tmp_path: Path) -> None:
    service = _service(tmp_path)

    # Success path.
    safe = service.ingest(_jpeg_bytes(), declared_filename="ok.jpg")
    service.cleanup(safe)
    assert not safe.path.exists()

    # Rejected (error) path: no temp file survives a rejected ingest either.
    with pytest.raises(IngestionError):
        service.ingest(b"not an image", declared_filename="bad.jpg")
    assert list(tmp_path.iterdir()) == []

    # Exception during downstream processing: caller's `finally` must still
    # be able to clean up the already-created temp file.
    safe2 = service.ingest(_jpeg_bytes(), declared_filename="ok2.jpg")
    try:
        raise RuntimeError("simulated analyzer crash")
    except RuntimeError:
        pass
    finally:
        service.cleanup(safe2)
    assert not safe2.path.exists()


def test_corrupted_truncated_fixture_rejected_with_415_unsupported_image(tmp_path: Path) -> None:
    corrupted = load_fixture("corrupted_truncated")
    service = _service(tmp_path)

    with pytest.raises(IngestionError) as exc_info:
        service.ingest(corrupted.bytes, declared_filename="corrupted_truncated.jpg")

    assert exc_info.value.status_code == corrupted.expected_error["status"]
    assert exc_info.value.code == corrupted.expected_error["code"]


def test_cleanup_is_idempotent_when_file_already_removed(tmp_path: Path) -> None:
    service = _service(tmp_path)
    safe = service.ingest(_jpeg_bytes(), declared_filename="ok.jpg")
    safe.path.unlink()

    service.cleanup(safe)  # must not raise
