"""P2-03t cryptographic actor scopes and source-quality adversarial checks."""
import base64
from copy import deepcopy
import hmac
import json
from pathlib import Path
import sys

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))

from app.disposable_crm_authorization import (
    ACTIONS, AUDIENCE, ISSUER, verify_actor_token, require_actor_access,
)
from app.synthetic_growth_autopilot import SyntheticGrowthError
from app.synthetic_meta_lead_federation import inspect_signed_meta_event
from app.synthetic_source_quality import quality_gate, require_disposable_source

PRIVATE = Ed25519PrivateKey.generate()
PUBLIC = PRIVATE.public_key()
OTHER = Ed25519PrivateKey.generate().public_key()
NOW = 1_800_000_000
SECRET = b"test-meta-provider-secret-unique"


def encode(payload: dict, signer=PRIVATE) -> str:
    raw = json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()
    body=base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
    statement="v1."+body
    sig=base64.urlsafe_b64encode(signer.sign(statement.encode())).rstrip(b"=").decode()
    return statement+"."+sig


def claims(**changes):
    data={
        "version": 1, "issuer": ISSUER, "audience": AUDIENCE,
        "workspace": "academy_demo", "actor_ref": "SIM-ACTOR-01",
        "role": "tenant_admin", "issued_at": NOW-15,
        "expires_at": NOW+120, "token_ref": "SIM-TOKEN-01",
    }
    return data | changes


def signed_inspection():
    body=json.dumps({"object":"page","entry":[{"id":"SIM-PAGE-ACADEMY","changes":[{
        "field":"leadgen","value":{"leadgen_id":"SIM-FB-QUALITY-01",
        "form_id":"SIM-FORM-ACADEMY","page_id":"SIM-PAGE-ACADEMY"}
    }]}]},sort_keys=True,separators=(",",":")).encode()
    signature="sha256="+hmac.new(SECRET,body,"sha256").hexdigest()
    inspection=inspect_signed_meta_event(body,signature,SECRET,
                                         expected_workspace="academy_demo")
    return inspection,body


def test_verified_claim_and_permissions():
    actor=verify_actor_token(encode(claims()),PUBLIC,now=NOW)
    assert actor.workspace=="academy_demo"
    assert actor.permits("ingest_signed_metadata")
    assert actor.permits("record_consent_review")
    assert actor.permits("read_queue")
    require_actor_access(actor,"academy_demo","record_consent_review")
    with pytest.raises(SyntheticGrowthError):
        require_actor_access(actor,"bespoke_demo","record_consent_review")


@pytest.mark.parametrize("role,allowed,denied",[
    ("auditor","read_queue","assign_human"),
    ("reviewer","assign_human","ingest_signed_metadata"),
    ("tenant_admin","ingest_signed_metadata","remove_production_gate"),
])
def test_least_privilege(role,allowed,denied):
    actor=verify_actor_token(encode(claims(role=role)),PUBLIC,now=NOW)
    require_actor_access(actor,"academy_demo",allowed)
    with pytest.raises(SyntheticGrowthError):
        require_actor_access(actor,"academy_demo",denied)


def test_invalid_signer_and_payload_tampering():
    token=encode(claims())
    with pytest.raises(SyntheticGrowthError):
        verify_actor_token(token,OTHER,now=NOW)
    edited=claims(role="auditor")
    fake=encode(edited)
    # preserve signature of an unrelated privileged token — must not validate
    combined=".".join(fake.split(".")[:2]+[token.split(".")[2]])
    with pytest.raises(SyntheticGrowthError):
        verify_actor_token(combined,PUBLIC,now=NOW)


@pytest.mark.parametrize("change",[
    {"issuer":"untrusted"},
    {"audience":"production"},
    {"version":2},
    {"role":"superuser"},
    {"role":"owner"},
    {"workspace":"fake_tenant"},
    {"actor_ref":"realperson@example.invalid"},
    {"token_ref":"123"},
    {"issued_at":NOW+40},
    {"issued_at":NOW-1000,"expires_at":NOW+1500},
    {"expires_at":NOW},
    {"issued_at":NOW-15,"expires_at":NOW+500},
    {"issued_at":"2026-10-16"},
    {"expires_at":True},
    {"role":None},
])
def test_invalid_claims_fail_closed(change):
    with pytest.raises(SyntheticGrowthError):
        verify_actor_token(encode(claims(**change)),PUBLIC,now=NOW)


