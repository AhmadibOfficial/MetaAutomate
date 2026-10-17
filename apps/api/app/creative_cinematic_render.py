"""P2-04h: offline cinematic finishing of already-composed, locally approved MP4.

No AI generation, remote media, network access, publishing, or rights authentication.
Operator must enforce an actual isolated runtime separately from these env flags.
"""
from __future__ import annotations

import argparse
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
import sys
from tempfile import TemporaryDirectory
from uuid import uuid4
import wave

from app.creative_cinematic_preflight import CinematicHold, preflight, digest_file

SRT_BLOCK = re.compile(
    r"(?P<index>[1-9][0-9]{0,3})\n"
    r"(?P<start>[0-9]{2}:[0-5][0-9]:[0-5][0-9],[0-9]{3}) --> "
    r"(?P<end>[0-9]{2}:[0-5][0-9]:[0-5][0-9],[0-9]{3})\n"
    r"(?P<text>[^\x00-\x08\x0b-\x1f\x7f]+)"
)
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_-]{7,63}$")
SHA = re.compile(r"^[a-f0-9]{64}$")

def _locked_dir(path: Path, *, create: bool = False) -> Path:
    if not path.is_absolute() or path.is_symlink():
        raise CinematicHold("Absolute, non-symlink private directory required")
    if create:
        path.mkdir(mode=0o700)
    if not path.is_dir() or path.resolve() != path or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise CinematicHold("Directory is not a private regular path")
    return path

def _locked_file(path: Path, *, maximum: int = 100_000_000) -> None:
    if (path.is_symlink() or not path.is_file() or path.resolve() != path
        or not 0 < path.stat().st_size <= maximum):
        raise CinematicHold("Unsafe or missing local media file")
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise CinematicHold("Local media is accessible to group/other")

def _timecode(value: str) -> float:
    h, m, second_ms = value.split(":")
    s, ms = second_ms.split(",")
    hours = int(h)
    if hours > 1:
        raise CinematicHold("Caption timecode out of bounds")
    return hours * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

def validate_srt(path: Path, runtime: float) -> int:
    """Validate timing and markup, not semantic accuracy of the captions."""
    _locked_file(path, maximum=128_000)
    try:
        source = path.read_text(encoding="utf-8-sig")
    except UnicodeError as exc:
        raise CinematicHold("Subtitle encoding invalid") from exc
    normalized = source.replace("\r\n", "\n")
    if "\r" in normalized or len(normalized) > 128_000:
        raise CinematicHold("Subtitle newline/length invalid")
    blocks = normalized.strip().split("\n\n")
    if not 1 <= len(blocks) <= 250:
        raise CinematicHold("Subtitle block count invalid")
    end_of_last = 0.0
    for index, block in enumerate(blocks, 1):
        match = SRT_BLOCK.fullmatch(block)
        if not match or int(match.group("index")) != index:
            raise CinematicHold("Malformed or nonsequential SRT cue")
        start, end = _timecode(match.group("start")), _timecode(match.group("end"))
        text = match.group("text").strip()
        if (not end > start >= end_of_last or end > runtime + 0.05
            or not text or len(text) > 300 or "<" in text or ">" in text
            or "\n\n" in text):
            raise CinematicHold("Unsafe or mistimed subtitle")
        end_of_last = end
    return len(blocks)

def validate_wav(path: Path, declared_duration: float) -> dict:
    """Only bounded uncompressed PCM mono/stereo audio; sample metadata is checked."""
    _locked_file(path)
    try:
        with wave.open(str(path), "rb") as f:
            ch, width, rate, frames, compression, _ = f.getparams()
    except (wave.Error, EOFError, OSError) as exc:
        raise CinematicHold("WAV decoder rejected audio") from exc
    if compression != "NONE" or ch not in (1, 2) or width != 2 or rate not in (44100, 48000):
        raise CinematicHold("Only PCM 16-bit mono/stereo WAV at 44.1/48kHz is allowed")
    if frames < 1 or abs(frames/rate - declared_duration) > 0.08:
        raise CinematicHold("Actual WAV length disagrees with manifest")
    return {"channels": ch, "sample_rate": rate, "duration_seconds": frames/rate}

