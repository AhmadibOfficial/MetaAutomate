import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from seed_registry import read_capabilities, with_database  # noqa: E402


def test_catalog_csv_has_32_drafts():
    rows = read_capabilities()
    assert len(rows) == 33
    assert len({row["capability_id"] for row in rows}) == 33
    assert all(row["lifecycle_status"] == "DRAFT" for row in rows)


def test_retargeting_database_preserves_host_and_credentials():
    base = "postgresql://user:password@postgres:5432/metaautomate"
    assert with_database(base, "metaautomate_validation") == (
        "postgresql://user:password@postgres:5432/metaautomate_validation"
    )


def test_database_override_rejects_unsafe_names():
    with pytest.raises(ValueError):
        with_database("postgresql://user:password@postgres:5432/metaautomate", "bad;DROP")
