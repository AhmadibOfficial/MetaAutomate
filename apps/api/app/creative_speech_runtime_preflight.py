"""P2-04q: verify local host/checkout/files/signatures before real speech execution.

Linux-only, fail closed. Does not prove legal rights, authenticate a person's
identity, establish independently observed model execution, or publish media.
"""
from __future__ import annotations
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

from app.creative_audio_assets import AudioAssetHold, sha_file, validate_job
from app.creative_speech_authorization import verify_speech_approval

COMMIT=re.compile(r"^[0-9a-f]{40}$")
NETNS=re.compile(r"^net:\[[0-9]+\]$")
def _private_file(path:Path, maximum:int)->None:
    if (not path.is_absolute() or path.is_symlink() or not path.is_file()
        or path.resolve()!=path or not 0<path.stat().st_size<=maximum
        or stat.S_IMODE(path.stat().st_mode)&0o077):
        raise AudioAssetHold("Private absolute regular file required")

def kernel_network_evidence(*, interface_root:Path=Path("/sys/class/net"),
                            route_path:Path=Path("/proc/net/route"),
                            namespace_path:Path=Path("/proc/self/ns/net"),
                            uid:int|None=None)->dict:
    """Only loopback interface and no IPv4 default route are permitted.

    This is a local kernel observation, not independently signed isolation
    evidence. Operator must also enforce a denied-egress network namespace.
    """
    if sys.platform!="linux" or (os.geteuid() if uid is None else uid)==0:
        raise AudioAssetHold("Linux non-root offline runtime required")
    try:
        names={p.name for p in interface_root.iterdir()}
        routes=route_path.read_text().splitlines()
        ns=os.readlink(namespace_path)
    except OSError as exc:
        raise AudioAssetHold("Linux network namespace inspection unavailable") from exc
    if names!={"lo"} or not NETNS.fullmatch(ns):
        raise AudioAssetHold("Non-loopback network interface or invalid namespace")
    if not routes or not routes[0].startswith("Iface"):
        raise AudioAssetHold("Linux route table cannot be inspected")
    if any((len(fields:=line.split())<2 or fields[1]=="00000000")
           for line in routes[1:] if line.strip()):
        raise AudioAssetHold("Default route or ambiguous route entry present")
    return {
        "network_namespace":ns,
        "interfaces":["lo"],
        "ipv4_default_route":False,
        "kernel_checks_passed":True,
        "isolation_independently_attested":False,
    }

def _git(repo_root:Path,*args:str)->str:
    try:
        x=subprocess.run(["git","-C",str(repo_root),*args],
                         check=True,text=True,capture_output=True,timeout=15)
    except (OSError,subprocess.SubprocessError) as exc:
        raise AudioAssetHold("Pinned private Git checkout cannot be inspected") from exc
    return x.stdout.strip()

def verify_operator_preflight(*,repo_root:Path,expected_commit:str,
    job:dict,authorization:dict,voice_model:Path,voice_config:Path,
    engine:Path,script:Path,license_evidence:Path,rights_evidence:Path,
    consent_evidence:Path|None,owner_public_key:str,
    reviewer_public_key:str,second_reviewer_public_key:str)->dict:
    """Read-only validation. Call before launching the pinned speech engine."""
    if (not COMMIT.fullmatch(expected_commit) or not repo_root.is_absolute()
        or repo_root.is_symlink() or not repo_root.is_dir()):
        raise AudioAssetHold("Exact Git commit and local source checkout required")
    observed=_git(repo_root,"rev-parse","HEAD")
    if observed!=expected_commit:
        raise AudioAssetHold("Git checkout differs from approved commit")
    if _git(repo_root,"status","--porcelain","--untracked-files=no"):
        raise AudioAssetHold("Git checkout contains unreviewed tracked modifications")
    plan=validate_job(job)
    if job["kind"]!="speech":
        raise AudioAssetHold("Only signed offline speech execution supported")
    for path,limit in ((voice_model,2_000_000_000),
                       (voice_config,128_000),
                       (engine,100_000_000),
                       (script,8192),
                       (license_evidence,128_000),
                       (rights_evidence,128_000)):
        _private_file(path,limit)
    if (voice_model.suffix!=".onnx"
        or voice_config.name!=voice_model.name+".json"
        or engine.name not in ("piper","piper.exe")
        or not stat.S_IMODE(engine.stat().st_mode)&stat.S_IXUSR):
        raise AudioAssetHold("Pinned executable/voice/config format unsupported")
    if (sha_file(voice_model)!=job["model_checkpoint_sha256"]
        or sha_file(license_evidence)!=job["model_license_evidence_sha256"]
        or sha_file(rights_evidence)!=job["content_rights_evidence_sha256"]):
        raise AudioAssetHold("Voice model or legal evidence digest mismatch")
    if job["voice_consent_evidence_sha256"] is not None:
        if consent_evidence is None:
            raise AudioAssetHold("Signed voice consent evidence file required")
        _private_file(consent_evidence,128_000)
        if sha_file(consent_evidence)!=job["voice_consent_evidence_sha256"]:
            raise AudioAssetHold("Voice consent digest mismatch")
    elif consent_evidence is not None:
        raise AudioAssetHold("Unexpected consent evidence for non-likeness job")
    try:
        source=script.read_text(encoding="utf-8")
        config=json.loads(voice_config.read_text(encoding="utf-8"))
    except (UnicodeError,ValueError) as exc:
        raise AudioAssetHold("Invalid voice config or text encoding") from exc
    if source.strip()!=job["prompt"] or not isinstance(config,dict):
        raise AudioAssetHold("Voice config/script does not match approved job")
    approval_sha=verify_speech_approval(
        job,authorization,config_sha256=sha_file(voice_config),
        engine_sha256=sha_file(engine),text_sha256=sha_file(script),
        owner_public_key=owner_public_key,reviewer_public_key=reviewer_public_key,
        second_reviewer_public_key=second_reviewer_public_key)
    net=kernel_network_evidence()
    if (type(net) is not dict or net.get("kernel_checks_passed") is not True
        or net.get("interfaces")!=["lo"] or net.get("ipv4_default_route") is not False
        or not isinstance(net.get("network_namespace"),str)
        or not NETNS.fullmatch(net["network_namespace"])):
        raise AudioAssetHold("Offline network namespace evidence missing")
    return {
        "status":"RUNTIME_PREFLIGHT_CLAIMS_VERIFIED_NO_INFERENCE",
        "source_commit_sha":observed,
        "job_sha256":plan["job_sha256"],
        "model_sha256":sha_file(voice_model),
        "config_sha256":sha_file(voice_config),
        "engine_sha256":sha_file(engine),
        "script_sha256":sha_file(script),
        "license_evidence_sha256":sha_file(license_evidence),
        "rights_evidence_sha256":sha_file(rights_evidence),
        "consent_evidence_sha256":(
            sha_file(consent_evidence) if consent_evidence is not None else None),
        "signed_approval_sha256":approval_sha,
        "local_network_evidence":net,
        "model_license_legality_independently_verified":False,
        "reviewer_real_world_identity_verified":False,
        "model_inference_observed":False,
        "release_authorized":False,
    }