def _probe(path: Path) -> dict:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-protocol_whitelist", "file",
             "-show_entries",
             "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels,duration",
             "-of", "json", str(path)],
            check=True, capture_output=True, text=True, timeout=30)
        probe = json.loads(result.stdout)
        if not isinstance(probe, dict):
            raise ValueError("Unexpected probe result")
        return probe
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        raise CinematicHold("ffprobe failed") from exc

def _streams(probe: dict, kind: str) -> list:
    return [s for s in probe.get("streams", [])
            if isinstance(s, dict) and s.get("codec_type") == kind]

def _duration(probe: dict) -> float:
    try:
        value = float(probe["format"]["duration"])
        if not math.isfinite(value) or value <= 0:
            raise ValueError("Non-finite duration")
        return value
    except (TypeError, KeyError, ValueError) as exc:
        raise CinematicHold("Unverifiable media duration") from exc

def validate_inputs(manifest: dict, root: Path, video_name: str, expected_video_sha256: str) -> dict:
    """Enforce evidence and technical compatibility before invoking FFmpeg."""
    _locked_dir(root)
    preflight(manifest, root)
    if not isinstance(video_name, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,70}\.mp4", video_name):
        raise CinematicHold("Unsafe source video name")
    if not isinstance(expected_video_sha256, str) or not SHA.fullmatch(expected_video_sha256):
        raise CinematicHold("Invalid source video SHA")
    video = root / video_name
    _locked_file(video, maximum=1_000_000_000)
    if digest_file(video) != expected_video_sha256:
        raise CinematicHold("Source video digest mismatch")
    probe = _probe(video)
    videos = _streams(probe, "video")
    if (len(videos) != 1 or _streams(probe, "audio") or _streams(probe, "subtitle")
        or videos[0].get("width") != 1920 or videos[0].get("height") != 1080
        or videos[0].get("r_frame_rate") != "30/1"):
        raise CinematicHold("Expected exactly one silent 1080p/30 video stream")
    runtime = float(manifest["runtime_seconds"])
    if abs(_duration(probe) - runtime) > 0.30:
        raise CinematicHold("Video duration disagrees with cinematic manifest")
    captions = []
    audio = []
    for track in manifest["tracks"]:
        path = root / track["file"]
        _locked_file(path)
        if track["role"] == "captions":
            captions.append((path, validate_srt(path, runtime)))
        else:
            audio.append((track, path, validate_wav(path, float(track["duration_seconds"]))))
    if len(captions) != 1:
        raise CinematicHold("Exactly one caption stream supported in first release")
    if not 1 <= len(audio) <= 16:
        raise CinematicHold("1-16 audio tracks supported")
    return {"video": video, "video_sha256": expected_video_sha256,
            "runtime": runtime, "audio": audio,
            "captions": captions[0], "probe": probe}

