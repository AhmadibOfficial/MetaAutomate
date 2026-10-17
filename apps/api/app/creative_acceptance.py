"""P2-04d independent, read-only acceptance of quarantined REAL Diffusers outputs.

Evidence validation is not a content safety scan, license audit, or release grant.
Run inside the approved offline environment. Requires Pillow; video requires ffprobe.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import stat
import subprocess
import sys

from app.creative_local_generation import GenerationBlocked, read_json, canonical

def _regular_private(path: Path, maximum: int) -> None:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
        raise GenerationBlocked("Evidence is missing, symlinked or over size limit")
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise GenerationBlocked("Evidence file is accessible by group/other")

def _hash_file(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for part in iter(lambda: f.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()

def verify(folder: Path, expected_kind: str) -> dict:
    if expected_kind not in ("image", "video"):
        raise GenerationBlocked("Unsupported kind")
    if not folder.is_absolute() or folder.is_symlink() or not folder.is_dir():
        raise GenerationBlocked("Quarantine folder must be absolute, existing, non-symlink")
    if stat.S_IMODE(folder.stat().st_mode) & 0o077:
        raise GenerationBlocked("Quarantine folder has unsafe permissions")
    receipt_path = folder / "receipt.json"
    media = folder / ("generated.png" if expected_kind == "image" else "generated.mp4")
    _regular_private(receipt_path, 16384)
    _regular_private(media, 100_000_000)
    receipt = read_json(receipt_path)
    required = {
        "schema_version": 1, "output_kind": expected_kind,
        "generation_mode": "LOCAL_DIFFUSERS_REAL_INFERENCE",
        "real_ai_output_verified": True,
        "output_state": "QUARANTINED_PENDING_INDEPENDENT_SAFETY_REVIEW",
        "published": False, "customer_distribution_authorized": False,
        "content_safety_independently_verified": False,
        "rights_independently_authenticated_by_worker": False,
    }
    if any(receipt.get(k) != v or type(receipt.get(k)) is not type(v) for k, v in required.items()):
        raise GenerationBlocked("Receipt not from claimed quarantined real inference")
    for field in ("job_sha256", "authorization_sha256", "model_tree_sha256", "output_sha256"):
        value = receipt.get(field)
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise GenerationBlocked("Invalid receipt digest")
    size = media.stat().st_size
    if size < 32 or type(receipt.get("output_bytes")) is not int or receipt["output_bytes"] != size:
        raise GenerationBlocked("Media byte count mismatch")
    if _hash_file(media) != receipt["output_sha256"]:
        raise GenerationBlocked("Media SHA-256 mismatch")
    if expected_kind == "image":
        try:
            from PIL import Image
            with Image.open(media) as img:
                if img.format != "PNG":
                    raise GenerationBlocked("Image is not PNG")
                width, height = img.size
                img.verify()
            if not 256 <= width <= 768 or not 256 <= height <= 768:
                raise GenerationBlocked("Image dimensions out of bounds")
            metadata = {"width": width, "height": height, "format": "PNG"}
        except ImportError as e:
            raise GenerationBlocked("Pillow unavailable for PNG validation") from e
        except (OSError, ValueError) as e:
            raise GenerationBlocked("Invalid PNG bitstream") from e
    else:
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=codec_name,width,height,nb_frames,r_frame_rate,duration",
                 "-of", "json", str(media)],
                capture_output=True, text=True, timeout=20, check=True)
            streams = json.loads(result.stdout).get("streams", [])
        except (OSError, ValueError, subprocess.SubprocessError) as e:
            raise GenerationBlocked("ffprobe failed or unavailable") from e
        if len(streams) != 1:
            raise GenerationBlocked("Exactly one decodable video stream required")
        stream = streams[0]
        if stream.get("width") != 576 or stream.get("height") != 320 or stream.get("r_frame_rate") != "8/1":
            raise GenerationBlocked("Video dimensions/frame rate mismatch")
        frames = stream.get("nb_frames")
        if not isinstance(frames, str) or not frames.isdigit() or not 16 <= int(frames) <= 64:
            raise GenerationBlocked("Video frame count missing or invalid")
        metadata = {"width": 576, "height": 320, "fps": 8,
                    "frames": int(frames), "codec": stream.get("codec_name")}
    return {
        "schema_version": 1, "acceptance": "MEDIA_INTEGRITY_ONLY_NOT_SAFETY_OR_RIGHTS_CLEARANCE",
        "output_kind": expected_kind, "output_sha256": receipt["output_sha256"],
        "receipt_sha256": _hash_file(receipt_path), "output_bytes": size,
        "media": metadata, "operator_attested_real_inference": True,
        "independently_proven_model_execution": False,
        "rights_validated": False, "content_safety_validated": False,
        "distribution_authorized": False, "published": False,
    }

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--quarantine-folder", type=Path, required=True)
    p.add_argument("--kind", choices=("image", "video"), required=True)
    args = p.parse_args(argv)
    try:
        result = verify(args.quarantine_folder, args.kind)
    except (GenerationBlocked, OSError, ImportError) as e:
        print("Acceptance HOLD: " + str(e), file=sys.stderr)
        return 2
    print(canonical(result).decode())
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
