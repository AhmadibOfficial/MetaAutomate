"""P2-04q Piper native output tests: synthetic PCM is never model inference."""
from hashlib import sha256
import math
import struct
import wave

import pytest

from app.creative_audio_assets import AudioAssetHold, canonical, pcm_metrics, sha_file, verify_asset

def sample(tmp_path, *, seconds=3, sample_rate=22050):
    folder=tmp_path/"private"
    folder.mkdir(mode=0o700)
    file=folder/"generated.wav"
    with wave.open(str(file),"wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(sample_rate)
        for offset in range(seconds):
            frames=b"".join(struct.pack("<h",int(2500*math.sin(2*math.pi*440*i/sample_rate)))
                             for i in range(sample_rate))
            stream.writeframes(frames)
    file.chmod(0o600)
    job={"schema_version":1,"project_id":"voice_project",
         "asset_id":"voice_sample","kind":"speech","use_case":"film",
         "prompt":"A professionally spoken original educational sample.",
         "style_direction":"Clear natural voice","target_seconds":1,"language":"en",
         "model_checkpoint_sha256":"a"*64,
         "model_license_evidence_sha256":"b"*64,
         "content_rights_evidence_sha256":"c"*64,
         "authorization_sha256":"d"*64,
         "voice_likeness":"none","voice_consent_evidence_sha256":None,
         "artist_reference":"none","artist_rights_evidence_sha256":None,
         "distribution_authorized":False}
    receipt={"schema_version":1,"asset_id":job["asset_id"],
             "job_sha256":sha256(canonical(job)).hexdigest(),
             "model_checkpoint_sha256":"a"*64,
             "output_sha256":sha_file(file),"output_bytes":file.stat().st_size,
             "generation_mode":"OPERATOR_ATTESTED_LOCAL_MODEL",
             "state":"QUARANTINED_PENDING_INDEPENDENT_REVIEW",
             "published":False,"distribution_authorized":False}
    return file,job,receipt

def test_native_22050_with_variable_utterance_length_is_accepted_as_integrity_only(tmp_path):
    file,job,receipt=sample(tmp_path)
    evidence=verify_asset(job,receipt,file)
    assert evidence["media"]["sample_rate"]==22050
    assert evidence["media"]["duration_seconds"]==pytest.approx(3)
    assert evidence["model_inference_independently_verified"] is False
    assert evidence["content_safety_verified"] is False

def test_unlicensed_music_cannot_use_speech_duration_exception(tmp_path):
    file,job,receipt=sample(tmp_path)
    job["kind"]="music"
    receipt["job_sha256"]=sha256(canonical(job)).hexdigest()
    with pytest.raises(AudioAssetHold,match="PCM"):
        verify_asset(job,receipt,file)

def test_utterance_outside_bound_is_rejected(tmp_path):
    file,job,receipt=sample(tmp_path,seconds=8)
    with pytest.raises(AudioAssetHold,match="duration"):
        verify_asset(job,receipt,file)
