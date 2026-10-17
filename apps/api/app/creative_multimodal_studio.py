"""P2-04t: private multimodal studio composition from reviewed local assets.

An IMAGE or VIDEO asset may come from an independently approved local AI
worker or from the owner. This module does NOT run image/video/TTS models,
authenticate licence claims, prove model inference, or publish content.

Combines still PNGs, silent MP4 clips, PCM16 narration and reviewed SRT into
a 1920x1080/30fps AAC/MP4 with embedded timed subtitles in quarantine.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
from tempfile import TemporaryDirectory
from uuid import uuid4

from app.creative_cinematic_render import validate_srt, validate_wav, _probe, _streams, _duration

SHA = re.compile(r"^[a-f0-9]{64}$")
ID = re.compile(r"^[a-z][a-z0-9_-]{7,63}$")
SAFE = re.compile(r"^[A-Za-z0-9_-]{1,70}\.(png|mp4|wav|srt)$")
FORMATS = {"film", "advertisement", "social", "education", "product",
           "documentary", "music_visual", "audiobook_video", "podcast_video"}
SCENE_FIELDS = {"kind", "file", "sha256", "rights_evidence_sha256",
                "duration_seconds", "human_rights_reviewed"}
VOICE_FIELDS = {"file", "sha256", "rights_evidence_sha256",
                "consent_evidence_sha256", "duration_seconds",
                "start_seconds", "human_rights_reviewed"}
CAPTION_FIELDS = {"file", "sha256", "human_reviewed"}
PROJECT_FIELDS = {"schema_version", "project_id", "project_format",
                  "style_direction", "scenes", "voice", "captions",
                  "distribution_authorized", "final_human_approval"}
MAX_VIDEO = 750_000_000
MAX_IMAGE = 32_000_000

class StudioHold(ValueError):
    pass

def canonical(value:dict)->bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),
                      allow_nan=False,ensure_ascii=True).encode("ascii")

def digest_file(path:Path)->str:
    h=sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def _number(value,lower,upper)->bool:
    return type(value) in (int,float) and math.isfinite(value) and lower<=value<=upper

def _private_root(root:Path)->None:
    if (not root.is_absolute() or root.is_symlink() or not root.is_dir()
        or root.resolve()!=root or stat.S_IMODE(root.stat().st_mode)&0o077):
        raise StudioHold("Trusted private absolute non-symlink directory required")

def _asset(root:Path,name:str,digest:str,ext:str,maximum:int)->Path:
    if type(name) is not str or SAFE.fullmatch(name) is None or not name.endswith(ext):
        raise StudioHold("Unsafe media filename or unexpected type")
    if type(digest) is not str or SHA.fullmatch(digest) is None:
        raise StudioHold("Required exact media SHA-256 missing")
    path=root/name
    if (path.is_symlink() or not path.is_file() or path.resolve()!=path
        or not 44<path.stat().st_size<=maximum
        or stat.S_IMODE(path.stat().st_mode)&0o077):
        raise StudioHold("Unsafe or public source asset")
    if digest_file(path)!=digest:
        raise StudioHold("Source media checksum mismatch")
    return path

def _rights(value)->None:
    if type(value) is not str or SHA.fullmatch(value) is None:
        raise StudioHold("Rights/consent evidence hash required; legal authenticity not established")

def _run(argv:list[str],*,timeout:int=240,cwd:Path|None=None)->None:
    try:
        subprocess.run(argv,cwd=cwd,check=True,capture_output=True,timeout=timeout)
    except (OSError,subprocess.SubprocessError) as exc:
        raise StudioHold("Local FFmpeg composition failed") from exc

def _visual_probe(path:Path,kind:str,seconds:float)->dict:
    if kind=="image":
        try:
            from PIL import Image
            with Image.open(path) as image:
                if image.format!="PNG" or image.width<256 or image.height<256:
                    raise StudioHold("PNG visual source invalid")
                image.verify()
            return {"kind":"image","native_width":image.width,"native_height":image.height}
        except (ImportError,OSError,ValueError) as exc:
            raise StudioHold("Image decoder unavailable or image invalid") from exc
    probe=_probe(path)
    videos=_streams(probe,"video")
    if (len(videos)!=1 or _streams(probe,"audio")
        or _streams(probe,"subtitle")
        or videos[0].get("width",0)<256
        or videos[0].get("height",0)<256
        or abs(_duration(probe)-seconds)>0.35):
        raise StudioHold("Silent video stream dimensions or duration invalid")
    return {"kind":"video","native_width":videos[0]["width"],
            "native_height":videos[0]["height"]}

def validate_manifest(manifest:dict,asset_root:Path)->dict:
    """Validate technical compatibility. Does not certify rights or AI origin."""
    if type(manifest) is not dict or set(manifest)!=PROJECT_FIELDS:
        raise StudioHold("Unexpected unified studio manifest")
    if type(manifest["schema_version"]) is not int or manifest["schema_version"]!=1:
        raise StudioHold("Unsupported manifest schema")
    project_id=manifest["project_id"]
    if type(project_id) is not str or ID.fullmatch(project_id) is None:
        raise StudioHold("Invalid production ID")
    if type(manifest["project_format"]) is not str or manifest["project_format"] not in FORMATS:
        raise StudioHold("Invalid creative project format")
    style=manifest["style_direction"]
    if type(style) is not str or not 8<=len(style.strip())<=400:
        raise StudioHold("Bounded image/video style direction required")
    if (manifest["distribution_authorized"] is not False
        or manifest["final_human_approval"] is not False):
        raise StudioHold("No distribution or premature final approval allowed")
    _private_root(asset_root)
    scenes=manifest["scenes"]
    if type(scenes) is not list or not 4<=len(scenes)<=24:
        raise StudioHold("Four to 24 source visual scenes required")
    approved=[]
    seen=set()
    for scene in scenes:
        if type(scene) is not dict or set(scene)!=SCENE_FIELDS:
            raise StudioHold("Unexpected visual scene fields")
        kind=scene["kind"]
        if kind not in ("image","video") or type(kind) is not str:
            raise StudioHold("Only PNG images or silent MP4 visual scenes")
        if scene["human_rights_reviewed"] is not True:
            raise StudioHold("Visual rights review missing")
        _rights(scene["rights_evidence_sha256"])
        seconds=scene["duration_seconds"]
        if not _number(seconds,2,15):
            raise StudioHold("Each visual scene must be 2-15 seconds")
        if type(scene["file"]) is not str:
            raise StudioHold("Visual scene filename required")
        if scene["file"] in seen:
            raise StudioHold("Duplicate visual source not accepted in first release")
        seen.add(scene["file"])
        path=_asset(asset_root,scene["file"],scene["sha256"],
                    ".png" if kind=="image" else ".mp4",
                    MAX_IMAGE if kind=="image" else MAX_VIDEO)
        meta=_visual_probe(path,kind,float(seconds))
        approved.append((scene,path,meta))
    runtime=sum(float(x["duration_seconds"]) for x,_,_ in approved)
    if not 30<=runtime<=120:
        raise StudioHold("First cinematic production requires 30-120 seconds")
    voice=manifest["voice"]
    if type(voice) is not dict or set(voice)!=VOICE_FIELDS:
        raise StudioHold("Exactly one narrated WAV track required")
    if voice["human_rights_reviewed"] is not True:
        raise StudioHold("Narration consent and rights review missing")
    _rights(voice["rights_evidence_sha256"])
    _rights(voice["consent_evidence_sha256"])
    start=voice["start_seconds"]
    length=voice["duration_seconds"]
    if (not _number(start,0,runtime-0.2)
        or not _number(length,0.2,runtime)
        or start+length>runtime+0.1):
        raise StudioHold("Narration timing is outside the film")
    voice_path=_asset(asset_root,voice["file"],voice["sha256"],".wav",130_000_000)
    try:
        voice_meta=validate_wav(voice_path,float(length))
    except (ValueError,OSError) as exc:
        raise StudioHold("Speech WAV does not match declared PCM/timing") from exc
    captions=manifest["captions"]
    if type(captions) is not dict or set(captions)!=CAPTION_FIELDS:
        raise StudioHold("Exactly one reviewed SRT subtitles track required")
    if captions["human_reviewed"] is not True:
        raise StudioHold("Human subtitle review required")
    caption_path=_asset(asset_root,captions["file"],captions["sha256"],".srt",128_000)
    try:
        count=validate_srt(caption_path,runtime)
    except (ValueError,OSError) as exc:
        raise StudioHold("Malformed or mistimed subtitles") from exc
    return {"scenes":approved,"voice":voice_path,"voice_meta":voice_meta,
            "captions":caption_path,"caption_count":count,"runtime":runtime}

def render(manifest:dict,asset_root:Path,quarantine_root:Path)->dict:
    if (os.environ.get("MAT_CREATIVE_MULTIMODAL_OFFLINE_ENABLED")!="1"
        or os.environ.get("MAT_CREATIVE_NETWORK_ISOLATED")!="1"):
        raise StudioHold("Unified cinematic renderer OFF by default")
    valid=validate_manifest(manifest,asset_root)
    _private_root(quarantine_root)
    directory=quarantine_root/uuid4().hex
    directory.mkdir(mode=0o700)
    try:
        with TemporaryDirectory(dir=directory) as tmpname:
            tmp=Path(tmpname)
            segments=[]
            for i,(scene,path,_) in enumerate(valid["scenes"]):
                target=tmp/f"segment{i:02}.mp4"
                seconds=float(scene["duration_seconds"])
                command=["ffmpeg","-nostdin","-v","error","-protocol_whitelist","file"]
                if scene["kind"]=="image":
                    command+=["-loop","1","-framerate","30","-i",str(path)]
                else:
                    command+=["-i",str(path)]
                command+=["-t",f"{seconds:.3f}","-an",
                          "-vf","scale=1920:1080:force_original_aspect_ratio=decrease,"
                          "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,"
                          "fps=30,format=yuv420p",
                          "-c:v","libx264","-preset","veryfast","-crf","21",
                          "-pix_fmt","yuv420p","-y",str(target)]
                _run(command,timeout=240)
                segments.append(target)
            concat=tmp/"concat.txt"
            concat.write_text("".join(f"file '{p.name}'\n" for p in segments))
            silent=tmp/"silent.mp4"
            _run(["ffmpeg","-nostdin","-v","error","-f","concat","-safe","1",
                  "-protocol_whitelist","file","-i",str(concat),
                  "-c","copy","-y",str(silent)],cwd=tmp,timeout=240)
            voice_start=round(float(manifest["voice"]["start_seconds"])*1000)
            mix=(f"[1:a:0]aresample=48000,"
                 "aformat=sample_fmts=fltp:channel_layouts=stereo,"
                 f"adelay={voice_start}|{voice_start},apad,"
                 f"atrim=duration={valid['runtime']:.3f}[a]")
            movie=tmp/"finished.mp4"
            _run(["ffmpeg","-nostdin","-v","error",
                  "-protocol_whitelist","file","-i",str(silent),
                  "-protocol_whitelist","file","-i",str(valid["voice"]),
                  "-protocol_whitelist","file","-sub_charenc","UTF-8",
                  "-i",str(valid["captions"]),
                  "-filter_complex",mix,
                  "-map","0:v:0","-map","[a]","-map","2:s:0",
                  "-c:v","copy","-c:a","aac","-b:a","192k",
                  "-ar","48000","-ac","2","-c:s","mov_text",
                  "-t",f"{valid['runtime']:.3f}",
                  "-map_metadata","-1","-movflags","+faststart",
                  "-y",str(movie)],timeout=240)
            probe=_probe(movie)
            videos=_streams(probe,"video")
            audio=_streams(probe,"audio")
            sub=_streams(probe,"subtitle")
            if (len(videos)!=1 or len(audio)!=1 or len(sub)!=1
                or videos[0].get("width")!=1920
                or videos[0].get("height")!=1080
                or videos[0].get("r_frame_rate")!="30/1"
                or audio[0].get("codec_name")!="aac"
                or sub[0].get("codec_name")!="mov_text"
                or abs(_duration(probe)-valid["runtime"])>0.4):
                raise StudioHold("Final Full HD visual, speech and captions validation failed")
            if movie.stat().st_size>1_000_000_000:
                raise StudioHold("Output exceeds 1 GB limit")
            movie.chmod(0o600)
            movie.rename(directory/"finished.mp4")
        final=directory/"finished.mp4"
        report={
            "schema_version":1,"project_id":manifest["project_id"],
            "project_format":manifest["project_format"],
            "generated_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "manifest_sha256":sha256(canonical(manifest)).hexdigest(),
            "final_sha256":digest_file(final),
            "final_bytes":final.stat().st_size,
            "runtime_seconds":_duration(probe),"width":1920,
            "height":1080,"fps":30,"audio_codec":"aac",
            "subtitle_codec":"mov_text","caption_count":valid["caption_count"],
            "source_image_count":sum(x["kind"]=="image" for x,_,_ in valid["scenes"]),
            "source_video_count":sum(x["kind"]=="video" for x,_,_ in valid["scenes"]),
            "native_1080p_ai_generation_verified":False,
            "real_ai_image_inference_independently_verified":False,
            "real_ai_video_inference_independently_verified":False,
            "neural_voice_inference_independently_verified":False,
            "legal_rights_independently_authenticated":False,
            "speech_quality_independently_reviewed":False,
            "final_human_approval":False,"distribution_authorized":False,
            "published":False,
            "status":"QUARANTINED_PENDING_INDEPENDENT_FINAL_REVIEW",
        }
        record=directory/"receipt.json"
        record.write_bytes(canonical(report)+b"\n")
        record.chmod(0o600)
        return report
    except Exception:
        shutil.rmtree(directory)
        raise
