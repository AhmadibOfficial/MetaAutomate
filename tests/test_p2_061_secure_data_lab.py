"""P2-061: real local SQLite/AES-GCM negative trust and governance tests.

No customer data, network, production databases, external providers or files
outside pytest's temporary directory. Uses fictional inventory and UUID users.
"""
from __future__ import annotations

import base64
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app import secure_inventory_lab as data_lab_module
from app.secure_inventory_lab import SecureInventoryLab, DataLabError, parse_inventory

DATA = (b"sku,name,stock,weekly_sales,unit_price_kobo\n"
        b"CAP-001,Sample Cotton Cap,20,2,850000\n"
        b"FAB-002,Sample Kaftan,14,0,3500000\n")
KEY = b"F" * 32
ORG_A = UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
ORG_B = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")


def actor(tenant=ORG_A, role="OWNER", user=None):
    return SimpleNamespace(organization_id=tenant, role=role, user_id=user or uuid4())


@pytest.fixture
def lab(tmp_path):
    return SecureInventoryLab(tmp_path / "secure-data.sqlite", KEY)


def save(lab, principal=None, *, content=DATA, now=2000000000, retention=7):
    return lab.import_csv(principal or actor(), content, retention_days=retention,
                          consent_claim="OWNER_AUTHORIZED_INVENTORY_NO_PERSONAL_DATA",
                          now=now)


def test_encrypts_at_rest_with_aes_gcm_and_denies_cross_tenant(lab):
    owner = actor(ORG_A)
    rival = actor(ORG_B)
    result = save(lab, owner)
    assert result["encrypted_at_rest"] is True
    assert lab.path.read_bytes().find(b"Sample Cotton Cap") == -1
    assert lab.path.read_bytes().find(b"CAP-001") == -1
    assert lab.get_document(owner, UUID(result["document_id"]), now=2000000001)["records"][0]["sku"] == "CAP-001"
    assert lab.list_documents(rival, now=2000000001) == []
    with pytest.raises(DataLabError, match="not found"):
        lab.get_document(rival, UUID(result["document_id"]), now=2000000001)
    with pytest.raises(DataLabError, match="not found"):
        lab.delete_document(rival, UUID(result["document_id"]), now=2000000001)


def test_authorization_roles_for_import_read_and_deletion(lab):
    writer = actor(role="ADMIN")
    reader = actor(role="OPERATOR")
    stranger = actor(role="VIEWER")
    record = save(lab, writer)
    doc = UUID(record["document_id"])
    assert len(lab.list_documents(reader, now=2000000001)) == 1
    assert lab.get_document(reader, doc, now=2000000001)["record_count"] == 2
    with pytest.raises(DataLabError):
        save(lab, reader)
    with pytest.raises(DataLabError):
        lab.delete_document(reader, doc, now=2000000001)
    with pytest.raises(DataLabError):
        lab.list_documents(stranger, now=2000000001)
    with pytest.raises(DataLabError):
        lab.import_csv(SimpleNamespace(organization_id="forged", user_id=uuid4(), role="OWNER"),
                       DATA, retention_days=7,
                       consent_claim="OWNER_AUTHORIZED_INVENTORY_NO_PERSONAL_DATA")


def test_requires_explicit_source_claim_and_bounded_retention(lab):
    owner = actor()
    with pytest.raises(DataLabError, match="declaration"):
        lab.import_csv(owner, DATA, retention_days=7, consent_claim="UNAUTHORIZED")
    for days in (0, 31, -1, True, "7"):
        with pytest.raises(DataLabError):
            lab.import_csv(owner, DATA, retention_days=days,
                           consent_claim="OWNER_AUTHORIZED_INVENTORY_NO_PERSONAL_DATA")


