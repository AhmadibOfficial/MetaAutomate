"""Source-level tests for an optional REAL offline generation worker.

Uses ONLY fixture files and fake bytes. No model weights, provider inference,
GPU or generated creative outputs are produced by these tests. CI must never
claim source tests are real AI media generation evidence.
"""
from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from pathlib import Path
import json
import os
import sys

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import ValidationError

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"apps/api"))
from app.creative_local_generation import (
    Approval,GenerationBlocked,Job,canonical,check_model_tree,
    check_approval,digest,execute,read_json,run_local_diffusers,
)

NOW=datetime(2026,10,17,0,0,0,tzinfo=timezone.utc)
SHA1="1"*64
SHA2="2"*64

def b64(data:bytes)->str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def job_data(kind="image",**overrides):
    base={
        "schema_version":1,
        "kind":kind,
        "project_key":"project_01",
        "prompt":"Illustrate trustworthy inventory records for small businesses",
        "requester_id":"operator-001",
        "reviewer_id":"reviewer-002",
        "rights_kind":"NO_EXTERNAL_REFERENCES",
        "rights_evidence_sha256":SHA1,
        "likeness_status":"NO_IDENTIFIABLE_PERSON",
        "consent_evidence_sha256":SHA2,
        "model_name":"image_model" if kind=="image" else "video_model",
        "seed":42,
        "steps":15,
        "width":512 if kind=="image" else 576,
        "height":512 if kind=="image" else 320,
        "frames":0 if kind=="image" else 24,
        "fps":0 if kind=="image" else 8,
        "idempotency_key":"unique-fixture-00001",
    }
    base.update(overrides)
    return base

@pytest.fixture
def env(tmp_path):
    models=tmp_path/"models"
    models.mkdir()
    for name,klass in (("image_model","StableDiffusionPipeline"),
                       ("video_model","TextToVideoSDPipeline")):
        path=models/name
        path.mkdir()
        (path/"model_index.json").write_text(
            json.dumps({"_class_name":klass}))
        (path/"test.safetensors").write_bytes(b"not real weights; never a model")
    quarantine=tmp_path/"quarantine"
    quarantine.mkdir(mode=0o700)
    return models,quarantine

def authorized(job,root,now=NOW):
    path,model_hash,model_class=check_model_tree(root,job.model_name)
    owner=Ed25519PrivateKey.generate()
    reviewer=Ed25519PrivateKey.generate()
    def pub(k):
        return b64(k.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw))
    payload={
        "schema_version":1,
        "job_sha256":digest(job.model_dump()),
        "model_tree_sha256":model_hash,
        "issued_at":"2026-10-16T23:59:00Z",
        "expires_at":"2026-10-17T00:20:00Z",
        "prompt_human_checked":True,
        "model_licence_human_checked":True,
        "rights_evidence_human_checked":True,
        "consent_evidence_human_checked":True,
        "output_must_be_quarantined":True,
        "publication_authorized":False,
    }
    data=canonical(payload)
    payload["signatures"]=[
        {"role":role,"signature":b64(signer.sign(data))}
        for role,signer in zip(("OWNER","INDEPENDENT_REVIEWER"),
                               (owner,reviewer))
    ]
    return Approval.model_validate(payload),pub(owner),pub(reviewer)

@pytest.mark.parametrize("override",[
    {"schema_version":2}, {"kind":"website"}, {"frames":10},
    {"fps":8}, {"width":900}, {"height":64}, {"steps":2},
    {"requester_id":"reviewer-002"}, {"prompt":"bad"},
    {"rights_kind":"UNVERIFIED"}, {"rights_evidence_sha256":"not-a-hash"},
    {"likeness_status":"UNKNOWN"},
    {"consent_evidence_sha256":"bad"}, {"seed":-1},
    {"idempotency_key":"short"}, {"customer_phone":"+2348112345678"},
])
def test_image_request_rejects_unauthorized_or_unbounded_fields(override):
    with pytest.raises(ValidationError):
        Job.model_validate(job_data(**override))

