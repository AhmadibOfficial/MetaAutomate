"""P2-04q strictly local runtime readiness; test approvals use fixture keys.

Synthetic assets are never proof of licensed voice or actual neural inference.
"""
import base64
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import os
from pathlib import Path
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import pytest

from app.creative_audio_assets import AudioAssetHold, canonical, sha_file, validate_job
from app import creative_speech_runtime_preflight as gate


def b64(x):
    return base64.urlsafe_b64encode(x).rstrip(b"=").decode()


def fixture(tmp_path, monkeypatch):
    repo=tmp_path/"repo"
    repo.mkdir()
    root=tmp_path/"private"
    root.mkdir(mode=0o700)
    data={
        "voice.onnx":b"synthetic non-model",
        "voice.onnx.json":b'{"audio":{"sample_rate":22050}}',
        "piper":b"synthetic non-executable binary",
        "text.txt":b"Original synthetic narration for validation only.",
        "licence.txt":b"fixture licence only",
        "rights.txt":b"fixture rights only",
    }
    paths={}
    for name,content in data.items():
        path=root/name
        path.write_bytes(content)
        path.chmod(0o700 if name=="piper" else 0o600)
        paths[name]=path
    job={
        "schema_version":1,"project_id":"offline_speech",
        "asset_id":"sample_voice","kind":"speech",
        "use_case":"film",
        "prompt":data["text.txt"].decode(),
        "style_direction":"Natural educational narration",
        "target_seconds":5,"language":"en",
        "model_checkpoint_sha256":sha_file(paths["voice.onnx"]),
        "model_license_evidence_sha256":sha_file(paths["licence.txt"]),
        "content_rights_evidence_sha256":sha_file(paths["rights.txt"]),
        "authorization_sha256":"a"*64,
        "voice_likeness":"none","voice_consent_evidence_sha256":None,
        "artist_reference":"none","artist_rights_evidence_sha256":None,
        "distribution_authorized":False,
    }
    now=datetime.now(timezone.utc).replace(microsecond=0)
    approvals={
        "schema_version":1,"job_sha256":validate_job(job)["job_sha256"],
        "model_checkpoint_sha256":job["model_checkpoint_sha256"],
        "model_config_sha256":sha_file(paths["voice.onnx.json"]),
        "engine_sha256":sha_file(paths["piper"]),
        "text_sha256":sha_file(paths["text.txt"]),
        "license_evidence_sha256":sha_file(paths["licence.txt"]),
        "rights_evidence_sha256":sha_file(paths["rights.txt"]),
        "consent_evidence_sha256":None,
        "issued_at":now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_at":(now+timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "licence_human_reviewed":True,"rights_human_reviewed":True,
        "consent_human_reviewed":True,"isolated_execution_required":True,
        "publication_authorized":False,
    }
    owner=Ed25519PrivateKey.generate()
    reviewer=Ed25519PrivateKey.generate()
    reviewer_two=Ed25519PrivateKey.generate()
    payload=canonical(approvals)
    approvals["signatures"]=[
        {"role":"OWNER","signature":b64(owner.sign(payload))},
        {"role":"REVIEWER_1","signature":b64(reviewer.sign(payload))},
        {"role":"REVIEWER_2","signature":b64(reviewer_two.sign(payload))},
    ]
    def public(k):
        return b64(k.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw))
    monkeypatch.setattr(gate,"_git",
        lambda root,*args: "c"*40 if args==("rev-parse","HEAD") else "")
    monkeypatch.setattr(gate,"kernel_network_evidence",
        lambda:{"network_namespace":"net:[42]","interfaces":["lo"],
                "ipv4_default_route":False,"kernel_checks_passed":True,
                "isolation_independently_attested":False})
    args={
        "repo_root":repo,"expected_commit":"c"*40,"job":job,
        "authorization":approvals,"voice_model":paths["voice.onnx"],
        "voice_config":paths["voice.onnx.json"],
        "engine":paths["piper"],"script":paths["text.txt"],
        "license_evidence":paths["licence.txt"],
        "rights_evidence":paths["rights.txt"],
        "consent_evidence":None,
        "owner_public_key":public(owner),"reviewer_public_key":public(reviewer),
        "second_reviewer_public_key":public(reviewer_two),
    }
    return args

