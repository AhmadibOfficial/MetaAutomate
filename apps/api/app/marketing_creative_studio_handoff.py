"""P2-04s: evidence-first marketing-to-voiceover handoff, never publication.

This module links marketing copy to quarantined audio and approved captions as a
source-only seam between PR #98 and the separately gated PR #97 speech worker.
No model execution, social posting, file transfer, or network calls.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import json
import re
import stat
import wave

from app.marketing_content_workbench import ContentHold, create_campaign, inspect_candidate

SHA=re.compile(r"^[0-9a-f]{64}$")
NAME=re.compile(r"^[A-Za-z0-9_-]{1,70}\.(wav|srt)$")
OUTPUT_TYPES={"social","ads","video","authority","blog","product","email"}

def digest(path:Path)->str:
    h=sha256()
    with path.open("rb") as source:
        for part in iter(lambda:source.read(1024*1024),b""):
            h.update(part)
    return h.hexdigest()

def file_private(root:Path,filename:str,max_bytes:int)->Path:
    if (not root.is_absolute() or root.is_symlink() or not root.is_dir()
        or root.resolve()!=root or stat.S_IMODE(root.stat().st_mode)&0o077):
        raise ContentHold("Private absolute production asset directory required")
    if type(filename) is not str or NAME.fullmatch(filename) is None:
        raise ContentHold("Unsupported source media filename")
    path=root/filename
    if (path.is_symlink() or not path.is_file() or path.resolve()!=path
        or not 44<path.stat().st_size<=max_bytes or
        stat.S_IMODE(path.stat().st_mode)&0o077):
        raise ContentHold("Private bounded local audio/caption file required")
    return path

def prepare_narrated_campaign(brief:dict, *, work_order_id:str,
                              script:str, evidence_checked:bool,
                              rights_checked:bool)->dict:
    """Produce a scripted production package with no real voice claimed."""
    bundle=create_campaign(brief)
    review=inspect_candidate(bundle,work_order_id,script,
                              evidence_checked=evidence_checked,
                              rights_checked=rights_checked)
    if review["review_status"]!="HUMAN_REVIEW_CLAIM_RECORDED_NOT_PUBLISHED":
        raise ContentHold("Source script remains under editorial review")
    task=next(item for item in bundle["work_orders"]
              if item["id"]==work_order_id)
    if task["content_kind"] not in OUTPUT_TYPES:
        raise ContentHold("Unsupported narration work order")
    if not 30<=len(script)<=8000:
        raise ContentHold("Narration script must be bounded")
    return {
        "schema_version":1,
        "project_id":brief["campaign_id"],
        "work_order_id":work_order_id,
        "content_kind":task["content_kind"],
        "channel":task["channel"],
        "brief_sha256":bundle["brief_sha256"],
        "script_sha256":sha256(script.encode("utf-8")).hexdigest(),
        "script_text":script,
        "editorial_review_claim_sha256":sha256(json.dumps(
            review,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
        "speech_model_output_sha256":None,
        "speech_independently_verified":False,
        "caption_sync_verified":False,
        "status":"SCRIPT_REVIEW_CLAIM_ONLY_PENDING_VOICE_INFERENCE",
        "external_messaging_authorized":False,
        "publication_authorized":False,
        "scheduling_authorized":False,
    }

def inspect_audio_attachment(package:dict, *, asset_root:Path,
                             audio_filename:str, audio_sha256:str,
                             claimed_speech_job_sha256:str,
                             claimed_signed_review_sha256:str)->dict:
    """Check source links and WAV properties, not real model or review provenance.

    A digest or a signed-claim hash is not a verification of a signature.
    """
    if type(package) is not dict or package.get("status")!="SCRIPT_REVIEW_CLAIM_ONLY_PENDING_VOICE_INFERENCE":
        raise ContentHold("Narration work package not eligible for attachment")
    if any(type(v) is not str or SHA.fullmatch(v) is None for v in (
        audio_sha256,claimed_speech_job_sha256,claimed_signed_review_sha256)):
        raise ContentHold("Complete fixed-length evidence references required")
    path=file_private(asset_root,audio_filename,130_000_000)
    if path.suffix!=".wav" or digest(path)!=audio_sha256:
        raise ContentHold("Narration audio digest mismatch")
    try:
        with wave.open(str(path),"rb") as wav:
            channels,width,rate,frames,coding,_=wav.getparams()
    except (OSError,wave.Error,EOFError) as exc:
        raise ContentHold("Invalid WAV bitstream") from exc
    if (coding!="NONE" or channels not in (1,2) or width!=2
        or rate not in (22050,44100,48000) or
        not 1<=frames/rate<=600):
        raise ContentHold("Unsupported speech audio properties")
    return {
        "schema_version":1,"project_id":package["project_id"],
        "work_order_id":package["work_order_id"],
        "source_script_sha256":package["script_sha256"],
        "audio_sha256":audio_sha256,
        "speech_job_sha256":claimed_speech_job_sha256,
        "signed_review_claim_sha256":claimed_signed_review_sha256,
        "duration_seconds":round(frames/rate,3),
        "sample_rate":rate,"channels":channels,
        "status":"AUDIO_INTEGRITY_ONLY_INFERENCE_AND_REVIEW_NOT_VERIFIED",
        "independent_model_execution_verified":False,
        "independent_human_signature_verified":False,
        "rights_legally_verified":False,
        "published":False,"publication_authorized":False,
    }
