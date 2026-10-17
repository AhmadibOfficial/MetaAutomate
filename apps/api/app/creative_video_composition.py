"""P2-04f: offline, fail-closed video composition from locally approved shots.

Not a generation engine. No network, no publishing, no shell invocation.
Requires preinstalled ffmpeg/ffprobe and an externally isolated runtime.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import subprocess
from tempfile import TemporaryDirectory

SHA = re.compile(r"^[a-f0-9]{64}$")
ID = re.compile(r"^[a-z][a-z0-9_-]{7,63}$")
class CompositionBlocked(ValueError): pass

def _hash(path):
    h=sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()

def _probe(path):
    try:
        x=subprocess.run(["ffprobe","-v","error","-show_entries",
            "format=duration:stream=codec_type,width,height","-of","json",str(path)],
            check=True,capture_output=True,text=True,timeout=20)
        obj=json.loads(x.stdout)
        streams=[s for s in obj.get("streams",[]) if s.get("codec_type")=="video"]
        if len(streams)!=1:raise CompositionBlocked("Exactly one video stream required")
        return float(obj["format"]["duration"]), streams[0]
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as exc:
        raise CompositionBlocked("Video probe failed") from exc

def validate(manifest, root):
    if type(manifest)!=dict or set(manifest)!={"schema_version","project_id","shots","reviewer_id","distribution_authorized"}:
        raise CompositionBlocked("Unexpected manifest schema")
    if manifest["schema_version"]!=1 or manifest["distribution_authorized"] is not False:
        raise CompositionBlocked("Project not eligible for private composition")
    if not isinstance(manifest["project_id"],str) or not ID.fullmatch(manifest["project_id"]):
        raise CompositionBlocked("Bad project ID")
    if not isinstance(manifest["reviewer_id"],str) or len(manifest["reviewer_id"])<8:
        raise CompositionBlocked("Human reviewer required")
    shots=manifest["shots"]
    if type(shots)!=list or not 4<=len(shots)<=64:raise CompositionBlocked("4-64 shots required")
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise CompositionBlocked("Trusted absolute asset root required")
    approved=[]
    for shot in shots:
        if type(shot)!=dict or set(shot)!={"file","sha256","rights_evidence_sha256","human_approved","duration_seconds"}:
            raise CompositionBlocked("Invalid shot schema")
        filename=shot["file"]
        if not isinstance(filename,str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,70}\.mp4",filename):
            raise CompositionBlocked("Unsafe shot file name")
        if shot["human_approved"] is not True or not all(
            isinstance(shot[k],str) and SHA.fullmatch(shot[k])
            for k in ("sha256","rights_evidence_sha256")):
            raise CompositionBlocked("Shot rights or review incomplete")
        path=root/filename
        if path.is_symlink() or not path.is_file() or path.stat().st_size>100_000_000:
            raise CompositionBlocked("Shot unavailable or unsafe")
        if _hash(path)!=shot["sha256"]:raise CompositionBlocked("Shot integrity mismatch")
        duration,stream=_probe(path)
        declared=shot["duration_seconds"]
        if type(declared) not in (int,float) or not 2<=declared<=15 or abs(declared-duration)>0.15:
            raise CompositionBlocked("Shot duration mismatch")
        if stream.get("width",0)<256 or stream.get("height",0)<256:
            raise CompositionBlocked("Insufficient source resolution")
        approved.append((path,duration))
    total=sum(duration for _,duration in approved)
    if not 30<=total<=120:raise CompositionBlocked("Total duration must be 30-120 seconds")
    return approved,total

def compose(manifest,asset_root,quarantine_root):
    """Assemble approved inputs as a silent 1080p timeline; audio requires separate review."""
    if os.environ.get("MAT_CREATIVE_COMPOSITION_OFFLINE_ENABLED")!="1":
        raise CompositionBlocked("Composition OFF by default")
    approved,total=validate(manifest,asset_root)
    if (not quarantine_root.is_absolute() or quarantine_root.is_symlink() or
        not quarantine_root.is_dir() or stat.S_IMODE(quarantine_root.stat().st_mode)&0o077):
        raise CompositionBlocked("Private 0700 quarantine required")
    target=quarantine_root / (manifest["project_id"]+".mp4")
    if target.exists():raise CompositionBlocked("Refusing overwrite")
    with TemporaryDirectory(dir=quarantine_root) as temp:
        tmp=Path(temp)
        segments=[]
        for i,(path,_) in enumerate(approved):
            segment=tmp/("part%03d.mp4"%i)
            command=["ffmpeg","-nostdin","-hide_banner","-loglevel","error",
              "-protocol_whitelist","file","-i",str(path),"-an","-vf",
              "scale=1920:1080:force_original_aspect_ratio=decrease,"
              "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,fps=30,format=yuv420p",
              "-c:v","libx264","-preset","medium","-crf","18","-movflags","+faststart",
              "-y",str(segment)]
            subprocess.run(command,check=True,timeout=240,capture_output=True)
            segments.append(segment)
        concat=tmp/"list.txt"
        concat.write_text("".join("file '%s'\n"%p.name for p in segments))
        output=tmp/"final.mp4"
        subprocess.run(["ffmpeg","-nostdin","-hide_banner","-loglevel","error",
            "-f","concat","-safe","1","-protocol_whitelist","file",
            "-i",str(concat),"-c","copy","-y",str(output)],
            cwd=tmp,check=True,timeout=240,capture_output=True)
        actual,stream=_probe(output)
        if not 30<=actual<=120 or abs(actual-total)>1.0 or (
          stream.get("width"),stream.get("height"))!=(1920,1080):
            raise CompositionBlocked("Final media verification failed")
        os.chmod(output,0o600)
        output.rename(target)
    return {"status":"QUARANTINED_PENDING_FINAL_HUMAN_REVIEW",
       "sha256":_hash(target),"seconds":actual,"width":1920,"height":1080,
       "has_audio":False,"published":False,"release_authorized":False,
       "native_1080p_inference":False}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--assets",type=Path,required=True)
    parser.add_argument("--quarantine",type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.manifest.is_symlink() or args.manifest.stat().st_size>32768:
            raise CompositionBlocked("Invalid manifest")
        manifest=json.loads(args.manifest.read_text())
        print(json.dumps(compose(manifest,args.assets,args.quarantine),sort_keys=True))
    except (CompositionBlocked,OSError,ValueError,subprocess.SubprocessError) as exc:
        parser.exit(2,"Composition HOLD: "+str(exc)+"\\n")
if __name__=="__main__":main()
