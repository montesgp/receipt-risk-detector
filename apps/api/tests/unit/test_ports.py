"""Slice 1 port-shape tests.

Traces to design.md's `application/ports.py::ImageDecoderPort` contract:
every port is a `runtime_checkable` `Protocol` so adapters can be verified
structurally in tests without importing the concrete adapter class.
"""

from __future__ import annotations

from receipt_risk.adapters.image.pillow_decoder import PillowImageDecoder
from receipt_risk.application.ports import ImageDecoderPort


def test_image_decoder_port_is_runtime_checkable() -> None:
    assert isinstance(PillowImageDecoder(), ImageDecoderPort)
