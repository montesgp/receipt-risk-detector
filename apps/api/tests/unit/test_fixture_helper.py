"""Consumer test for `conftest.py`'s `fixture()` helper.

Traces to design.md: "`tests/conftest.py` loads the manifest, verifies each
`sha256` (drift detection), and exposes a `fixture("id")` helper."
"""

from __future__ import annotations

from conftest import fixture


def test_fixture_helper_returns_expected_declared_fields() -> None:
    clean = fixture("clean_valid_transfer")

    assert clean.declared_fields["amount"] == "125000.00"
    assert clean.declared_fields["destination_cbu"] == "2850590940090418135201"
    assert clean.expected_classification == "LOW_RISK"
    assert clean.path.exists()


def test_fixture_helper_raises_for_unknown_id() -> None:
    import pytest

    with pytest.raises(KeyError):
        fixture("does_not_exist")