def test_signed_preflight_fails_to_claim_real_model(tmp_path,monkeypatch):
    args=fixture(tmp_path,monkeypatch)
    result=gate.verify_operator_preflight(**args)
    assert result["status"]=="RUNTIME_PREFLIGHT_CLAIMS_VERIFIED_NO_INFERENCE"
    assert result["model_inference_observed"] is False
    assert result["model_license_legality_independently_verified"] is False
    assert result["release_authorized"] is False

def test_file_tampering_fails(tmp_path,monkeypatch):
    args=fixture(tmp_path,monkeypatch)
    args["rights_evidence"].write_bytes(b"modified")
    with pytest.raises(AudioAssetHold,match="digest mismatch"):
        gate.verify_operator_preflight(**args)

def test_untrusted_git_commit_fails(tmp_path,monkeypatch):
    args=fixture(tmp_path,monkeypatch)
    args["expected_commit"]="0"*40
    with pytest.raises(AudioAssetHold,match="differs"):
        gate.verify_operator_preflight(**args)

def test_forged_review_claim_rejected(tmp_path,monkeypatch):
    args=fixture(tmp_path,monkeypatch)
    args["authorization"]["rights_human_reviewed"]=False
    with pytest.raises(AudioAssetHold,match="Approval does not match"):
        gate.verify_operator_preflight(**args)

def test_online_network_namespace_blocks(tmp_path,monkeypatch):
    args=fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(gate,"kernel_network_evidence",
        lambda:{"network_namespace":"net:[42]","interfaces":["lo","eth0"],
                "ipv4_default_route":True,"kernel_checks_passed":True})
    with pytest.raises(AudioAssetHold,match="network"):
        gate.verify_operator_preflight(**args)

def test_network_kernel_only_loopback(tmp_path):
    if sys.platform!="linux":
        pytest.skip("Linux only")
    iface=tmp_path/"interfaces"
    iface.mkdir()
    (iface/"lo").mkdir()
    route=tmp_path/"route"
    route.write_text("Iface Destination Gateway Flags RefCnt Use Metric Mask\n")
    ns=tmp_path/"ns"
    ns.symlink_to("net:[42]")
    report=gate.kernel_network_evidence(
        interface_root=iface,route_path=route,namespace_path=ns,uid=1000)
    assert report["interfaces"]==["lo"]
    assert report["isolation_independently_attested"] is False

def test_network_kernel_rejects_online_interface(tmp_path):
    if sys.platform!="linux":
        pytest.skip("Linux only")
    iface=tmp_path/"interfaces"
    iface.mkdir()
    (iface/"lo").mkdir()
    (iface/"eth0").mkdir()
    route=tmp_path/"route"
    route.write_text("Iface Destination Gateway Flags RefCnt Use Metric Mask\n")
    ns=tmp_path/"ns"
    ns.symlink_to("net:[42]")
    with pytest.raises(AudioAssetHold,match="Non-loopback"):
        gate.kernel_network_evidence(
            interface_root=iface,route_path=route,namespace_path=ns,uid=1000)

def test_network_kernel_rejects_root(tmp_path):
    if sys.platform!="linux":
        pytest.skip("Linux only")
    with pytest.raises(AudioAssetHold,match="non-root"):
        gate.kernel_network_evidence(uid=0)


def test_owner_and_two_reviewers_required(tmp_path,monkeypatch):
    args=fixture(tmp_path,monkeypatch)
    args["authorization"]["signatures"].pop()
    with pytest.raises(AudioAssetHold,match="Required owner/reviewer signatures"):
        gate.verify_operator_preflight(**args)

def test_duplicate_second_reviewer_key_rejected(tmp_path,monkeypatch):
    args=fixture(tmp_path,monkeypatch)
    args["second_reviewer_public_key"]=args["reviewer_public_key"]
    with pytest.raises(AudioAssetHold,match="keys must differ"):
        gate.verify_operator_preflight(**args)