@pytest.mark.parametrize("override",[
    {"frames":0}, {"frames":65}, {"fps":12},
    {"width":512}, {"height":512}, {"steps":100},
])
def test_short_video_requires_bounded_real_model_frame_budget(override):
    with pytest.raises(ValidationError):
        Job.model_validate(job_data("video",**override))

def test_valid_image_and_short_video_have_exact_task_specific_limits():
    image=Job.model_validate(job_data())
    video=Job.model_validate(job_data("video"))
    assert image.frames==0 and image.fps==0
    assert video.frames==24 and video.fps==8
    assert video.width==576 and video.height==320
    assert video.frames/video.fps==3
    assert image.kind=="image"

def test_model_tree_only_local_safe_weights_and_allowlisted_pipeline(env,tmp_path):
    root,_=env
    image,sha,kind=check_model_tree(root,"image_model")
    assert image.name=="image_model"
    assert len(sha)==64
    assert kind=="StableDiffusionPipeline"
    assert check_model_tree(root,"image_model")[1]==sha
    with pytest.raises(GenerationBlocked):
        check_model_tree(root,"../../etc")
    (root/"image_model"/"code.py").write_text("print('remote model code')")
    with pytest.raises(GenerationBlocked):
        check_model_tree(root,"image_model")
    (root/"image_model"/"code.py").unlink()
    (root/"image_model"/"link.json").symlink_to(
        root/"video_model"/"model_index.json")
    with pytest.raises(GenerationBlocked):
        check_model_tree(root,"image_model")

def test_pickle_model_weights_not_accepted(env):
    root,_=env
    (root/"video_model"/"pytorch_model.bin").write_bytes(b"unsafe pickle")
    with pytest.raises(GenerationBlocked):check_model_tree(root,"video_model")

def test_authorization_signatures_bind_job_and_preverified_model_hash(env):
    root,_=env
    job=Job.model_validate(job_data())
    auth,k1,k2=authorized(job,root)
    model_hash=check_model_tree(root,"image_model")[1]
    result=check_approval(job,auth,model_hash,k1,k2,now=NOW)
    assert len(result)==64
    with pytest.raises(GenerationBlocked):
        check_approval(Job.model_validate(job_data(prompt="A different"
           " ethically reviewed educational stock management poster")),auth,
                       model_hash,k1,k2,now=NOW)
    with pytest.raises(GenerationBlocked):
        check_approval(job,auth,"a"*64,k1,k2,now=NOW)

@pytest.mark.parametrize("edit",[
    lambda a:setattr(a,"model_licence_human_checked",False),
    lambda a:setattr(a,"prompt_human_checked",False),
    lambda a:setattr(a,"rights_evidence_human_checked",False),
    lambda a:setattr(a,"consent_evidence_human_checked",False),
    lambda a:setattr(a,"publication_authorized",True),
    lambda a:setattr(a,"output_must_be_quarantined",False),
    lambda a:setattr(a,"expires_at","2026-10-17T00:30:00Z"),
    lambda a:setattr(a,"issued_at","2026-10-16T23:20:00Z"),
    lambda a:setattr(a,"schema_version",2),
])
def test_authorization_rejects_missing_signoffs_mutation_and_stale(edit,env):
    root,_=env
    job=Job.model_validate(job_data())
    a,k1,k2=authorized(job,root)
    edit(a)
    with pytest.raises(GenerationBlocked):
        check_approval(job,a,check_model_tree(root,"image_model")[1],k1,k2,now=NOW)

def test_authorization_expiry_and_one_key_attempt_fails(env):
    root,_=env
    job=Job.model_validate(job_data())
    a,k1,k2=authorized(job,root)
    h=check_model_tree(root,"image_model")[1]
    with pytest.raises(GenerationBlocked):
        check_approval(job,a,h,k1,k2,now=NOW+timedelta(hours=2))
    with pytest.raises(GenerationBlocked):
        check_approval(job,a,h,k1,k1,now=NOW)
    a.signatures=a.signatures[:1]
    with pytest.raises(GenerationBlocked):
        check_approval(job,a,h,k1,k2,now=NOW)