def test_unknown_claim_and_noncanonical_token_rejected():
    with pytest.raises(SyntheticGrowthError):
        verify_actor_token(encode(claims(phone="+234000")),PUBLIC,now=NOW)
    token=encode(claims())
    with pytest.raises(SyntheticGrowthError):
        verify_actor_token(token+".",PUBLIC,now=NOW)
    with pytest.raises(SyntheticGrowthError):
        verify_actor_token("v2."+token.split(".",1)[1],PUBLIC,now=NOW)
    with pytest.raises(SyntheticGrowthError):
        verify_actor_token(token.replace(".","/"),PUBLIC,now=NOW)
    with pytest.raises(SyntheticGrowthError):
        verify_actor_token("v1."+"A"*5000+".abc",PUBLIC,now=NOW)


def test_quality_gate_good_but_never_live_ready():
    inspection,raw=signed_inspection()
    quality=quality_gate(inspection,raw,"academy_demo")
    assert quality["quality_state"]=="READY_FOR_DISPOSABLE_REHEARSAL"
    assert quality["reason_codes"]==()
    assert quality["checked_event_count"]==1
    assert quality["production_ready"] is False
    assert quality["customer_consent_verified"] is False
    assert quality["live_event_freshness_verified"] is False
    assert require_disposable_source(inspection,raw,"academy_demo")==quality


@pytest.mark.parametrize("mutator,code",[
    (lambda e:e.update({"workspace":"bespoke_demo"}),"WORKSPACE_MISMATCH"),
    (lambda e:e.update({"signature_check":"SKIPPED"}),"SIGNED_SOURCE_NOT_ESTABLISHED"),
    (lambda e:e.update({"raw_body_sha256":"0"*64}),"SOURCE_HASH_MISMATCH"),
    (lambda e:e.update({"messages_sent":1}),"LIVE_SIDE_EFFECT_FLAG"),
    (lambda e:e.update({"real_provider_identity_verified":True}),"UNSUPPORTED_PRODUCTION_STATUS"),
    (lambda e:e.update({"unverified_contact":"fake@email.test"}),"BAD_INSPECTION_ENVELOPE"),
    (lambda e:e["events"][0].update({"customer_contact":"+234000"}),"PERSONAL_DATA_NOT_ACCEPTED"),
    (lambda e:e["events"][0].update({"consent_verified":True}),"UNSUPPORTED_LIVE_CONSENT_OR_SEND_CLAIM"),
    (lambda e:e["events"][0].update({"account_ref":"SIM-PAGE-BESPOKE"}),"PROVIDER_ACCOUNT_TENANT_MISMATCH"),
    (lambda e:e["events"][0].update({"form_ref":None}),"MISSING_SUBMITTED_FORM_PROVENANCE"),
    (lambda e:e["events"][0].update({"kind":"INBOUND_WHATSAPP_METADATA"}),"CHANNEL_KIND_MISMATCH"),
    (lambda e:e["events"].append(deepcopy(e["events"][0])),"DUPLICATE_SOURCE_EVENT"),
])
def test_quality_rejection_reason_codes(mutator,code):
    inspect,raw=signed_inspection()
    mutator(inspect)
    report=quality_gate(inspect,raw,"academy_demo")
    assert report["quality_state"]=="QUARANTINE"
    assert code in report["reason_codes"]
    assert not report["rejected_raw_data_retained"]
    with pytest.raises(SyntheticGrowthError):
        require_disposable_source(inspect,raw,"academy_demo")


def test_quality_tampered_bytes_rejected_without_storing_data():
    inspect,raw=signed_inspection()
    q=quality_gate(inspect,raw+b" ", "academy_demo")
    assert q["quality_state"]=="QUARANTINE"
    assert "SOURCE_HASH_MISMATCH" in q["reason_codes"]
    assert q["production_ready"] is False
    assert quality_gate({},raw,"academy_demo")["quality_state"]=="QUARANTINE"
