"""P2-04g cinematic production manifest validator (source-only, no rendering).

The approval fields are operator assertions, not proof of licensed content.
Preflight never authorizes publishing or substitutes for independent human review.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json
import re

class CinematicHold(ValueError):
    pass

HASH = re.compile(r"^[0-9a-f]{64}$")
NAME = re.compile(r"^[A-Za-z0-9_-]{1,70}\.(wav|srt|mp4)$")
MAX_BYTES = 100_000_000

def digest_file(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def preflight(manifest: dict, asset_root: Path) -> dict:
    """Validate a bounded, private, rights-declared audio/caption timeline."""
    if not isinstance(manifest, dict) or set(manifest) != {
        "schema_version", "project_id", "runtime_seconds", "tracks",
        "scene_continuity_reviewed", "final_human_approval", "publication_authorized"
    }:
        raise CinematicHold("Invalid cinematic manifest")
    if manifest["schema_version"] != 1 or manifest["publication_authorized"] is not False:
        raise CinematicHold("Publishing must remain disabled")
    if manifest["final_human_approval"] is not False:
        raise CinematicHold("Preflight cannot claim final approval before rendering")
    runtime = manifest["runtime_seconds"]
    if type(runtime) not in (int, float) or not 30 <= runtime <= 120:
        raise CinematicHold("Only 30-120 second projects supported")
    if not isinstance(manifest["project_id"], str) or not re.fullmatch(r"[a-z][a-z0-9_-]{7,63}", manifest["project_id"]):
        raise CinematicHold("Invalid project ID")
    if manifest["scene_continuity_reviewed"] is not True:
        raise CinematicHold("Scene continuity review required")
    if not asset_root.is_absolute() or asset_root.is_symlink() or not asset_root.is_dir():
        raise CinematicHold("Approved absolute asset root required")
    tracks = manifest["tracks"]
    if not isinstance(tracks, list) or not 1 <= len(tracks) <= 24:
        raise CinematicHold("Track count out of bounds")
    seen = set()
    validated = []
    for track in tracks:
        if not isinstance(track, dict) or set(track) != {
            "role", "file", "sha256", "rights_evidence_sha256",
            "consent_evidence_sha256", "human_rights_reviewed",
            "start_seconds", "duration_seconds", "gain_db"
        }:
            raise CinematicHold("Invalid track")
        role = track["role"]
        if role not in ("narration", "dialogue", "music", "captions"):
            raise CinematicHold("Unsupported track role")
        filename = track["file"]
        if not isinstance(filename, str) or not NAME.fullmatch(filename):
            raise CinematicHold("Untrusted asset filename")
        if filename in seen:
            raise CinematicHold("Duplicate asset filename")
        seen.add(filename)
        if (role == "captions" and not filename.endswith(".srt")) or (
            role != "captions" and not filename.endswith(".wav")
        ):
            raise CinematicHold("Asset type does not match role")
        if track["human_rights_reviewed"] is not True or any(
            not isinstance(track[k], str) or not HASH.fullmatch(track[k])
            for k in ("sha256", "rights_evidence_sha256", "consent_evidence_sha256")
        ):
            raise CinematicHold("Rights or consent evidence incomplete")
        start, length, gain = (track[k] for k in ("start_seconds", "duration_seconds", "gain_db"))
        if (any(type(n) not in (int, float) for n in (start, length, gain))
            or not 0 <= start < runtime or length <= 0
            or start + length > runtime + 0.05 or not -36 <= gain <= 6):
            raise CinematicHold("Track timing or gain invalid")
        if role == "music" and gain > -6:
            raise CinematicHold("Music gain must not exceed -6dB")
        path = asset_root / filename
        if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= MAX_BYTES:
            raise CinematicHold("Missing, linked or oversized asset")
        if digest_file(path) != track["sha256"]:
            raise CinematicHold("Media SHA-256 mismatch")
        validated.append({"role": role, "file": filename, "sha256": track["sha256"]})
    if not any(x["role"] == "captions" for x in validated):
        raise CinematicHold("Accessible captions required")
    if not any(x["role"] in ("narration", "dialogue") for x in validated):
        raise CinematicHold("Narration or dialogue required")
    return {
        "status": "PREFLIGHT_ONLY_NOT_RENDERED",
        "project_id": manifest["project_id"],
        "tracks": validated,
        "runtime_seconds": runtime,
        "publication_authorized": False,
        "final_human_approval": False,
        "audio_sync_verified": False,
        "rights_independently_verified": False,
        "film_rendered": False,
    }
