"""P2-04c — REAL optional local Diffusers inference, disabled by default.

No model weights are included or downloaded. Operators must provide a
pre-verified local safetensors model and execute this worker INSIDE an
independently approved egress-disabled GPU container. This module cannot
enforce host/container network isolation or validate licences on its own.
Results always stay in a 0700 quarantine directory; there is NO publish API.

Image: approved local StableDiffusionPipeline/StableDiffusionXLPipeline.
Video: approved local TextToVideoSDPipeline, SHORT clips (16..64 frames).
The public 30..120-second video brief is a PLAN, not 30..120 seconds of AI film.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime,timezone,timedelta
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import sys
from uuid import uuid4

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import BaseModel,ConfigDict,Field,StrictBool,StrictInt,model_validator

SHA=re.compile(r"^[a-f0-9]{64}$")
IDENT=re.compile(r"^[a-z][a-z0-9_-]{7,63}$")
ALLOWED_EXT={".json",".safetensors",".txt",".model",".vocab",".merges"}
PIPELINES={
    "image":{"StableDiffusionPipeline","StableDiffusionXLPipeline"},
    "video":{"TextToVideoSDPipeline"},
}
KEYS=("OWNER","INDEPENDENT_REVIEWER")
SAFE_BYTES=16384

class GenerationBlocked(RuntimeError):
    """The correct outcome until authorization and real runtime exist."""


class Job(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True,str_strip_whitespace=True)
    schema_version:StrictInt=1
    kind:str=Field(pattern="^(image|video)$")
    project_key:str=Field(min_length=8,max_length=64,pattern=r"^[a-z][a-z0-9_-]{7,63}$")
    prompt:str=Field(min_length=15,max_length=700)
    requester_id:str=Field(min_length=8,max_length=80,pattern=r"^[A-Za-z0-9_:-]+$")
    reviewer_id:str=Field(min_length=8,max_length=80,pattern=r"^[A-Za-z0-9_:-]+$")
    rights_kind:str=Field(pattern=r"^(OWNED|LICENSED|WRITTEN_PERMISSION|NO_EXTERNAL_REFERENCES)$")
    rights_evidence_sha256:str=Field(pattern=r"^[a-f0-9]{64}$")
    likeness_status:str=Field(pattern=r"^(NO_IDENTIFIABLE_PERSON|VERIFIED_CONSENT)$")
    consent_evidence_sha256:str=Field(pattern=r"^[a-f0-9]{64}$")
    model_name:str=Field(min_length=8,max_length=80,pattern=r"^[a-z0-9_-]+$")
    seed:StrictInt=Field(ge=0,le=2147483647)
    steps:StrictInt=Field(ge=10,le=30)
    width:StrictInt=Field(ge=256,le=768)
    height:StrictInt=Field(ge=256,le=768)
    frames:StrictInt=Field(ge=0,le=64)
    fps:StrictInt=Field(ge=0,le=12)
    idempotency_key:str=Field(min_length=12,max_length=80,pattern=r"^[A-Za-z0-9_.:-]+$")

    @model_validator(mode="after")
    def bounded_media(self):
        if self.requester_id==self.reviewer_id:
            raise ValueError("Independent human reviewer must differ from requester")
        if any(not x.strip() for x in (self.prompt,self.project_key)):
            raise ValueError("Empty prompt or project")
        if self.kind=="image" and (self.frames,self.fps)!=(0,0):
            raise ValueError("Image job must not claim video frames")
        if self.kind=="video" and (
            not 16<=self.frames<=64 or self.fps!=8 or
            (self.width,self.height)!=(576,320)
        ):
            raise ValueError("Video restricted to 16-64 frames at 576x320 and 8 fps")
        if self.kind=="image" and (self.width*self.height>768*768):
            raise ValueError("Image output too large")
        return self


class Approval(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    schema_version:StrictInt=1
    job_sha256:str=Field(pattern=r"^[a-f0-9]{64}$")
    model_tree_sha256:str=Field(pattern=r"^[a-f0-9]{64}$")
    issued_at:str
    expires_at:str
    prompt_human_checked:StrictBool
    model_licence_human_checked:StrictBool
    rights_evidence_human_checked:StrictBool
    consent_evidence_human_checked:StrictBool
    output_must_be_quarantined:StrictBool
    publication_authorized:StrictBool
    signatures:list[dict]

def canonical(value)->bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),
                      ensure_ascii=True,allow_nan=False).encode("ascii")

def digest(value)->str:
    return sha256(canonical(value)).hexdigest()

def _b64(value,size):
    if not isinstance(value,str) or not re.fullmatch(r"[A-Za-z0-9_-]+",value):
        raise GenerationBlocked("Invalid signing key or signature encoding")
    try:
        raw=base64.urlsafe_b64decode(value+"="*((-len(value))%4))
    except (ValueError,base64.binascii.Error) as e:
        raise GenerationBlocked("Invalid signing key or signature encoding") from e
    if len(raw)!=size or base64.urlsafe_b64encode(raw).rstrip(b"=").decode()!=value:
        raise GenerationBlocked("Noncanonical signing key or signature")
    return raw

def read_json(path:Path)->dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size>SAFE_BYTES:
        raise GenerationBlocked("Bounded signed file must be regular and non-symlink")
    try:
        def reject_duplicate(pairs):
            out={}
            for k,v in pairs:
                if k in out:raise GenerationBlocked("Duplicate JSON key")
                out[k]=v
            return out
        def reject_number(_):raise GenerationBlocked("Noninteger number forbidden")
        doc=json.loads(path.read_bytes().decode("utf8"),
                       object_pairs_hook=reject_duplicate,
                       parse_float=reject_number,parse_constant=reject_number)
    except (UnicodeError,ValueError,RecursionError) as e:
        raise GenerationBlocked("Malformed job or authorization") from e
    if type(doc) is not dict:raise GenerationBlocked("Invalid JSON document")
    return doc

def _time(value:str)->datetime:
    if not isinstance(value,str) or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ",value):
        raise GenerationBlocked("Signed expiry must be UTC seconds")
    try:
        return datetime.strptime(value,"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as e:raise GenerationBlocked("Invalid time") from e

def check_approval(job:Job,auth:Approval,model_tree_sha:str,
                   owner_key:str,reviewer_key:str,now:datetime|None=None)->str:
    if (auth.schema_version!=1 or auth.job_sha256!=digest(job.model_dump()) or
        auth.model_tree_sha256!=model_tree_sha or
        not all((auth.prompt_human_checked,auth.model_licence_human_checked,
                 auth.rights_evidence_human_checked,auth.consent_evidence_human_checked,
                 auth.output_must_be_quarantined)) or
        auth.publication_authorized is not False):
        raise GenerationBlocked("Job is not independently authorized for quarantined media")
    issued,expires=_time(auth.issued_at),_time(auth.expires_at)
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise GenerationBlocked("Timezone-aware time required")
    if not (issued<=now.astimezone(timezone.utc)<expires and
            timedelta(minutes=1)<=expires-issued<=timedelta(minutes=30)):
        raise GenerationBlocked("Missing current time-bounded signed authorization")
    if len(auth.signatures)!=2 or any(
        type(v) is not dict or set(v)!={"role","signature"}
        for v in auth.signatures
    ) or [x["role"] for x in auth.signatures]!=list(KEYS):
        raise GenerationBlocked("Two ordered signatures required")
    k1,k2=_b64(owner_key,32),_b64(reviewer_key,32)
    if k1==k2:
        raise GenerationBlocked("Independent signer keys cannot be identical")
    data=canonical(auth.model_dump(exclude={"signatures"}))
    for key,item in zip((k1,k2),auth.signatures):
        try:
            Ed25519PublicKey.from_public_bytes(key).verify(
                _b64(item["signature"],64),data)
        except (InvalidSignature,ValueError) as e:
            raise GenerationBlocked("Invalid owner/reviewer approval signature") from e
    return sha256(data).hexdigest()

def check_model_tree(model_root:Path, model_name:str)->tuple[Path,str,str]:
    """Only operator-selected, regular files under a trusted offline root."""
    if not model_root.is_absolute() or model_root.is_symlink():
        raise GenerationBlocked("Model root must be absolute and not a symlink")
    root=model_root.resolve(strict=True)
    candidate=root/model_name
    if candidate.is_symlink() or not candidate.is_dir() or candidate.resolve()!=candidate:
        raise GenerationBlocked("Model path invalid, missing or symlinked")
    files=sorted(p for p in candidate.rglob("*"))
    if not files or len(files)>200:
        raise GenerationBlocked("Missing or excessive model files")
    record=[]
    for path in files:
        if path.is_symlink():
            raise GenerationBlocked("Symlinked model component forbidden")
        if path.is_dir():continue
        if not path.is_file() or path.suffix.lower() not in ALLOWED_EXT:
            raise GenerationBlocked("Disallowed executable or pickle model asset")
        if not path.resolve().is_relative_to(root):
            raise GenerationBlocked("Model asset escapes approved root")
        relative=path.relative_to(candidate).as_posix()
        if len(relative)>240 or path.stat().st_size>12_000_000_000:
            raise GenerationBlocked("Unbounded model asset")
        hasher=sha256()
        with path.open("rb") as stream:
            for block in iter(lambda:stream.read(1024*1024),b""):
                hasher.update(block)
        record.append((relative,hasher.hexdigest()))
    if not any(p.endswith(".safetensors") for p,_ in record):
        raise GenerationBlocked("Model must contain safetensors weights")
    config=candidate/"model_index.json"
    if not config.is_file() or config.is_symlink():
        raise GenerationBlocked("Missing local trusted model_index.json")
    model_doc=read_json(config)
    cls=model_doc.get("_class_name")
    if cls not in PIPELINES["image"]|PIPELINES["video"]:
        raise GenerationBlocked("Model pipeline not allowlisted")
    return candidate,digest(record),cls

def validate_job(job:Job,auth:Approval,*,model_root:Path,
                 owner_key:str,reviewer_key:str,now:datetime|None=None)->tuple[Path,str,str,str]:
    model_dir,model_hash,model_class=check_model_tree(model_root,job.model_name)
    if model_class not in PIPELINES[job.kind]:
        raise GenerationBlocked("Model task does not match requested medium")
    receipt=check_approval(job,auth,model_hash,owner_key,reviewer_key,now=now)
    return model_dir,model_hash,model_class,receipt

def execute(job:Job,auth:Approval,*,model_root:Path,output_root:Path,
            owner_key:str,reviewer_key:str,runner=None,now=None)->dict:
    """Real runner can invoke local inference; any output is QUARANTINED.

    An injection runner exists ONLY for tests and must never report real AI.
    """
    if (os.environ.get("MAT_CREATIVE_OFFLINE_EXECUTION_ENABLED")!="1" or
        os.environ.get("MAT_CREATIVE_NETWORK_ISOLATED")!="1"):
        raise GenerationBlocked("Generation disabled; independent networkless worker required")
    model_dir,model_hash,model_class,authorization=validate_job(
        job,auth,model_root=model_root,owner_key=owner_key,
        reviewer_key=reviewer_key,now=now,
    )
    if not output_root.is_absolute() or output_root.is_symlink():
        raise GenerationBlocked("Quarantine root must be an absolute trusted non-symlink path")
    root=output_root.resolve(strict=True)
    if root.is_symlink() or not root.is_dir():
        raise GenerationBlocked("Quarantine destination unavailable")
    # Caller must separately enforce physical network isolation, uid, no
    # host mounts, CPU/GPU quota, job-time limits, and filesystem limits.
    receipt=uuid4().hex
    folder=root/receipt
    folder.mkdir(mode=0o700)
    try:
        if stat.S_IMODE(folder.stat().st_mode)!=0o700:
            raise GenerationBlocked("Quarantine file permissions invalid")
        extension=".png" if job.kind=="image" else ".mp4"
        path=folder/("generated"+extension)
        if runner is None:
            run_local_diffusers(job,model_dir,model_class,path)
            mode="LOCAL_DIFFUSERS_REAL_INFERENCE"
        else:
            runner(job,model_dir,path)
            mode="TEST_ONLY_FAKE_RUNNER_NOT_AI"
        if path.is_symlink() or not path.is_file() or path.stat().st_size<32:
            raise GenerationBlocked("Model output is missing or nonregular")
        if path.stat().st_size>100_000_000:
            raise GenerationBlocked("Generated artifact exceeds quarantine cap")
        path.chmod(0o600)
        content=sha256(path.read_bytes()).hexdigest()
        report={
            "schema_version":1,"job_sha256":digest(job.model_dump()),
            "authorization_sha256":authorization,
            "model_tree_sha256":model_hash,
            "model_class":model_class,
            "output_sha256":content,
            "output_kind":job.kind,
            "output_bytes":path.stat().st_size,
            "generation_mode":mode,
            "output_state":"QUARANTINED_PENDING_INDEPENDENT_SAFETY_REVIEW",
            "published":False,"external_calls_made_by_this_wrapper":False,
            "rights_independently_authenticated_by_worker":False,
            "content_safety_independently_verified":False,
            "customer_distribution_authorized":False,
            "real_ai_output_verified":mode=="LOCAL_DIFFUSERS_REAL_INFERENCE",
        }
        (folder/"receipt.json").write_bytes(canonical(report)+b"\n")
        (folder/"receipt.json").chmod(0o600)
        return report
    except Exception:
        # Never leave a partial/untested artifact as publishable or approved.
        for sub in folder.iterdir():
            if sub.is_file() and not sub.is_symlink():sub.unlink()
        folder.rmdir()
        raise

def run_local_diffusers(job:Job,model_dir:Path,model_class:str,output:Path)->None:
    """GPU-only local inference. Optional dependencies must be preinstalled.

    No HTTP clients, provider API or model download functions are invoked.
    Enforce egress deny at *container* boundary, not just environment vars.
    """
    os.environ["HF_HUB_OFFLINE"]="1"
    os.environ["TRANSFORMERS_OFFLINE"]="1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"]="1"
    try:
        import torch
        from diffusers import AutoPipelineForText2Image,DiffusionPipeline
        from diffusers.utils import export_to_video
    except ImportError as exc:
        raise GenerationBlocked("Local diffusers/torch/video codecs not installed") from exc
    if not torch.cuda.is_available():
        raise GenerationBlocked("Approved GPU execution device unavailable")
    # safetensors only; no trust_remote_code and no remotely resolved model ID.
    cls=AutoPipelineForText2Image if job.kind=="image" else DiffusionPipeline
    pipe=cls.from_pretrained(str(model_dir),local_files_only=True,
                             use_safetensors=True,torch_dtype=torch.float16)
    pipe=pipe.to("cuda")
    generator=torch.Generator(device="cuda").manual_seed(job.seed)
    args=dict(prompt=job.prompt,generator=generator,
              num_inference_steps=job.steps,width=job.width,height=job.height)
    with torch.inference_mode():
        if job.kind=="image":
            images=pipe(**args).images
            if len(images)!=1:raise GenerationBlocked("Unexpected generated images")
            images[0].save(output,format="PNG")
        else:
            frames=pipe(**args,num_frames=job.frames).frames[0]
            if len(frames)!=job.frames:
                raise GenerationBlocked("Unexpected video frame count")
            export_to_video(frames,output_video_path=str(output),fps=job.fps)

def main(argv=None)->int:
    parser=argparse.ArgumentParser(description="Local quarantined Diffusers media worker")
    parser.add_argument("--job",type=Path,required=True)
    parser.add_argument("--authorization",type=Path,required=True)
    parser.add_argument("--model-root",type=Path,required=True)
    parser.add_argument("--quarantine-root",type=Path,required=True)
    opts=parser.parse_args(argv)
    try:
        job=Job.model_validate(read_json(opts.job))
        auth=Approval.model_validate(read_json(opts.authorization))
        record=execute(
            job,auth,model_root=opts.model_root,output_root=opts.quarantine_root,
            owner_key=os.environ.get("MAT_CREATIVE_OWNER_VERIFY_KEY",""),
            reviewer_key=os.environ.get("MAT_CREATIVE_REVIEWER_VERIFY_KEY",""),
        )
    except (GenerationBlocked,ValueError,OSError) as exc:
        print("Creative generation blocked: "+str(exc),file=sys.stderr)
        return 2
    print(json.dumps(record,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
