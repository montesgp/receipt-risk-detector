"""Tests for `bootstrap/app.py`'s `/ready` and `/version` analyzer roster,
verifying the vision analyzer is wired alongside ocr/metadata/provenance
(public-api-contract spec: "Analyzer readiness roster").
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from receipt_risk.bootstrap.app import app


def test_ready_endpoint_reports_four_analyzers_including_vision() -> None:
    client = TestClient(app)
    response = client.get("/ready")

    assert response.status_code == 200
    analyzers = response.json()["analyzers"]
    assert set(analyzers) == {"ocr", "metadata", "provenance", "vision"}
    assert analyzers["vision"].startswith("mobilenetv3-embedding/")


def test_version_endpoint_includes_vision_analyzer_entry() -> None:
    client = TestClient(app)
    response = client.get("/version")

    assert response.status_code == 200
    body = response.json()
    assert "engine_version" in body
    assert "ruleset_version" in body
    assert set(body["analyzers"]) == {"ocr", "metadata", "provenance", "vision"}
