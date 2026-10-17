"""Three independently registered Ed25519 signatories, synthetic fixtures only."""
import base64
from datetime import datetime,timedelta,timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,PrivateFormat,PublicFormat,NoEncryption,
)
import pytest
from app.creative_audio_assets import AudioAssetHold
from app.creative_speech_approval_signing import ROLES,sign_next

def b64(x):
    return base64.urlsafe_b64encode(x).rstrip(b"=").decode()

def sample(tmp_path):
    keys=[Ed25519PrivateKey.generate() for _ in range(3)]
    trusted={role:b64(key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw))
             for role,key in zip(ROLES,keys)}
    paths=[]
    for i,key in enumerate(keys):
        p=tmp_path/f"human-{i}.pem"
        p.write_bytes(key.private_bytes(Encoding.PEM,PrivateFormat.PKCS8,
                                       NoEncryption()))
        p.chmod(0o600)
        paths.append(p)
    now=datetime.now(timezone.utc).replace(microsecond=0)
    packet={
        "schema_version":1,
        "job_sha256":"0"*64,"model_checkpoint_sha256":"1"*64,
        "model_config_sha256":"2"*64,"engine_sha256":"3"*64,
        "text_sha256":"4"*64,"license_evidence_sha256":"5"*64,
        "rights_evidence_sha256":"6"*64,"consent_evidence_sha256":None,
        "issued_at":now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at":(now+timedelta(minutes=20)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "licence_human_reviewed":True,"rights_human_reviewed":True,
        "consent_human_reviewed":True,"isolated_execution_required":True,
        "publication_authorized":False,"signatures":[],
    }
    return packet,trusted,paths,now

def test_three_parties_must_sign_in_order(tmp_path):
    packet,trust,paths,now=sample(tmp_path)
    for i,role in enumerate(ROLES):
        packet=sign_next(packet,role=role,key_path=paths[i],
                         trusted_public_keys=trust,now=now)
        assert len(packet["signatures"])==i+1
    with pytest.raises(AudioAssetHold,match="sequence"):
        sign_next(packet,role="OWNER",key_path=paths[0],
                  trusted_public_keys=trust,now=now)

def test_two_reviewer_packet_cannot_skip_second(tmp_path):
    packet,trust,paths,now=sample(tmp_path)
    with pytest.raises(AudioAssetHold,match="sequence"):
        sign_next(packet,role="REVIEWER_2",key_path=paths[2],
                  trusted_public_keys=trust,now=now)

def test_duplicate_reviewer_key_is_rejected(tmp_path):
    packet,trust,paths,now=sample(tmp_path)
    trust["REVIEWER_2"]=trust["REVIEWER_1"]
    with pytest.raises(AudioAssetHold,match="Duplicate"):
        sign_next(packet,role="OWNER",key_path=paths[0],
                  trusted_public_keys=trust,now=now)

def test_unreviewed_flags_are_not_self_approved(tmp_path):
    packet,trust,paths,now=sample(tmp_path)
    packet["rights_human_reviewed"]=False
    with pytest.raises(AudioAssetHold,match="human checks"):
        sign_next(packet,role="OWNER",key_path=paths[0],
                  trusted_public_keys=trust,now=now)

def test_private_key_permission_is_enforced(tmp_path):
    packet,trust,paths,now=sample(tmp_path)
    paths[0].chmod(0o644)
    with pytest.raises(AudioAssetHold,match="Private reviewer"):
        sign_next(packet,role="OWNER",key_path=paths[0],
                  trusted_public_keys=trust,now=now)

def test_tamper_after_owner_signature_fails(tmp_path):
    packet,trust,paths,now=sample(tmp_path)
    packet=sign_next(packet,role="OWNER",key_path=paths[0],
                     trusted_public_keys=trust,now=now)
    packet["text_sha256"]="f"*64
    with pytest.raises(AudioAssetHold,match="Earlier reviewer"):
        sign_next(packet,role="REVIEWER_1",key_path=paths[1],
                  trusted_public_keys=trust,now=now)

def test_signature_expiry_must_hold(tmp_path):
    packet,trust,paths,now=sample(tmp_path)
    with pytest.raises(AudioAssetHold,match="Short-lived"):
        sign_next(packet,role="OWNER",key_path=paths[0],
                  trusted_public_keys=trust,now=now+timedelta(hours=1))
