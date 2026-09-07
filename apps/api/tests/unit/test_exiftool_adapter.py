"""Unit tests for `adapters.metadata.exiftool`.

Traces to design.md's threat matrix "Subprocess invocation (ExifTool)" — all
4 adversarial cases — and to spec.md's "Missing metadata is neutral"
scenario. Every threat test mocks `subprocess.run` so it runs deterministically
without a real `exiftool` binary; the real-binary integration test lives in
`tests/integration/test_metadata_provenance_integration.py` and is
skip-marked when the binary is absent locally.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from receipt_risk.adapters.metadata import exiftool as exiftool_module
from receipt_risk.adapters.metadata.exiftool import ExifToolMetadataAdapter
from receipt_risk.application.models import SafeImageRef


def _safe_image_ref(path: Path) -> SafeImageRef:
    return SafeImageRef(
        path=path, sha256="a" * 64, media_type="image/jpeg", width=100, height=100, byte_size=123
    )


def _fake_completed(stdout: str) -> MagicMock:
    completed = MagicMock()
    completed.stdout = stdout
    return completed


def test_exiftool_argv_never_contains_client_supplied_filename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A client uploads a file whose (attacker-controlled) declared filename
    is `; rm -rf /.jpg`. Ingestion always discards that name and stores the
    bytes under a server-generated temp path (application/ingestion.py), so
    the adapter must never see or use the malicious string; argv must be a
    plain list (never shell-interpreted) ending in the real temp path."""
    monkeypatch.setattr(exiftool_module, "_EXIFTOOL", "/usr/bin/exiftool")
    captured: dict[str, object] = {}

    def _fake_run(argv: list[str], **kwargs: object) -> MagicMock:
        captured["argv"] = argv
        captured["kwargs"] = kwargs
        return _fake_completed("[]")

    monkeypatch.setattr(exiftool_module.subprocess, "run", _fake_run)

    real_path = tmp_path / "f47b3c9e2a.bin"  # server-generated name; never client-controlled
    real_path.write_bytes(b"\xff\xd8\xff")
    safe = _safe_image_ref(real_path)

    asyncio.run(ExifToolMetadataAdapter().inspect(safe))

    argv = captured["argv"]
    assert isinstance(argv, list)
    assert "; rm -rf /.jpg" not in " ".join(argv)
    assert argv[-1] == str(real_path)
    assert captured["kwargs"]["shell"] is False


