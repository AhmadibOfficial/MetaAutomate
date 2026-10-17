"""P2-04q cryptographic approval checks: fixture keys never authorize production."""
from datetime import datetime, timedelta, timezone
import base64
from hashlib import sha256

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import pytest

from app.creative_audio_assets import AudioAssetHold, canonical, validate_job
from app.creative_speech_authorization import verify_speech_approval

def b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def make_approval():
    job = {
        "schema_version":1, "project_id":"voice_project",
        "asset_id":"voice_sample", "kind":"speech", "use_case":"film",
        "prompt":"Original narrator for educational documentary.",
        "style_direction":"Warm natural English narration",
        "target_seconds":5, "language":"en",
        "model_checkpoint_sha256":"a"*64,
        "model_license_evidence_sha256":"b"*64,
        "content_rights_evidence_sha256":"c"*64,
        "authorization_sha256":"d"*64,
        "voice_likeness":"none","voice_consent_evidence_sha256":None,
        "artist_reference":"none","artist_rights_evidence_sha256":None,
        "distribution_authorized":False,
    }
    keys=[Ed25519PrivateKey.generate(),Ed25519PrivateKey.generate()]
    pub=[b64(k.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)) for k in keys]
    now=datetime.now(timezone.utc).replace(microsecond=0)
    approval={
        "schema_version":1,"job_sha256":validate_job(job)["job_sha256"],
        "model_checkpoint_sha256":job["model_checkpoint_sha256"],
        "model_config_sha256":"e"*64, "engine_sha256":"f"*64,
        "text_sha256":"1"*64, "license_evidence_sha256":"b"*64,
        "rights_evidence_sha256":"c"*64, "consent_evidence_sha256":None,
        "issued_at":now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at":(now+timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "licence_human_reviewed":True, "rights_human_reviewed":True,
        "consent_human_reviewed":True, "isolated_execution_required":True,
        "publication_authorized":False,
    }
    payload=canonical(approval)
    approval["signatures"]=[
        {"role":"OWNER","signature":b64(keys[0].sign(payload))},
        {"role":"REVIEWER","signature":b64(keys[1].sign(payload))},
    ]
    return job,approval,pub,now

def verify(job,approval,pub,now):
    return verify_speech_approval(job,approval,config_sha256="e"*64,
          engine_sha256="f"*64,text_sha256="1"*64,
          owner_public_key=pub[0],reviewer_public_key=pub[1],now=now)

def test_two_distinct_signatures_bound_to_exact_job():
    job,approval,pub,now=make_approval()
    assert len(verify(job,approval,pub,now))==64

@pytest.mark.parametrize("field,value",[
    ("model_config_sha256","0"*64),
    ("model_checkpoint_sha256","0"*64),
    ("text_sha256","0"*64),
    ("engine_sha256","0"*64),
    ("license_evidence_sha256","0"*64),
    ("publication_authorized",True),
    ("consent_human_reviewed",False),
])
def test_approval_mismatch_blocked(field,value):
    job,approval,pub,now=make_approval()
    approval[field]=value
    with pytest.raises(AudioAssetHold,match="Approval does not match"):
        verify(job,approval,pub,now)

def test_mutating_prompt_invalidates_signed_approval():
    job,approval,pub,now=make_approval()
    job["prompt"]="Altered documentary narration without authorization."
    with pytest.raises(AudioAssetHold,match="Approval does not match"):
        verify(job,approval,pub,now)

def test_incorrect_signature_rejected():
    job,approval,pub,now=make_approval()
    approval["signatures"][1]["signature"]=approval["signatures"][0]["signature"]
    with pytest.raises(AudioAssetHold,match="Invalid independently signed"):
        verify(job,approval,pub,now)

def test_same_key_not_independent():
    job,approval,pub,now=make_approval()
    with pytest.raises(AudioAssetHold,match="must differ"):
        verify(job,approval,[pub[0],pub[0]],now)

def test_approval_expiry_blocks_execution():
    job,approval,pub,now=make_approval()
    with pytest.raises(AudioAssetHold,match="short-lived"):
        verify(job,approval,pub,now+timedelta(hours=1))

def test_approval_reviewer_role_missing():
    job,approval,pub,now=make_approval()
    approval["signatures"][1]["role"]="OWNER"
    with pytest.raises(AudioAssetHold,match="ordered"):
        verify(job,approval,pub,now)

def test_extra_signature_or_field_blocks_execution():
    job,approval,pub,now=make_approval()
    approval["unexpected"]="yes"
    with pytest.raises(AudioAssetHold,match="Complete signed"):
        verify(job,approval,pub,now)