def render(manifest: dict, asset_root: Path, quarantine_root: Path,
           video_name: str, video_sha256: str) -> dict:
    if (os.environ.get("MAT_CREATIVE_CINEMATIC_RENDER_ENABLED") != "1"
        or os.environ.get("MAT_CREATIVE_NETWORK_ISOLATED") != "1"):
        raise CinematicHold("Offline cinematic rendering disabled by default")
    media = validate_inputs(manifest, asset_root, video_name, video_sha256)
    _locked_dir(quarantine_root)
    receipt_id = uuid4().hex
    destination = quarantine_root / receipt_id
    destination.mkdir(mode=0o700)
    try:
        with TemporaryDirectory(dir=destination) as temporary:
            temporary = Path(temporary)
            output = temporary / "film.mp4"
            command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                       "-protocol_whitelist", "file", "-i", str(media["video"])]
            for track, path, _ in media["audio"]:
                command += ["-protocol_whitelist", "file", "-i", str(path)]
            command += ["-protocol_whitelist", "file", "-sub_charenc", "UTF-8",
                        "-i", str(media["captions"][0])]
            filters = []
            for i, (track, _, _) in enumerate(media["audio"]):
                gain = float(track["gain_db"])
                delay = int(round(float(track["start_seconds"]) * 1000))
                length = float(track["duration_seconds"])
                filters.append(
                    f"[{i+1}:a:0]atrim=duration={length:.3f},asetpts=PTS-STARTPTS,"
                    f"aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,"
                    f"volume={gain:.2f}dB,adelay={delay}|{delay}[a{i}]")
            names = "".join(f"[a{i}]" for i in range(len(media["audio"])))
            filters.append(
                f"{names}amix=inputs={len(media['audio'])}:duration=longest:"
                "dropout_transition=0,apad,alimiter=limit=0.95,"
                f"atrim=duration={media['runtime']:.3f}[sound]")
            command += ["-filter_complex", ";".join(filters),
                        "-map", "0:v:0", "-map", "[sound]",
                        "-map", f"{len(media['audio'])+1}:s:0",
                        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                        "-ar", "48000", "-ac", "2", "-c:s", "mov_text",
                        "-t", f"{media['runtime']:.3f}",
                        "-map_metadata", "-1", "-movflags", "+faststart",
                        "-y", str(output)]
            try:
                subprocess.run(command, check=True, capture_output=True, timeout=300)
            except (OSError, subprocess.SubprocessError) as exc:
                raise CinematicHold("Bounded offline FFmpeg render failed") from exc
            _locked_file(output, maximum=1_000_000_000) if False else None
            if output.is_symlink() or not output.is_file() or output.stat().st_size > 1_000_000_000:
                raise CinematicHold("Renderer produced unsafe media")
            os.chmod(output, 0o600)
            final_probe = _probe(output)
            out_v, out_a, out_s = (_streams(final_probe, k) for k in ("video", "audio", "subtitle"))
            if (len(out_v) != 1 or len(out_a) != 1 or len(out_s) != 1
                or out_v[0].get("width") != 1920 or out_v[0].get("height") != 1080
                or out_v[0].get("r_frame_rate") != "30/1"
                or out_a[0].get("codec_name") != "aac"
                or out_s[0].get("codec_name") != "mov_text"
                or abs(_duration(final_probe) - media["runtime"]) > 0.35):
                raise CinematicHold("Final stream and timing verification failed")
            final_path = destination / "film.mp4"
            output.rename(final_path)
        receipt = {
            "schema_version": 1,
            "project_id": manifest["project_id"],
            "rendered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "source_video_sha256": media["video_sha256"],
            "manifest_sha256": sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "final_sha256": digest_file(final_path),
            "final_bytes": final_path.stat().st_size,
            "duration_seconds": _duration(final_probe),
            "width": 1920, "height": 1080, "fps": 30,
            "audio_codec": "aac", "subtitle_codec": "mov_text",
            "caption_count": media["captions"][1],
            "state": "QUARANTINED_PENDING_INDEPENDENT_FINAL_REVIEW",
            "authentic_rights_verified_by_code": False,
            "semantic_caption_sync_verified": False,
            "actual_AI_inference_proven": False,
            "final_human_approval": False,
            "published": False, "release_authorized": False,
        }
        receipt_path = destination / "receipt.json"
        receipt_path.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
        receipt_path.chmod(0o600)
        return receipt
    except Exception:
        shutil.rmtree(destination)
        raise

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Offline quarantined cinematic finishing")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--quarantine", type=Path, required=True)
    parser.add_argument("--video-name", required=True)
    parser.add_argument("--video-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        if args.manifest.is_symlink() or not args.manifest.is_file() or args.manifest.stat().st_size > 32768:
            raise CinematicHold("Invalid manifest file")
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        result = render(manifest, args.assets, args.quarantine, args.video_name, args.video_sha256)
    except (OSError, CinematicHold, ValueError, subprocess.SubprocessError) as exc:
        print("Cinematic rendering HOLD: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
