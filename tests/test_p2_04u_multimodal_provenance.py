"""P2-04u: signed cross-modal proof-chain tests; deliberately NO model inference.

Each source receipt in these tests is a synthetic claim generated in-memory.
Passing means signature/contract logic works, NOT that an actual model ran.
"""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import base64

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import pytest

from app.creative_multimodal_studio import StudioHold, canonical
from app import creative_multimodal_provenance as chain

def b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

def signed_fixture(monkeypatch):
    monkeypatch.setattr(chain, "validate_manifest",
                        lambda _manifest,_root: {"runtime": 32.0})
    manifest={
        "project_id":"creative_project_01",
        "scenes":[
            {"kind":"image","file":"still.png","sha256":"a"*64},
            {"kind":"video","file":"shot.mp4","sha256":"b"*64},
        ],
        "voice":{"file":"speech.wav","sha256":"c"*64},
    }
    now=datetime.now(timezone.utc).replace(microsecond=0)
    keys={}
    evidence={"schema_version":1,"project_id":manifest["project_id"],"sources":{}}
    for kind,name,media_sha,model_sha in [
        ("image","still.png","a"*64,"d"*64),
        ("video","shot.mp4","b"*64,"e"*64),
        ("speech","speech.wav","c"*64,"f"*64),
    ]:
        reviewer_id="reviewer_"+kind
        private=Ed25519PrivateKey.generate()
        keys[reviewer_id]=b64(private.public_key().public_bytes(
            Encoding.Raw,PublicFormat.Raw))
        if kind!="speech":
            receipt={
                "generation_mode":"LOCAL_DIFFUSERS_REAL_INFERENCE",
                "output_state":"QUARANTINED_PENDING_INDEPENDENT_SAFETY_REVIEW",
                "output_kind":kind,
                "job_sha256":"1"*64,"model_tree_sha256":model_sha,
                "authorization_sha256":"2"*64,
                "output_sha256":media_sha,"output_bytes":999,
                "real_ai_output_verified":True,
                "published":False,"customer_distribution_authorized":False,
            }
        else:
            receipt={
                "generation_mode":"OPERATOR_ATTESTED_LOCAL_MODEL",
                "state":"QUARANTINED_PENDING_INDEPENDENT_REVIEW",
                "job_sha256":"1"*64,
                "model_checkpoint_sha256":model_sha,
                "output_sha256":media_sha,
                "published":False,"distribution_authorized":False,
            }
        review={
            "asset_file":name,"asset_kind":kind,
            "output_sha256":media_sha,
            "source_receipt_sha256":sha256(canonical(receipt)).hexdigest(),
            "source_job_sha256":"1"*64,
            "model_sha256":model_sha,
            "authorization_sha256":"2"*64,
            "observed_execution_record_sha256":"3"*64,
            "producer_id":"producer_original",
            "reviewer_id":reviewer_id,
            "operator_execution_witnessed":True,
            "quality_human_checked":True,
            "licence_human_checked":True,
            "rights_human_checked":True,
            "consent_human_checked":True,
            "issued_at":now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "expires_at":(now+timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        review["signature"]=b64(private.sign(canonical(review)))
        evidence["sources"][name]={"receipt":receipt,"review":review}
    return manifest,evidence,keys,now

def check(manifest,evidence,keys,now):
    from pathlib import Path
    return chain.verify_source_bundle(
        manifest,Path("/private/test-images-videos-speech"),
        evidence,reviewer_keys=keys,now=now)

def test_all_three_media_types_require_independent_signed_claims(monkeypatch):
    manifest,proofs,keys,now=signed_fixture(monkeypatch)
    result=check(manifest,proofs,keys,now)
    assert set(result["registered_review_claims_sha256"]) == {
        "still.png","shot.mp4","speech.wav"}
    assert result["status"]=="SOURCE_HASHES_AND_SIGNED_HUMAN_CLAIMS_VALIDATED"
    assert result["inference_independently_verified_by_code"] is False
    assert result["final_review_signed"] is False
    assert result["distribution_authorized"] is False

def test_unreviewed_speech_source_is_not_silently_omitted(monkeypatch):
    manifest,proofs,keys,now=signed_fixture(monkeypatch)
    del proofs["sources"]["speech.wav"]
    with pytest.raises(StudioHold,match="Every visual and voice"):
        check(manifest,proofs,keys,now)

def test_fake_runner_speech_mode_rejected(monkeypatch):
    manifest,proofs,keys,now=signed_fixture(monkeypatch)
    proofs["sources"]["speech.wav"]["receipt"]["generation_mode"]="TEST_ONLY_FAKE_RUNNER_NOT_AI"
    with pytest.raises(StudioHold):
        check(manifest,proofs,keys,now)

def test_tampered_model_receipt_rejected(monkeypatch):
    manifest,proofs,keys,now=signed_fixture(monkeypatch)
    proofs["sources"]["shot.mp4"]["receipt"]["model_tree_sha256"]="0"*64
    with pytest.raises(StudioHold,match="binding"):
        check(manifest,proofs,keys,now)

def test_different_media_sha_rejected(monkeypatch):
    manifest,proofs,keys,now=signed_fixture(monkeypatch)
    proofs["sources"]["still.png"]["receipt"]["output_sha256"]="0"*64
    with pytest.raises(StudioHold):
        check(manifest,proofs,keys,now)

def test_review_claim_tampering_breaks_signature(monkeypatch):
    manifest,proofs,keys,now=signed_fixture(monkeypatch)
    proofs["sources"]["still.png"]["review"]["observed_execution_record_sha256"]="0"*64
    with pytest.raises(StudioHold,match="signature"):
        check(manifest,proofs,keys,now)

def test_unregistered_reviewer_rejected(monkeypatch):
    manifest,proofs,keys,now=signed_fixture(monkeypatch)
    del keys["reviewer_video"]
    with pytest.raises(StudioHold,match="registered reviewer"):
        check(manifest,proofs,keys,now)

def test_expired_review_rejected(monkeypatch):
    manifest,proofs,keys,now=signed_fixture(monkeypatch)
    with pytest.raises(StudioHold,match="Expired"):
        check(manifest,proofs,keys,now+timedelta(days=2))

def test_missing_video_prevents_full_ai_proof(monkeypatch):
    manifest,proofs,keys,now=signed_fixture(monkeypatch)
    manifest["scenes"]=[manifest["scenes"][0]]
    proofs["sources"].pop("shot.mp4")
    with pytest.raises(StudioHold,match="image, short video and speech"):
        check(manifest,proofs,keys,now)

def test_render_not_called_until_all_source_claims_verify(monkeypatch):
    manifest,proofs,keys,now=signed_fixture(monkeypatch)
    calls=[]
    def fake_render(manifest,source_root,quarantine_root):
        calls.append("render")
        return {"manifest_sha256":sha256(canonical(manifest)).hexdigest(),
                "final_sha256":"9"*64,
                "status":"QUARANTINED_PENDING_INDEPENDENT_FINAL_REVIEW",
                "final_human_approval":False,"published":False}
    monkeypatch.setattr(chain,"render",fake_render)
    from pathlib import Path
    result=chain.render_with_source_proofs(manifest,Path("/private/input"),
            Path("/private/output"),proofs,reviewer_keys=keys)
    assert calls==["render"]
    assert result["neural_voice_inference_independently_proven"] is False
    assert result["publication_authorized"] is False
    calls.clear()
    proofs["sources"]["still.png"]["review"]["rights_human_checked"]=False
    with pytest.raises(StudioHold):
        chain.render_with_source_proofs(manifest,Path("/private/input"),
            Path("/private/output"),proofs,reviewer_keys=keys)
    assert not calls
