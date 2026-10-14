"""P2-04b synthetic webhook-proof contract; no HTTP/provider or real keys."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
from pathlib import Path
from uuid import uuid4

import pytest

from app.synthetic_webhook_proof import (
    DemoWebhookDenied, EVENT_TYPE, MAX_EVENTS_PER_TENANT,
    OfflineSyntheticWebhookVerifier, SCHEMA, sign_synthetic_fixture,
    synthetic_tenant_marker,
)

KEY_ID = "DEMO-KID-PRIMARY"
KEY = b"DEMO-KEY-MATERIAL-THIS-IS-A-SYNTHETIC-FIXTURE-0001"


def payload(tenant, *, event_id="DEMO-EVT-ABC123", **changes):
    document = {
        "schema": SCHEMA, "event_id": event_id,
        "tenant_marker": synthetic_tenant_marker(tenant),
        "event_type": EVENT_TYPE,
        "scenario": "DEMO-INVENTORY-LOW-STOCK", "issued_tick": 100,
    }
    document.update(changes)
    return json.dumps(document, sort_keys=True, separators=(",", ":")).encode()


def fixture(tenant=None, *, key_id=KEY_ID, key=KEY, raw=None):
    tenant = tenant or uuid4()
    raw = raw if raw is not None else payload(tenant)
    signature = sign_synthetic_fixture(tenant, key_id, key, raw)
    return tenant, OfflineSyntheticWebhookVerifier({(tenant, key_id): key}), raw, signature


def check(tenant, verifier, raw, signature, *, key_id=KEY_ID, now=101):
    return verifier.verify_once(tenant, key_id, raw, signature, now_tick=now)


def test_proof_is_pure_simulation_without_external_effect():
    tenant, verifier, raw, signature = fixture()
    proof = check(tenant, verifier, raw, signature)
    assert proof.event_id == "DEMO-EVT-ABC123"
    assert proof.tenant_demo_marker == synthetic_tenant_marker(tenant)
    assert proof.accepted_for_simulation is True
    assert proof.executed is False
    assert proof.persisted is False
    assert proof.actual_business_data is False
    assert proof.webhook_endpoint_available is False
    assert proof.simulation_only is True


def test_same_signed_event_is_rejected_on_replay():
    tenant, verifier, raw, signature = fixture()
    check(tenant, verifier, raw, signature)
    with pytest.raises(DemoWebhookDenied):
        check(tenant, verifier, raw, signature)


def test_tampered_payload_fails_signature_before_parse():
    tenant, verifier, raw, signature = fixture()
    changed = raw.replace(b"DEMO-INVENTORY-LOW-STOCK", b"DEMO-INVENTORY-IN-RANGE")
    with pytest.raises(DemoWebhookDenied):
        check(tenant, verifier, changed, signature)


def test_wrong_tenant_cannot_use_other_tenant_signature():
    a, verifier, raw, signature = fixture()
    b = uuid4()
    with pytest.raises(DemoWebhookDenied):
        check(b, verifier, raw, signature)
    assert check(a, verifier, raw, signature).event_id == "DEMO-EVT-ABC123"


def test_key_ids_are_scoped_and_other_key_cannot_validate():
    tenant = uuid4()
    verifier = OfflineSyntheticWebhookVerifier({
        (tenant, KEY_ID): KEY,
        (tenant, "DEMO-KID-BACKUP"): b"DEMO-KEY-MATERIAL-ALTERNATE-SYNTHETIC-FIXTURE-0002",
    })
    body = payload(tenant)
    sig = sign_synthetic_fixture(tenant, KEY_ID, KEY, body)
    with pytest.raises(DemoWebhookDenied):
        check(tenant, verifier, body, sig, key_id="DEMO-KID-BACKUP")
    assert check(tenant, verifier, body, sig).simulation_only


def test_alternative_active_demo_key_is_accepted():
    tenant = uuid4()
    backup_id = "DEMO-KID-BACKUP"
    backup = b"DEMO-KEY-MATERIAL-ALTERNATE-SYNTHETIC-FIXTURE-0002"
    verifier = OfflineSyntheticWebhookVerifier({(tenant, backup_id): backup})
    raw = payload(tenant)
    signature = sign_synthetic_fixture(tenant, backup_id, backup, raw)
    assert check(tenant, verifier, raw, signature, key_id=backup_id).simulation_only


def test_wrong_signature_format_and_case_are_denied():
    tenant, verifier, raw, sig = fixture()
    for bad in (sig.upper(), "SHA256=" + sig[7:], sig[:-1],
                "sha256=" + "f" * 64 + "\n", "", b"bytes", None):
        with pytest.raises(DemoWebhookDenied):
            check(tenant, verifier, raw, bad)


@pytest.mark.parametrize("now", [94, 106, 1000001, -1, True, 101.1, "101"])
def test_expired_future_or_invalid_logical_ticks_are_rejected(now):
    tenant, verifier, raw, signature = fixture()
    with pytest.raises(DemoWebhookDenied):
        check(tenant, verifier, raw, signature, now=now)


@pytest.mark.parametrize("now", [99, 100, 105])
def test_inclusive_simulated_freshness_window(now):
    tenant, verifier, raw, signature = fixture()
    assert check(tenant, verifier, raw, signature, now=now).simulation_only


@pytest.mark.parametrize("changes", [
    {"schema": "provider.actual.webhook.v1"},
    {"event_type": "CUSTOMER-CREATED"},
    {"scenario": "LIVE-CUSTOMER-DATA"},
    {"event_id": "REAL-EVENT-ID"},
    {"issued_tick": True},
    {"issued_tick": -1},
    {"issued_tick": 1000001},
    {"tenant_marker": "DEMO-TENANT-OTHER"},
    {"sensitive_customer_record": "DO_NOT_ACCEPT"},
])
def test_signed_non_demo_or_unauthorized_fields_are_rejected(changes):
    tenant = uuid4()
    raw = payload(tenant, **changes)
    _, verifier, raw, signature = fixture(tenant, raw=raw)
    with pytest.raises(DemoWebhookDenied):
        check(tenant, verifier, raw, signature)


@pytest.mark.parametrize("raw", [
    b'{"schema":"demo","schema":"duplicate"}',
    b"not-json",
    b"\xff",
    b"[]",
    b"{}",
    b" " * 2049,
    b"",
])
def test_signed_malformed_duplicate_or_oversized_bodies_are_rejected(raw):
    tenant = uuid4()
    if 0 < len(raw) <= 2048:
        tenant, verifier, raw, signature = fixture(tenant, raw=raw)
        with pytest.raises(DemoWebhookDenied):
            check(tenant, verifier, raw, signature)
    else:
        with pytest.raises(DemoWebhookDenied):
            sign_synthetic_fixture(tenant, KEY_ID, KEY, raw)


def test_event_replay_is_tenant_scoped_without_granting_tenancy():
    a, b = uuid4(), uuid4()
    verifier = OfflineSyntheticWebhookVerifier({(a, KEY_ID): KEY, (b, KEY_ID): KEY})
    for tenant in (a, b):
        raw = payload(tenant, event_id="DEMO-EVT-SHARED")
        sig = sign_synthetic_fixture(tenant, KEY_ID, KEY, raw)
        proof = check(tenant, verifier, raw, sig)
        assert proof.event_id == "DEMO-EVT-SHARED"
    with pytest.raises(DemoWebhookDenied):
        raw = payload(a, event_id="DEMO-EVT-SHARED")
        check(a, verifier, raw, sign_synthetic_fixture(a, KEY_ID, KEY, raw))


def test_same_event_id_cannot_be_reused_with_different_signed_body():
    tenant, verifier, raw, signature = fixture()
    check(tenant, verifier, raw, signature)
    other = payload(tenant, scenario="DEMO-INVENTORY-IN-RANGE")
    other_sig = sign_synthetic_fixture(tenant, KEY_ID, KEY, other)
    with pytest.raises(DemoWebhookDenied):
        check(tenant, verifier, other, other_sig)


def test_concurrent_double_delivery_accepts_only_one():
    tenant, verifier, raw, signature = fixture()
    def worker(_):
        try:
            check(tenant, verifier, raw, signature)
            return True
        except DemoWebhookDenied:
            return False
    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(worker, range(80)))
    assert sum(results) == 1


def test_full_replay_cache_fails_closed_without_eviction():
    tenant = uuid4()
    verifier = OfflineSyntheticWebhookVerifier({(tenant, KEY_ID): KEY})
    for index in range(MAX_EVENTS_PER_TENANT):
        raw = payload(tenant, event_id=f"DEMO-EVT-{index:04}")
        sig = sign_synthetic_fixture(tenant, KEY_ID, KEY, raw)
        check(tenant, verifier, raw, sig)
    raw = payload(tenant, event_id="DEMO-EVT-OVERFLOW")
    with pytest.raises(DemoWebhookDenied):
        check(tenant, verifier, raw, sign_synthetic_fixture(tenant, KEY_ID, KEY, raw))
    first = payload(tenant, event_id="DEMO-EVT-0000")
    with pytest.raises(DemoWebhookDenied):
        check(tenant, verifier, first, sign_synthetic_fixture(tenant, KEY_ID, KEY, first))


def test_per_tenant_maximum_demo_keys():
    tenant = uuid4()
    ring = {
        (tenant, "DEMO-KID-ONE"): KEY,
        (tenant, "DEMO-KID-TWO"): KEY,
        (tenant, "DEMO-KID-THREE"): KEY,
    }
    with pytest.raises(DemoWebhookDenied):
        OfflineSyntheticWebhookVerifier(ring)


@pytest.mark.parametrize("bad_key", [
    b"real_live_secret_of_external_provider_123", b"DEMO-short", "", None,
])
def test_disallow_unmarked_or_short_keys(bad_key):
    with pytest.raises(DemoWebhookDenied):
        OfflineSyntheticWebhookVerifier({(uuid4(), KEY_ID): bad_key})


def test_static_no_route_storage_worker_or_network_boundary():
    root = Path(__file__).resolve().parents[1]
    source = (root / "apps/api/app/synthetic_webhook_proof.py").read_text()
    api = (root / "apps/api/app/main.py").read_text()
    for forbidden in (
        "APIRouter", "requests.", "httpx.", "socket.", "psycopg",
        "subprocess.", "urlopen", "http://", "https://",
        "import os", "open(", "redis.",
    ):
        assert forbidden not in source
    assert "synthetic_webhook_proof" not in api