def test_cross_tenant_distinct_ciphertexts_and_key_failures(lab, tmp_path):
    owner_a, owner_b = actor(ORG_A), actor(ORG_B)
    a = save(lab, owner_a)
    b = save(lab, owner_b)
    with sqlite3.connect(lab.path) as conn:
        values = conn.execute("SELECT tenant_id, encrypted FROM inventory_documents ORDER BY tenant_id").fetchall()
    assert values[0][1] != values[1][1]
    assert len(values) == 2
    rotated = SecureInventoryLab(lab.path, b"K" * 32)
    with pytest.raises(DataLabError, match="cannot be verified"):
        rotated.get_document(owner_a, UUID(a["document_id"]), now=2000000001)


def test_ciphertext_tamper_detected(lab):
    owner = actor()
    record = save(lab, owner)
    doc = record["document_id"]
    with sqlite3.connect(lab.path) as conn:
        c = conn.execute("SELECT encrypted FROM inventory_documents WHERE document_id=?", (doc,)).fetchone()[0]
        conn.execute("UPDATE inventory_documents SET encrypted=? WHERE document_id=?",
                     (bytes([c[0] ^ 1]) + c[1:], doc))
    with pytest.raises(DataLabError, match="cannot be verified"):
        lab.get_document(owner, UUID(doc), now=2000000001)


def test_aad_rejects_ciphertext_swapped_between_documents(lab):
    owner = actor()
    x = save(lab, owner)
    y = save(lab, owner)
    with sqlite3.connect(lab.path) as conn:
        first = conn.execute("SELECT nonce,encrypted FROM inventory_documents WHERE document_id=?",
                             (x["document_id"],)).fetchone()
        conn.execute("UPDATE inventory_documents SET nonce=?,encrypted=? WHERE document_id=?",
                     (first[0], first[1], y["document_id"]))
    with pytest.raises(DataLabError):
        lab.get_document(owner, UUID(y["document_id"]), now=2000000001)


def test_active_record_delete_and_tombstone_audit(lab):
    owner = actor()
    result = save(lab, owner)
    doc = UUID(result["document_id"])
    before = lab.verify_audit(owner)
    assert before["events"] == 1
    response = lab.delete_document(owner, doc, now=2000000001)
    assert response["deletion_scope"] == "ACTIVE_SQLITE_RECORD_ONLY"
    assert response["backup_copies_verified_deleted"] is False
    assert lab.list_documents(owner, now=2000000001) == []
    with pytest.raises(DataLabError):
        lab.get_document(owner, doc, now=2000000001)
    assert lab.verify_audit(owner)["events"] == 2



def test_read_and_audit_are_atomic_against_concurrent_deletion(lab, monkeypatch):
    """SQLite must not allow another writer to delete after lookup but before audit."""
    owner = actor()
    saved = save(lab, owner)
    identifier = UUID(saved["document_id"])
    real_unseal = data_lab_module._unseal
    observed = []

    def inspect_while_decrypting(*args, **kwargs):
        # The read transaction must already hold a RESERVED write lock here.
        # A 0-second timeout makes this deterministic and leaves no stray writer.
        rival = sqlite3.connect(lab.path, timeout=0)
        try:
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                rival.execute("DELETE FROM inventory_documents WHERE document_id=?",
                              (str(identifier),))
            observed.append(True)
        finally:
            rival.close()
        return real_unseal(*args, **kwargs)

    monkeypatch.setattr(data_lab_module, "_unseal", inspect_while_decrypting)
    read = lab.get_document(owner, identifier, now=2000000001)
    assert observed == [True]
    assert read["records"][0]["sku"] == "CAP-001"
    assert lab.verify_audit(owner)["events"] == 2

    # After the serialized read commits, a normal authorized deletion can proceed.
    assert lab.delete_document(owner, identifier, now=2000000002)["deleted"] is True
    assert lab.verify_audit(owner)["events"] == 3


