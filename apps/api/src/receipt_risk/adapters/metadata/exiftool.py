"""ExifTool subprocess adapter — `MetadataPort` implementation.

Adapters own every framework/tool import per `docs/ARCHITECTURE.md` §5.
`subprocess` is allowed here only via the `TID251` per-file-ignore on
`adapters/**`; ruff's banned-api list still forbids importing it from
`domain/` or `application/` (design.md, pyproject.toml).

Threat matrix: "Subprocess invocation (ExifTool)" — design.md locks the
injection surface down structurally, not by sanitizing input:
  - fixed argv list, never a shell string (`shell=False`)
  - `--` end-of-options marker immediately before the path
  - the path is always the server-generated temp path from
    `application/ingestion.py` — the client-supplied filename is discarded
    at ingestion and never reaches this module
  - a mandatory `timeout` bounds a hung binary
  - `shutil.which`-resolved absolute binary path (never a bare command name)
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess  # noqa: S404 — adapter-only, see pyproject.toml banned-api
import time
from decimal import Decimal
from pathlib import Path
from typing import Any, Final

import anyio

from receipt_risk.application.models import SafeImageRef
from receipt_risk.domain.analysis import AnalyzerResult
from receipt_risk.domain.signals import Severity, SignalCategory, SignalCode, ValidationSignal

_EXIFTOOL: Final[str | None] = shutil.which("exiftool")
DEFAULT_TIMEOUT_S: Final[float] = 2.0

# Substrings matched case-insensitively against the `Software`/`CreatorTool`
# EXIF/XMP tags. Not exhaustive — a documented default per the proposal's
# "reasonable defaults, not fake precision" stance, revisited once real-world
# samples exist.
_EDITOR_SOFTWARE_MARKERS: Final[tuple[str, ...]] = (
    "photoshop",
    "gimp",
    "affinity photo",
    "canva",
    "paint.net",
    "lightroom",
)


class ExifToolUnavailable(Exception):
    """Raised when the `exiftool` binary cannot be located on `PATH`."""


def _run_exiftool(path: Path, timeout_s: float) -> str:
    if _EXIFTOOL is None:
        raise ExifToolUnavailable
    completed = subprocess.run(  # noqa: S603 — fixed argv, shell=False, mandatory timeout
        [_EXIFTOOL, "-json", "-n", "-charset", "utf8", "-fast2", "--", str(path)],
        capture_output=True,
        text=True,
        timeout=timeout_s,
        shell=False,
        check=False,
        env={"PATH": os.defpath, "LANG": "C"},
    )
    return completed.stdout


def _derive_signals(tags: dict[str, Any]) -> tuple[ValidationSignal, ...]:
    software = str(tags.get("Software") or tags.get("CreatorTool") or "").strip().lower()
    if not software:
        return ()
    if not any(marker in software for marker in _EDITOR_SOFTWARE_MARKERS):
        return ()
    return (
        ValidationSignal(
            code=SignalCode.METADATA_EDITOR_SOFTWARE,
            category=SignalCategory.METADATA,
            severity=Severity.LOW,
            confidence=Decimal("0.80"),
            description=(
                "Embedded metadata names editing software; the receipt's "
                "original capture may have been modified."
            ),
            evidence={"software": software},
        ),
    )


def _parse_tags(stdout: str) -> dict[str, Any]:
    try:
        parsed = json.loads(stdout) if stdout else []
    except json.JSONDecodeError:
        return {}
    if not parsed:
        return {}
    return parsed[0]


def _elapsed_ms(started_monotonic: float) -> int:
    return int((time.monotonic() - started_monotonic) * 1000)


class ExifToolMetadataAdapter:
    """Concrete `MetadataPort` implementation."""

    name = "exiftool"
    version = "1.0.0"

    def __init__(self, *, timeout_s: float = DEFAULT_TIMEOUT_S) -> None:
        self._timeout_s = timeout_s

    async def inspect(self, image: SafeImageRef) -> AnalyzerResult:
        started = time.monotonic()
        try:
            stdout = await anyio.to_thread.run_sync(_run_exiftool, image.path, self._timeout_s)
        except subprocess.TimeoutExpired:
            return AnalyzerResult(
                analyzer=self.name,
                version=self.version,
                status="timed_out",
                error_code="ANALYZER_TIMEOUT",
                duration_ms=_elapsed_ms(started),
            )
        except ExifToolUnavailable:
            return AnalyzerResult(
                analyzer=self.name,
                version=self.version,
                status="failed",
                error_code="ANALYZER_UNAVAILABLE",
                duration_ms=_elapsed_ms(started),
            )

        tags = _parse_tags(stdout)
        return AnalyzerResult(
            analyzer=self.name,
            version=self.version,
            status="completed",
            signals=_derive_signals(tags),
            duration_ms=_elapsed_ms(started),
        )