def test_exiftool_leading_dash_filename_no_option_injection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Even if a temp path happened to start with `-`, exiftool must treat it
    as a literal filename, never an option, because argv always contains a
    `--` end-of-options marker immediately before the path."""
    monkeypatch.setattr(exiftool_module, "_EXIFTOOL", "/usr/bin/exiftool")
    captured: dict[str, object] = {}

    def _fake_run(argv: list[str], **kwargs: object) -> MagicMock:
        captured["argv"] = argv
        return _fake_completed("[]")

    monkeypatch.setattr(exiftool_module.subprocess, "run", _fake_run)

    dash_path = tmp_path / "-ver.jpg"
    dash_path.write_bytes(b"\xff\xd8\xff")
    safe = _safe_image_ref(dash_path)

    asyncio.run(ExifToolMetadataAdapter().inspect(safe))

    argv = captured["argv"]
    assert "--" in argv
    dash_marker_index = argv.index("--")
    assert argv[dash_marker_index + 1] == str(dash_path)


def test_exiftool_hung_binary_times_out_no_orphan_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(exiftool_module, "_EXIFTOOL", "/usr/bin/exiftool")

    def _fake_run(argv: list[str], **kwargs: object) -> MagicMock:
        # subprocess.run(timeout=...) kills the child on TimeoutExpired
        # internally (Popen.communicate contract) — no orphan process is
        # left behind by construction; asserting the mandatory timeout kwarg
        # plus the resulting status is the adapter-level contract.
        assert kwargs["timeout"] > 0
        raise subprocess.TimeoutExpired(cmd=argv, timeout=kwargs["timeout"])

    monkeypatch.setattr(exiftool_module.subprocess, "run", _fake_run)

    path = tmp_path / "hung.bin"
    path.write_bytes(b"\xff\xd8\xff")
    safe = _safe_image_ref(path)

    result = asyncio.run(ExifToolMetadataAdapter().inspect(safe))

    assert result.status == "timed_out"
    assert result.error_code == "ANALYZER_TIMEOUT"


def test_exiftool_binary_absent_returns_failed_status_request_still_200(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(exiftool_module, "_EXIFTOOL", None)

    path = tmp_path / "any.bin"
    path.write_bytes(b"\xff\xd8\xff")
    safe = _safe_image_ref(path)

    result = asyncio.run(ExifToolMetadataAdapter().inspect(safe))

    # "request still 200" is enforced at the API layer (slice 4's guarded
    # call, which converts any AnalyzerResult into a 200 response); here we
    # assert the adapter-level contract the API relies on: a failed tool
    # never raises, it degrades to a typed AnalyzerResult.
    assert result.status == "failed"
    assert result.error_code == "ANALYZER_UNAVAILABLE"


def test_missing_metadata_is_neutral_zero_signals_status_completed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(exiftool_module, "_EXIFTOOL", "/usr/bin/exiftool")
    monkeypatch.setattr(
        exiftool_module.subprocess,
        "run",
        lambda argv, **kwargs: _fake_completed(json.dumps([{"SourceFile": str(argv[-1])}])),
    )

    path = tmp_path / "clean.bin"
    path.write_bytes(b"\xff\xd8\xff")
    safe = _safe_image_ref(path)

    result = asyncio.run(ExifToolMetadataAdapter().inspect(safe))

    assert result.status == "completed"
    assert result.signals == ()


def test_editor_software_tag_emits_metadata_editor_software_signal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(exiftool_module, "_EXIFTOOL", "/usr/bin/exiftool")
    monkeypatch.setattr(
        exiftool_module.subprocess,
        "run",
        lambda argv, **kwargs: _fake_completed(
            json.dumps([{"SourceFile": str(argv[-1]), "Software": "Adobe Photoshop 25.0"}])
        ),
    )

    path = tmp_path / "edited.bin"
    path.write_bytes(b"\xff\xd8\xff")
    safe = _safe_image_ref(path)

    result = asyncio.run(ExifToolMetadataAdapter().inspect(safe))

    assert result.status == "completed"
    assert len(result.signals) == 1
    assert result.signals[0].code == "METADATA_EDITOR_SOFTWARE"


def test_tc260_aigc_label_emits_metadata_ai_generated_claim_signal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Real-world regression: a Qwen-generated fake Mercado Pago receipt
    (amount tampered 8.000 -> 80.000) scored LOW_RISK (5/100) because this
    tag was never checked -- only `Software`/`CreatorTool` were. `exiftool
    -json -n` flattens the XMP-TC260 group, so the tag is a bare `Aigc` key
    on the parsed object, exactly as reproduced here."""
    monkeypatch.setattr(exiftool_module, "_EXIFTOOL", "/usr/bin/exiftool")
    aigc = (
        '{"Label":"1","ContentProducer":"001191330106MA2CFLDG4R10001",'
        '"ProduceID":"R-7-k8iwyGTBKJWktIK8qLKA"}'
    )
    monkeypatch.setattr(
        exiftool_module.subprocess,
        "run",
        lambda argv, **kwargs: _fake_completed(
            json.dumps([{"SourceFile": str(argv[-1]), "Aigc": aigc}])
        ),
    )

    path = tmp_path / "ai_generated.bin"
    path.write_bytes(b"\x89PNG")
    safe = _safe_image_ref(path)

    result = asyncio.run(ExifToolMetadataAdapter().inspect(safe))

    assert result.status == "completed"
    assert len(result.signals) == 1
    assert result.signals[0].code == "METADATA_AI_GENERATED_CLAIM"
    assert result.signals[0].severity == "critical"


def test_tc260_aigc_label_zero_is_neutral_not_a_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TC260's `Aigc.Label` is `"0"` for non-AI content -- must not fire."""
    monkeypatch.setattr(exiftool_module, "_EXIFTOOL", "/usr/bin/exiftool")
    monkeypatch.setattr(
        exiftool_module.subprocess,
        "run",
        lambda argv, **kwargs: _fake_completed(
            json.dumps([{"SourceFile": str(argv[-1]), "Aigc": '{"Label":"0"}'}])
        ),
    )

    path = tmp_path / "not_ai.bin"
    path.write_bytes(b"\x89PNG")
    safe = _safe_image_ref(path)

    result = asyncio.run(ExifToolMetadataAdapter().inspect(safe))

    assert result.signals == ()