def test_failed_decryption_cannot_append_read_audit(lab):
    """Authenticity rejection rolls back without fabricating a successful read."""
    owner = actor()
    saved = save(lab, owner)
    identifier = UUID(saved["document_id"])
    with sqlite3.connect(lab.path) as conn:
        conn.execute("UPDATE inventory_documents SET actor_id=? WHERE document_id=?",
                     (str(uuid4()), str(identifier)))
    with pytest.raises(DataLabError, match="cannot be verified"):
        lab.get_document(owner, identifier, now=2000000001)
    assert lab.verify_audit(owner)["events"] == 1


def test_read_is_audited(lab):
    owner = actor()
    record = save(lab, owner)
    lab.get_document(owner, UUID(record["document_id"]), now=2000000001)
    assert lab.verify_audit(owner)["events"] == 2


def test_retention_expiry_hides_records_until_manual_purge(lab):
    owner = actor()
    result = save(lab, owner, retention=1)
    doc = UUID(result["document_id"])
    assert len(lab.list_documents(owner, now=2000086399)) == 1
    assert lab.list_documents(owner, now=2000086400) == []
    with pytest.raises(DataLabError, match="expired"):
        lab.get_document(owner, doc, now=2000086400)
    with sqlite3.connect(lab.path) as conn:
        assert conn.execute("SELECT count(*) FROM inventory_documents").fetchone()[0] == 1
    assert lab.purge_expired(owner, now=2000086400)["purged"] == 1
    with sqlite3.connect(lab.path) as conn:
        assert conn.execute("SELECT count(*) FROM inventory_documents").fetchone()[0] == 0
    assert lab.verify_audit(owner)["events"] == 2


def test_purge_cannot_delete_other_tenant(lab):
    owner_a, owner_b = actor(ORG_A), actor(ORG_B)
    save(lab, owner_a, retention=1)
    save(lab, owner_b, retention=1)
    assert lab.purge_expired(owner_a, now=2000086400)["purged"] == 1
    assert lab.verify_audit(owner_a)["events"] == 2
    assert len(lab.list_documents(owner_b, now=2000000001)) == 1


def test_audit_hmac_chain_detects_log_tampering(lab):
    owner = actor()
    rec = save(lab, owner)
    lab.delete_document(owner, UUID(rec["document_id"]), now=2000000002)
    assert lab.verify_audit(owner)["integrity"] == "LOCAL_HMAC_CHAIN_VERIFIED"
    with sqlite3.connect(lab.path) as conn:
        conn.execute("UPDATE inventory_audit SET event='FORGED' WHERE tenant_id=? AND sequence_number=1",
                     (str(ORG_A),))
    with pytest.raises(DataLabError, match="integrity"):
        lab.verify_audit(owner)


def test_authentication_wrong_roles_and_cross_tenant_audit_fail_closed(lab):
    other = actor(ORG_B)
    with pytest.raises(DataLabError):
        lab.verify_audit(actor(role="VIEWER"))
    assert lab.verify_audit(other)["events"] == 0
    with pytest.raises(DataLabError):
        lab.purge_expired(actor(role="OPERATOR"), now=2000000001)


@pytest.mark.parametrize("bad", [
    b"", b"sku,name,stock,weekly_sales,unit_price_kobo\n",
    b"sku,name,stock,weekly_sales,unit_price_kobo\nA-1,=SUM,1,0,100",
    b"sku,name,stock,weekly_sales,unit_price_kobo\nA-1,+FORMULA,1,0,100",
    b"sku,name,stock,weekly_sales,unit_price_kobo\nA-1,Safe,1,0,0",
    b"sku,name,stock,weekly_sales,unit_price_kobo\nA-1,Safe,-1,0,100",
    b"sku,name,stock,weekly_sales,unit_price_kobo\nA-1,Safe,2,0,1e6",
    b"sku,name,stock,weekly_sales,unit_price_kobo\nA-1,Safe,2,1.5,100",
    b"sku,name,stock,weekly_sales,unit_price_kobo\nA-1,Safe,2,0,100,extra",
    b"sku,name,stock,weekly_sales,unit_price_kobo\nA-1,Safe,2,0",
    b"sku,name,stock,weekly_sales,unit_price_kobo\nA-1,Safe,2,0,100\nA-1,Other,3,0,100",
    b"sku,name,stock,weekly_sales,unit_price_kobo\nA-1,\"unterminated,2,0,100",
    b"sku,name,stock,weekly_sales,unit_price_kobo\nA-1,Name with\nnewline,2,0,100",
    b"\xff\xff",
])
def test_csv_rejects_invalid_or_formula_data(bad):
    with pytest.raises(DataLabError):
        parse_inventory(bad)


