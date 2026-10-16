"""P2-03c: synthetic-only inventory parser security and release boundary tests."""
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
from uuid import uuid4

import pytest

from app.provider_read_boundary import (
    CONTENT_TYPE, MAX_BODY_BYTES, MAX_ITEMS, MAX_UNITS, PROVIDER_ID,
    SCHEMA, DemoInventoryItem, ReadBoundaryDenied,
    demo_inventory_fixture, demo_marker, parse_demo_inventory_fixture,
)

ROOT = Path(__file__).resolve().parents[1]


def fixture(tenant, items=(("DEMO-SKU-MAIZE", 120),)):
    return demo_inventory_fixture(tenant, items)


def parse(tenant, body, content_type=CONTENT_TYPE):
    return parse_demo_inventory_fixture(
        tenant_id=tenant, body=body, content_type=content_type,
    )


def test_valid_offline_preview_always_denied_and_untrusted():
    tenant = uuid4()
    view = parse(tenant, fixture(tenant))
    assert view.items == (DemoInventoryItem("DEMO-SKU-MAIZE", 120),)
    assert view.tenant_marker == demo_marker(tenant)
    assert view.decision == "DENY"
    assert view.source == "UNTRUSTED_DEMO_FIXTURE"
    assert not view.tenancy_authenticated
    assert not view.customer_consent_verified
    assert not view.read_scope_verified
    assert not view.provider_identity_verified
    assert not view.network_request_performed
    assert not view.customer_data_read
    assert not view.execution_authorized
    assert not view.persisted


def test_allowlisted_empty_and_multiple_items():
    tenant = uuid4()
    for items in ((), (("DEMO-SKU-MAIZE", 0), ("DEMO-SKU-SOY", MAX_UNITS))):
        assert len(parse(tenant, fixture(tenant, items)).items) == len(items)


def test_foreign_tenant_cannot_reuse_fixture():
    a, b = uuid4(), uuid4()
    data = fixture(a)
    with pytest.raises(ReadBoundaryDenied):
        parse(b, data)
    assert parse(a, data).items


@pytest.mark.parametrize("bad_body", [
    b"", b"[]", b"null", b"true", b"not json", b"\xff",
    b" " * (MAX_BODY_BYTES + 1),
    b'{"schema":"fake","schema":"fake"}', b'{"x":NaN}',
    7, None, "a string",
])
def test_invalid_envelope_bytes_are_denied(bad_body):
    with pytest.raises(ReadBoundaryDenied):
        parse(uuid4(), bad_body)


@pytest.mark.parametrize("wrong_type", [
    "application/json; charset=utf-8", "text/plain", "APPLICATION/JSON",
    None, 0, b"application/json",
])
def test_content_type_must_be_exact(wrong_type):
    tenant = uuid4()
    with pytest.raises(ReadBoundaryDenied):
        parse(tenant, fixture(tenant), wrong_type)


@pytest.mark.parametrize("changes", [
    {"schema": "provider.live.v1"},
    {"provider": "ACTUAL-SERVICE"},
    {"tenant_marker": "DEMO-TENANT-INTRUDER"},
    {"items": "not-array"},
    {"items": None},
    {"items": [{}]},
    {"items": [{"sku": "DEMO-SKU-MAIZE", "available_units": True}]},
    {"items": [{"sku": "DEMO-SKU-MAIZE", "available_units": -1}]},
    {"items": [{"sku": "DEMO-SKU-MAIZE", "available_units": MAX_UNITS+1}]},
    {"items": [{"sku": "REAL-SKU-CUSTOMER", "available_units": 4}]},
    {"items": [{"sku": "DEMO-SKU-A", "available_units": 4}]},
    {"items": [{"sku": "DEMO-SKU-MAIZE", "available_units": "5"}]},
    {"items": [{"sku": "DEMO-SKU-MAIZE", "available_units": 1, "pii": "secret"}]},
    {"items": [{"sku": "DEMO-SKU-MAIZE", "available_units": 1} for _ in range(2)]},
    {"items": [{"sku": f"DEMO-SKU-ITEM-{n}", "available_units": n}
               for n in range(MAX_ITEMS+1)]},
    {"external_url": "https://example.com/"},
])
def test_untrusted_extra_fields_and_invalid_items_are_denied(changes):
    tenant = uuid4()
    payload = json.loads(fixture(tenant))
    payload.update(changes)
    with pytest.raises(ReadBoundaryDenied):
        parse(tenant, json.dumps(payload).encode())


def test_duplicate_object_keys_rejected_at_nested_and_root():
    t=uuid4()
    original=fixture(t)
    malicious=original.replace(
        b'"available_units":120', b'"available_units":120,"available_units":0'
    )
    with pytest.raises(ReadBoundaryDenied):
        parse(t, malicious)
    malicious=original.replace(
        b'"provider":"DEMO-INVENTORY-PROVIDER"',
        b'"provider":"DEMO-INVENTORY-PROVIDER","provider":"OTHER"',
    )
    with pytest.raises(ReadBoundaryDenied):
        parse(t, malicious)


def test_invalid_tenant_identity_is_denied():
    for t in ("not-a-uuid", None, b"a", True, 8):
        with pytest.raises(ReadBoundaryDenied):
            demo_marker(t)
        with pytest.raises(ReadBoundaryDenied):
            demo_inventory_fixture(t, ())


def test_demo_fixture_creator_rejects_invalid_items():
    t=uuid4()
    for x in (
        (("LIVE-SKU", 3),), (("DEMO-SKU-MAIZE", True),),
        (("DEMO-SKU-MAIZE", 9), ("DEMO-SKU-MAIZE", 6)),
        ([("DEMO-SKU-MAIZE", 1)]),
    ):
        with pytest.raises(ReadBoundaryDenied):
            demo_inventory_fixture(t,x)


def test_view_is_immutable_and_not_authority():
    t=uuid4()
    view=parse(t, fixture(t))
    with pytest.raises(FrozenInstanceError):
        view.execution_authorized=True
    forged=replace(view, execution_authorized=True)
    assert forged.decision == "DENY"
    assert forged.source == "UNTRUSTED_DEMO_FIXTURE"
    # Nothing accepts the forged view as authorization for external reads.


def test_no_api_or_transport_and_domain_contract_stays_draft():
    content=(ROOT / "apps/api/app/provider_read_boundary.py").read_text()
    for forbidden in (
        "APIRouter(", "import httpx", "import requests", "import socket",
        "import subprocess", "import psycopg", "urlopen(",
    ):
        assert forbidden not in content
    main=(ROOT / "apps/api/app/main.py").read_text()
    assert "provider_read_boundary" not in main
    manifest=json.loads((ROOT / "contracts/domains/v1/operations.json").read_text())
    assert manifest["default_policy"] == "DENY"
    assert manifest["adapter_state"] == "unbound"
    assert manifest["external_access"] is False
