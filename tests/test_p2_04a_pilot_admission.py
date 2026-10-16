"""Adversarial P2-04a scoped private pilot admission (no real staff / providers).

All signing keys below are ephemeral in-memory CI fixtures. There are no
private keys, IdP credentials, customer data or production admission bundles
committed to source control.
"""
from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime,timezone,timedelta
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import HTTPException
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"apps/api"))
from app.p2_04a_pilot_admission import (
    AdmissionDenied,GATES,KIND,canonical,decode,verify_bundle,
    verify_private_pilot_admission,require_private_pilot_admission,
)

NOW=datetime(2026,10,16,20,0,tzinfo=timezone.utc)
TENANT="123e4567-e89b-12d3-a456-426614174000"
COMMIT="a"*40
ORIGIN="https://staging.private.example.org"
ISSUER="https://idp.private.example.org"

def b64(v:bytes)->str:
    return base64.urlsafe_b64encode(v).rstrip(b"=").decode("ascii")


@pytest.fixture
def signed():
    owner=Ed25519PrivateKey.generate()
    independent=Ed25519PrivateKey.generate()
    def key(k):
        return b64(k.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        ))
    doc={
        "schema_version":1,"purpose":"PRIVATE_STAGING_AGGREGATE_MEASUREMENT",
        "repository":"AhmadibOfficial/MetaAutomate",
        "commit_sha":COMMIT,
        "tenant_id":TENANT,
        "workspace_origin":ORIGIN,
        "oidc_issuer":ISSUER,
        "issued_at":"2026-10-16T19:59:00Z",
        "expires_at":"2026-10-16T21:00:00Z",
        "environment":"PRIVATE_STAGING",
        "consent_scope":"AGGREGATE_ONLY",
        "external_execution":False,
        "evidence":{
            gate:{
                "artifact_sha256":f"{i+1:x}"*64,
                "witness_url":f"https://evidence.example.org/{gate.lower()}/review",
                "witness_kind":KIND[gate],
            } for i,gate in enumerate(sorted(GATES))
        },
    }
    def sign(payload=None, *, keys=(owner,independent)):
        obj=deepcopy(payload or doc)
        encoded=canonical(obj)
        obj["signatures"]=[
            {"role":role,"signature":b64(key_.sign(encoded))}
            for role,key_ in zip(("OWNER","INDEPENDENT_REVIEWER"),keys)
        ]
        return canonical(obj)
    return {
        "doc":doc,"raw":sign(),"sign":sign,
        "owner":key(owner),"reviewer":key(independent),
        "keys":(owner,independent),
    }


def verify(x,**changes):
    args={
        "owner_pub":x["owner"],"reviewer_pub":x["reviewer"],
        "expected_commit":COMMIT,
        "expected_tenant":TENANT,
        "expected_origin":ORIGIN,
        "expected_issuer":ISSUER,
        "now":NOW,
    }
    args.update(changes)
    return verify_bundle(x["raw"],**args)


def test_two_distinct_valid_signatures_only_authenticate_attested_claims(signed):
    x=verify(signed)
    assert x["tenant_id"]==TENANT
    assert x["commit_sha"]==COMMIT
    assert x["scope"]=="PRIVATE_STAGING_AGGREGATE_MEASUREMENT"
    assert x["source_claims_signed"] is True
    assert x["actual_live_provider_evidence_verified_by_this_module"] is False
    assert x["operational_foundation_promoted"] is False
    assert x["external_agents_enabled"] is False


@pytest.mark.parametrize("name,value",[
    ("purpose","PRODUCTION_AGENT_EXECUTION"),
    ("repository","other/repository"),
    ("environment","PRODUCTION"),
    ("environment","SIMULATED_CI"),
    ("consent_scope","ALL_CUSTOMER_RECORDS"),
    ("external_execution",True),
    ("external_execution",0),
    ("commit_sha","b"*40),
    ("commit_sha","bad-sha"),
    ("tenant_id","aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"),
    ("workspace_origin","https://evil.example.org"),
    ("oidc_issuer","https://other-idp.example.org"),
    ("schema_version",True),
    ("schema_version",2),
])
def test_signed_but_wrong_scope_is_never_accepted(signed,name,value):
    doc=deepcopy(signed["doc"])
    doc[name]=value
    signed["raw"]=signed["sign"](doc)
    with pytest.raises(AdmissionDenied):
        verify(signed)


@pytest.mark.parametrize("change",[
    lambda x:x.pop("F04"),
    lambda x:x["F04"].update({"witness_kind":"CI_PASSED"}),
    lambda x:x["F06"].update({"artifact_sha256":"a"*63}),
    lambda x:x["F07"].update({"witness_url":"http://insecure.example.org/evidence"}),
    lambda x:x["F08"].update({"witness_url":"https://localhost/evidence"}),
    lambda x:x["F05"].update({"witness_url":"https://evidence.example.org:8080/review"}),
    lambda x:x["F06"].update({"witness_url":"https://username:pass@evidence.example.org/review"}),
])
def test_witness_evidence_must_have_exact_shape_and_scope(signed,change):
    doc=deepcopy(signed["doc"])
    change(doc["evidence"])
    signed["raw"]=signed["sign"](doc)
    with pytest.raises(AdmissionDenied):
        verify(signed)


