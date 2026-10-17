"""P2-04h: source tests; synthetic footage is never AI inference evidence."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import wave

import pytest

from app import creative_cinematic_render as mod
from app.creative_cinematic_preflight import CinematicHold

def make_assets(tmp_path, duration=30):
    root = tmp_path / "assets"
    root.mkdir(mode=0o700)
    video = root / "scene.mp4"
    video.write_bytes(b"synthetic fixture, not a video")
    video.chmod(0o600)
    srt = root / "titles.srt"
    srt.write_text("1\n00:00:00,000 --> 00:00:04,000\nExample narration.\n\n"
                   "2\n00:00:15,000 --> 00:00:19,000\nA second scene.\n")
    srt.chmod(0o600)
    wav = root / "voice.wav"
    with wave.open(str(wav), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(48000)
        output.writeframes(b"\x00\x00" * 48000 * duration)
    wav.chmod(0o600)
    def track(role, path):
        return {
            "role": role, "file": path.name,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "rights_evidence_sha256": "a"*64,
            "consent_evidence_sha256": "b"*64,
            "human_rights_reviewed": True,
            "start_seconds": 0, "duration_seconds": duration,
            "gain_db": -12,
        }
    manifest = {
        "schema_version": 1, "project_id": "test_film",
        "runtime_seconds": duration,
        "tracks": [track("narration", wav), track("captions", srt)],
        "scene_continuity_reviewed": True,
        "final_human_approval": False, "publication_authorized": False,
    }
    return root, manifest, hashlib.sha256(video.read_bytes()).hexdigest()

def test_strict_srt_accepts_ordered_cues(tmp_path):
    root, manifest, _ = make_assets(tmp_path)
    assert mod.validate_srt(root/"titles.srt", 30) == 2

@pytest.mark.parametrize("content", [
    "1\n00:00:29,000 --> 00:00:31,000\nToo late\n",
    "1\n00:00:00,000 --> 00:00:04,000\n<script>alert(1)</script>\n",
    "2\n00:00:00,000 --> 00:00:04,000\nOut of sequence\n",
    "1\n00:00:05,000 --> 00:00:04,000\nBackwards\n",
    "1\n00:00:00,000 --> 00:00:04,000\nFirst\n\n"
    "2\n00:00:03,000 --> 00:00:05,000\nOverlap\n",
])
def test_bad_srt_rejected(tmp_path, content):
    root, _, _ = make_assets(tmp_path)
    (root/"titles.srt").write_text(content)
    with pytest.raises(CinematicHold):
        mod.validate_srt(root/"titles.srt", 30)

def test_pcm_wav_duration_is_verified(tmp_path):
    root, _, _ = make_assets(tmp_path)
    assert mod.validate_wav(root/"voice.wav", 30)["sample_rate"] == 48000
    with pytest.raises(CinematicHold, match="length"):
        mod.validate_wav(root/"voice.wav", 29)

def test_disabled_without_explicit_flags(tmp_path, monkeypatch):
    root, manifest, sha = make_assets(tmp_path)
    monkeypatch.delenv("MAT_CREATIVE_CINEMATIC_RENDER_ENABLED", raising=False)
    with pytest.raises(CinematicHold, match="disabled"):
        mod.render(manifest, root, tmp_path, "scene.mp4", sha)

def test_video_digest_does_not_trust_attestation(tmp_path, monkeypatch):
    root, manifest, sha = make_assets(tmp_path)
    with pytest.raises(CinematicHold, match="digest mismatch"):
        mod.validate_inputs(manifest, root, "scene.mp4", "0"*64)

def test_requires_silent_full_hd_input(tmp_path, monkeypatch):
    root, manifest, sha = make_assets(tmp_path)
    monkeypatch.setattr(mod, "_probe", lambda _: {
        "format": {"duration": "30"},
        "streams": [
            {"codec_type": "video", "width": 1920, "height": 1080,
             "r_frame_rate": "30/1"},
            {"codec_type": "audio"}
        ]
    })
    with pytest.raises(CinematicHold, match="silent"):
        mod.validate_inputs(manifest, root, "scene.mp4", sha)

def test_symlink_source_rejected(tmp_path, monkeypatch):
    root, manifest, sha = make_assets(tmp_path)
    (root/"scene.mp4").rename(root/"original.mp4")
    (root/"scene.mp4").symlink_to(root/"original.mp4")
    with pytest.raises(CinematicHold, match="Unsafe"):
        mod.validate_inputs(manifest, root, "scene.mp4", sha)

def test_preflight_rejects_unauthorized_music(tmp_path, monkeypatch):
    root, manifest, sha = make_assets(tmp_path)
    manifest["tracks"][0]["human_rights_reviewed"] = False
    with pytest.raises(CinematicHold):
        mod.validate_inputs(manifest, root, "scene.mp4", sha)

@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
                    reason="Local test requires installed ffmpeg/ffprobe")
def test_synthetic_thirty_second_cinematic_render_is_quarantined(tmp_path, monkeypatch):
    root, manifest, _ = make_assets(tmp_path)
    # A colour test fixture checks audio/subtitle muxing, NOT model inference.
    video = root/"scene.mp4"
    subprocess.run([
        "ffmpeg", "-v", "error", "-f", "lavfi",
        "-i", "color=c=blue:size=1920x1080:rate=30:duration=30",
        "-an", "-c:v", "mpeg4", "-q:v", "25", "-y", str(video)
    ], check=True, capture_output=True, timeout=120)
    video.chmod(0o600)
    quarantine = tmp_path/"quarantine"
    quarantine.mkdir(mode=0o700)
    monkeypatch.setenv("MAT_CREATIVE_CINEMATIC_RENDER_ENABLED", "1")
    monkeypatch.setenv("MAT_CREATIVE_NETWORK_ISOLATED", "1")
    result = mod.render(
        manifest, root, quarantine, "scene.mp4",
        hashlib.sha256(video.read_bytes()).hexdigest())
    assert result["state"] == "QUARANTINED_PENDING_INDEPENDENT_FINAL_REVIEW"
    assert result["final_human_approval"] is False
    assert result["published"] is False
    assert result["caption_count"] == 2
    final_files = list(quarantine.glob("*/film.mp4"))
    assert len(final_files) == 1
    assert hashlib.sha256(final_files[0].read_bytes()).hexdigest() == result["final_sha256"]
    final_probe = mod._probe(final_files[0])
    assert len(mod._streams(final_probe, "audio")) == 1
    assert len(mod._streams(final_probe, "subtitle")) == 1
