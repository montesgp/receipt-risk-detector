"""Deterministic financial validators (slice 3a).

Pure, I/O-free per `docs/ARCHITECTURE.md` §5 — no new dependencies. Every
validator in this package operates on already-extracted strings/values; OCR
extraction itself lives in `adapters/ocr/` (slice 3b).
"""

from __future__ import annotations
