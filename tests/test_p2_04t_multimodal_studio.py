"""P2-04t source rejection tests and optional synthetic FFmpeg rendering test.

All fixture images and audio are SYNTHETIC, never proof of AI generation.
"""
from hashlib import sha256
import os
from pathlib import Path
import shutil
import wave

import pytest

from app.creative_multimodal_studio import (
    StudioHold, validate_manifest, render, digest_file,
)

def fixture(tmp_path):
    pil=pytest.importorskip("PIL.Image")
    root=tmp_path/"private"
    root.mkdir(mode=0o700)
    scenes=[]
    for i in range(4):
        name=f"still{i}.png"
        path=root/name
        pil.new("RGB",(576,320),(i*50,35,90)).save(path)
        path.chmod(0o600)
        scenes.append({
            "kind":"image","file":name,
            "sha256":digest_file(path),
            "rights_evidence_sha256":"a"*64,
            "duration_seconds":8,
            "human_rights_reviewed":True,
        })
    audio=root/"narration.wav"
    with wave.open(str(audio),"wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(48000)
        wav.writeframes(b"\x01\x00"*(48000*32))
    audio.chmod(0o600)
    captions=root/"captions.srt"
    captions.write_text(
        "1\n00:00:00,000 --> 00:00:07,000\nFirst still scene.\n\n"
        "2\n00:00:08,000 --> 00:00:15,000\nSecond scene.\n\n"
        "3\n00:00:16,000 --> 00:00:23,000\nThird scene.\n\n"
        "4\n00:00:24,000 --> 00:00:31,000\nFourth scene.\n")
    captions.chmod(0o600)
    manifest={
        "schema_version":1,"project_id":"studio_test_film",
        "project_format":"education",
        "style_direction":"Four simple instructional storyboard visuals",
        "scenes":scenes,
        "voice":{"file":"narration.wav","sha256":digest_file(audio),
                 "rights_evidence_sha256":"b"*64,
                 "consent_evidence_sha256":"c"*64,
                 "duration_seconds":32,"start_seconds":0,
                 "human_rights_reviewed":True},
        "captions":{"file":"captions.srt","sha256":digest_file(captions),
                    "human_reviewed":True},
        "distribution_authorized":False,
        "final_human_approval":False,
    }
    return root,manifest

def test_valid_source_inputs_still_do_not_prove_ai(tmp_path):
    root,manifest=fixture(tmp_path)
    result=validate_manifest(manifest,root)
    assert result["runtime"]==32
    assert len(result["scenes"])==4
    assert result["caption_count"]==4

def test_no_auto_publication_or_false_approval(tmp_path):
    root,manifest=fixture(tmp_path)
    manifest["distribution_authorized"]=True
    with pytest.raises(StudioHold,match="distribution"):
        validate_manifest(manifest,root)
    manifest["distribution_authorized"]=False
    manifest["final_human_approval"]=True
    with pytest.raises(StudioHold,match="premature"):
        validate_manifest(manifest,root)

def test_source_digest_tampering_rejected(tmp_path):
    root,manifest=fixture(tmp_path)
    (root/"still0.png").write_bytes(b"tampered")
    with pytest.raises(StudioHold,match="checksum"):
        validate_manifest(manifest,root)

def test_unreviewed_image_rights_blocked(tmp_path):
    root,manifest=fixture(tmp_path)
    manifest["scenes"][0]["human_rights_reviewed"]=False
    with pytest.raises(StudioHold,match="rights"):
        validate_manifest(manifest,root)

def test_voice_rights_and_consent_blocked(tmp_path):
    root,manifest=fixture(tmp_path)
    manifest["voice"]["consent_evidence_sha256"]="missing"
    with pytest.raises(StudioHold,match="Rights"):
        validate_manifest(manifest,root)

def test_unsafe_scene_path_rejected(tmp_path):
    root,manifest=fixture(tmp_path)
    manifest["scenes"][0]["file"]="../outside.png"
    with pytest.raises(StudioHold,match="Unsafe"):
        validate_manifest(manifest,root)

def test_symlink_visual_asset_rejected(tmp_path):
    root,manifest=fixture(tmp_path)
    path=root/"still0.png"
    path.rename(root/"stored.png")
    path.symlink_to(root/"stored.png")
    with pytest.raises(StudioHold,match="Unsafe"):
        validate_manifest(manifest,root)

def test_mistimed_captions_fail(tmp_path):
    root,manifest=fixture(tmp_path)
    path=root/"captions.srt"
    path.write_text("1\n00:00:31,000 --> 00:00:33,000\nToo long.\n")
    manifest["captions"]["sha256"]=digest_file(path)
    with pytest.raises(StudioHold,match="subtitles"):
        validate_manifest(manifest,root)

def test_scene_duration_rejected(tmp_path):
    root,manifest=fixture(tmp_path)
    manifest["scenes"][0]["duration_seconds"]=30
    with pytest.raises(StudioHold,match="2-15"):
        validate_manifest(manifest,root)

def test_renderer_disabled_by_default(tmp_path,monkeypatch):
    root,manifest=fixture(tmp_path)
    monkeypatch.delenv("MAT_CREATIVE_MULTIMODAL_OFFLINE_ENABLED",raising=False)
    with pytest.raises(StudioHold,match="OFF"):
        render(manifest,root,root)

@pytest.mark.skipif(
    os.getenv("MAT_RUN_SLOW_MULTIMODAL_FFMPEG_TESTS")!="1"
    or shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="Operator-only, CPU-intensive 32-second synthetic 1080p render",
)
def test_synthetic_full_hd_video_with_voice_and_captions(tmp_path,monkeypatch):
    root,manifest=fixture(tmp_path)
    quarantine=tmp_path/"quarantine"
    quarantine.mkdir(mode=0o700)
    monkeypatch.setenv("MAT_CREATIVE_MULTIMODAL_OFFLINE_ENABLED","1")
    monkeypatch.setenv("MAT_CREATIVE_NETWORK_ISOLATED","1")
    receipt=render(manifest,root,quarantine)
    assert receipt["width"]==1920 and receipt["height"]==1080
    assert receipt["source_image_count"]==4
    assert receipt["audio_codec"]=="aac"
    assert receipt["subtitle_codec"]=="mov_text"
    assert receipt["real_ai_video_inference_independently_verified"] is False
    assert receipt["neural_voice_inference_independently_verified"] is False
    assert receipt["final_human_approval"] is False
    assert receipt["published"] is False
    output=list(quarantine.glob("*/finished.mp4"))
    assert len(output)==1
    assert digest_file(output[0])==receipt["final_sha256"]