def test_execution_disabled_without_both_env_conditions(env,monkeypatch):
    root,out=env
    job=Job.model_validate(job_data())
    approval,k1,k2=authorized(job,root)
    for flag in ("MAT_CREATIVE_OFFLINE_EXECUTION_ENABLED",
                 "MAT_CREATIVE_NETWORK_ISOLATED"):
        monkeypatch.delenv(flag,raising=False)
    with pytest.raises(GenerationBlocked):
        execute(job,approval,model_root=root,output_root=out,
                owner_key=k1,reviewer_key=k2)
    assert list(out.iterdir())==[]

def fake_image(job,model_dir,path):
    path.write_bytes(b"\x89PNG\r\n\x1a\n"+b"CI-ONLY NOT AN IMAGE MODEL "*3)

def fake_video(job,model_dir,path):
    path.write_bytes(b"\x00\x00\x00\x18ftyp"+b"CI-ONLY NOT AN AI VIDEO "*4)

@pytest.mark.parametrize("kind,runner",[
    ("image",fake_image),("video",fake_video)
])
def test_outputs_remain_quarantined_even_with_two_signed_reviewers(
    kind,runner,env,monkeypatch,
):
    root,out=env
    job=Job.model_validate(job_data(kind))
    approval,k1,k2=authorized(job,root)
    monkeypatch.setenv("MAT_CREATIVE_OFFLINE_EXECUTION_ENABLED","1")
    monkeypatch.setenv("MAT_CREATIVE_NETWORK_ISOLATED","1")
    result=execute(job,approval,model_root=root,output_root=out,
        owner_key=k1,reviewer_key=k2,runner=runner,now=NOW)
    assert result["published"] is False
    assert result["output_state"]=="QUARANTINED_PENDING_INDEPENDENT_SAFETY_REVIEW"
    assert result["rights_independently_authenticated_by_worker"] is False
    assert result["content_safety_independently_verified"] is False
    assert result["customer_distribution_authorized"] is False
    assert result["real_ai_output_verified"] is False
    assert result["generation_mode"]=="TEST_ONLY_FAKE_RUNNER_NOT_AI"
    folders=list(out.iterdir())
    assert len(folders)==1
    assert folders[0].stat().st_mode & 0o777 == 0o700
    record=json.loads((folders[0]/"receipt.json").read_text())
    assert record==result
    assert not any(p.name=="published" for p in out.rglob("*"))

def test_invalid_rendered_media_is_destroyed_before_receipt(env,monkeypatch):
    root,out=env
    job=Job.model_validate(job_data())
    a,k1,k2=authorized(job,root)
    monkeypatch.setenv("MAT_CREATIVE_OFFLINE_EXECUTION_ENABLED","1")
    monkeypatch.setenv("MAT_CREATIVE_NETWORK_ISOLATED","1")
    with pytest.raises(GenerationBlocked):
        execute(job,a,model_root=root,output_root=out,
                owner_key=k1,reviewer_key=k2,runner=lambda j,m,p:
                p.write_bytes(b"not a PNG despite claiming image"),now=NOW)
    assert list(out.iterdir())==[]

def test_read_json_duplicate_key_rejected(tmp_path):
    path=tmp_path/"job.json"
    path.write_text('{"job":1,"job":2}')
    with pytest.raises(GenerationBlocked):read_json(path)
    path.write_text('{"bad":NaN}')
    with pytest.raises(GenerationBlocked):read_json(path)
    path.unlink()
    path.symlink_to("/etc/hosts")
    with pytest.raises(GenerationBlocked):read_json(path)

def test_real_model_runner_is_separately_optional_and_not_invoked_in_ci(monkeypatch):
    assert callable(run_local_diffusers)
    module=(ROOT/"apps/api/app/creative_local_generation.py").read_text()
    for required in (
        "HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE","local_files_only=True",
        "use_safetensors=True","AutoPipelineForText2Image",
        "DiffusionPipeline","export_to_video",
        "MAT_CREATIVE_OFFLINE_EXECUTION_ENABLED",
        "MAT_CREATIVE_NETWORK_ISOLATED",
        "QUARANTINED_PENDING_INDEPENDENT_SAFETY_REVIEW",
    ):
        assert required in module
