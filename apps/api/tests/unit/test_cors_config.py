"""Unit tests for the CORS allowlist env-config reader."""

from __future__ import annotations

import pytest

from receipt_risk.adapters.api.cors_config import allowed_origins


def test_no_env_var_yields_empty_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RECEIPT_RISK_CORS_ALLOWED_ORIGINS", raising=False)
    assert allowed_origins() == []


def test_single_origin_parsed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RECEIPT_RISK_CORS_ALLOWED_ORIGINS", "https://app.example.com")
    assert allowed_origins() == ["https://app.example.com"]


def test_multiple_comma_separated_origins_parsed_and_trimmed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "RECEIPT_RISK_CORS_ALLOWED_ORIGINS",
        " https://app.example.com , https://staging.example.com ",
    )
    assert allowed_origins() == ["https://app.example.com", "https://staging.example.com"]


def test_empty_string_env_var_yields_empty_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RECEIPT_RISK_CORS_ALLOWED_ORIGINS", "")
    assert allowed_origins() == []