@pytest.mark.parametrize("issued,expired",[
    ("2026-10-16T20:01:00Z","2026-10-16T21:00:00Z"),
    ("2026-10-16T19:00:00Z","2026-10-16T20:00:00Z"),
    ("2026-10-16T19:59:00Z","2026-10-18T21:00:00Z"),
    ("2026-10-16T20:00:00Z","2026-10-16T19:59:00Z"),
    ("2026-10-16T19:59:00+00:00","2026-10-16T21:00:00Z"),
    ("2026-10-16T19:59:00Z","2026-11-31T21:00:00Z"),
])
def test_stale_future_and_noncanonical_timestamps_are_denied(signed,issued,expired):
    doc=deepcopy(signed["doc"])
    doc["issued_at"]=issued
    doc["expires_at"]=expired
    signed["raw"]=signed["sign"](doc)
    with pytest.raises(AdmissionDenied):verify(signed)


def test_old_reviewer_signature_is_invalid_after_a_document_edit(signed):
    doc=decode(signed["raw"])
    doc["tenant_id"]="aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"
    with pytest.raises(AdmissionDenied):
        verify_bundle(canonical(doc),owner_pub=signed["owner"],reviewer_pub=signed["reviewer"],
                      expected_commit=COMMIT,expected_tenant=doc["tenant_id"],
                      expected_origin=ORIGIN,expected_issuer=ISSUER,now=NOW)


def test_no_one_person_two_keys_and_no_missing_signatures(signed):
    raw_owner=signed["keys"][0]
    altered=signed["sign"](keys=(raw_owner,raw_owner))
    with pytest.raises(AdmissionDenied):
        verify_bundle(altered,owner_pub=signed["owner"],reviewer_pub=signed["owner"],
                      expected_commit=COMMIT,expected_tenant=TENANT,
                      expected_origin=ORIGIN,expected_issuer=ISSUER,now=NOW)
    doc=decode(signed["raw"])
    doc["signatures"]=doc["signatures"][:1]
    with pytest.raises(AdmissionDenied):
        verify_bundle(canonical(doc),owner_pub=signed["owner"],reviewer_pub=signed["reviewer"],
                      expected_commit=COMMIT,expected_tenant=TENANT,
                      expected_origin=ORIGIN,expected_issuer=ISSUER,now=NOW)


@pytest.mark.parametrize("raw",[
    b'{"schema_version":1,"schema_version":1}',
    b'{"schema_version":NaN}',
    b'',
    b'\x00',
    b'{' + b' ' * 16500 + b'}',
])
def test_malformed_untrusted_bundle_rejected(raw):
    with pytest.raises(AdmissionDenied):decode(raw)


def test_runtime_is_default_off_even_with_local_manifest(signed,monkeypatch,tmp_path):
    record=tmp_path/"approval.json"
    record.write_bytes(signed["raw"])
    for key in ("MAT_PILOT_OUTCOMES_ENABLED","WORKSPACE_AUTH_MODE","MAT_PILOT_ADMISSION_FILE"):
        monkeypatch.delenv(key,raising=False)
    with pytest.raises(AdmissionDenied):
        verify_private_pilot_admission()


def test_runtime_revokes_on_file_removal_and_rechecks_per_request(signed,monkeypatch,tmp_path):
    record=tmp_path/"approval.json"
    record.write_bytes(signed["raw"])
    settings={
        "MAT_PILOT_OUTCOMES_ENABLED":"1",
        "WORKSPACE_AUTH_MODE":"oidc",
        "MAT_PILOT_ADMISSION_FILE":str(record),
        "MAT_PILOT_OWNER_VERIFY_KEY":signed["owner"],
        "MAT_PILOT_REVIEWER_VERIFY_KEY":signed["reviewer"],
        "MAT_DEPLOY_COMMIT_SHA":COMMIT,
        "MAT_PILOT_TENANT_ID":TENANT,
        "WORKSPACE_ORIGIN":ORIGIN,
        "OIDC_ISSUER":ISSUER,
    }
    for k,v in settings.items():monkeypatch.setenv(k,v)
    # Avoid dependence on current CI wall-clock; the signed fixture may
    # remain within its short validity window when the runner starts.
    from app import p2_04a_pilot_admission as admission
    monkeypatch.setattr(admission,"verify_bundle",lambda raw,**kwargs: {
        "tenant_id":TENANT, "commit_sha":COMMIT,
        "scope":"PRIVATE_STAGING_AGGREGATE_MEASUREMENT",
    })
    assert verify_private_pilot_admission()["tenant_id"]==TENANT
    assert require_private_pilot_admission(SimpleNamespace(
        principal=SimpleNamespace(organization_id=UUID(TENANT)),
    )) is None
    with pytest.raises(HTTPException) as foreign:
        require_private_pilot_admission(SimpleNamespace(
            principal=SimpleNamespace(
                organization_id=UUID("aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa")
            ),
        ))
    assert foreign.value.status_code==403
    record.unlink()
    with pytest.raises(AdmissionDenied):
        verify_private_pilot_admission()
    with pytest.raises(HTTPException) as revoked:
        require_private_pilot_admission(SimpleNamespace(
            principal=SimpleNamespace(organization_id=UUID(TENANT)),
        ))
    assert revoked.value.status_code==503


def test_new_admission_checks_are_really_wired_to_all_pilot_routes():
    main=(ROOT/"apps/api/app/main.py").read_text()
    assert "verify_private_pilot_admission()" in main
    assert "pilot_outcomes_router.dependencies.append(Depends(require_private_pilot_admission))" in main
    assert "app.include_router(pilot_outcomes_router)" in main
    assert main.index("verify_private_pilot_admission()") < main.index("app.include_router(pilot_outcomes_router)")
    assert 'MAT_PILOT_OUTCOMES_ENABLED") == "1"' in main