def test_csv_roundtrip_quoted_commas_bom_crlf():
    x = b'\xef\xbb\xbfsku,name,stock,weekly_sales,unit_price_kobo\r\nA-001,"A, sample ""display""",8,2,1050\r\n'
    assert parse_inventory(x)[0]["name"] == 'A, sample "display"'


def test_csv_hard_caps_and_quota(lab):
    with pytest.raises(DataLabError):
        parse_inventory(DATA + b"X" * (64 * 1024))
    over = b"sku,name,stock,weekly_sales,unit_price_kobo\n" + (
        b"A-000,Long Sample,2,1,100\n" * 201)
    with pytest.raises(DataLabError):
        parse_inventory(over)
    owner = actor()
    for _ in range(25):
        save(lab, owner)
    with pytest.raises(DataLabError, match="quota"):
        save(lab, owner)


def test_missing_or_incorrect_root_key_rejected(lab, tmp_path, monkeypatch):
    with pytest.raises(DataLabError):
        SecureInventoryLab(tmp_path / "x.sqlite", b"too short")
    monkeypatch.setenv("MAT_DATA_LAB_SQLITE", str(tmp_path / "other.sqlite"))
    monkeypatch.setenv("MAT_DATA_LAB_KEY_B64", base64.b64encode(KEY).decode())
    assert SecureInventoryLab.from_environment().path.name == "other.sqlite"
    monkeypatch.setenv("MAT_DATA_LAB_KEY_B64", "not a valid base64")
    with pytest.raises(DataLabError):
        SecureInventoryLab.from_environment()


def test_refuses_symlinked_storage(tmp_path):
    original = tmp_path / "original.sqlite"
    lab = SecureInventoryLab(original, KEY)
    alias = tmp_path / "alias.sqlite"
    alias.symlink_to(original)
    with pytest.raises(DataLabError, match="non-symlink"):
        SecureInventoryLab(alias, KEY)


def test_no_production_or_provider_side_effect_imports():
    root = ROOT / "apps/api/app"
    source = (root / "secure_inventory_lab.py").read_text()
    api = (root / "secure_data_lab_api.py").read_text()
    main = (root / "main.py").read_text()
    assert "MAT_DATA_LAB_ENABLED" in main
    assert "LOCAL_REHEARSAL_ONLY" in api
    assert "WORKSPACE_AUTH_MODE" in api
    assert "get_tenant_session" in api
    assert "PRAGMA secure_delete=ON" in source
    assert "AESGCM" in source and "HKDF" in source
    for disallowed in ("request.client.organization_id", "mat_deploy", "trigger_deploy",
                       "publish_social", "requests.post("):
        assert disallowed not in source + api


@pytest.mark.parametrize("column,value", [
    ("retained_until", 2009999999),
    ("source_sha256", "f" * 64),
    ("actor_id", "00000000-0000-4000-8000-000000000001"),
    ("record_count", 20),
])
def test_provenance_and_retention_metadata_authenticated_by_aesgcm(lab, column, value):
    owner = actor()
    result = save(lab, owner)
    doc = result["document_id"]
    with sqlite3.connect(lab.path) as conn:
        # Fixed test-controlled column names only; never derived from HTTP input.
        conn.execute("UPDATE inventory_documents SET " + column + "=? WHERE document_id=?",
                     (value, doc))
    with pytest.raises(DataLabError):
        lab.get_document(owner, UUID(doc), now=2000000001)
