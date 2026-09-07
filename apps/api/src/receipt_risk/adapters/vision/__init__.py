"""Vision adapter package (visual-anomaly-detection change).

`VisionPort` implementation over a frozen MobileNetV3-Small embedder,
mirroring `adapters/ocr/paddle_onnx.py`'s fail-closed model-loading and
adapter-only-import conventions (`docs/ARCHITECTURE.md` §5).
"""

from __future__ import annotations
