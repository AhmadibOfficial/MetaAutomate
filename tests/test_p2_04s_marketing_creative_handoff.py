"""P2-04s marketing-to-speech bridge source tests (synthetic audio only)."""
from hashlib import sha256
import wave

import pytest

from app.marketing_content_workbench import ContentHold
from app.marketing_creative_studio_handoff import (
    prepare_narrated_campaign, inspect_audio_attachment,
)

def brief():
    return {
        "campaign_id":"metareach_october",
        "brand":"MetaAutomate","industry":"AI and business workflows",
        "offer":"Systems that simplify everyday business activities",
        "audience":"Small business operators",
        "goal":"Explain practical product benefits, no financial guarantees",
        "channels":["instagram","youtube"],
        "verified_facts":[{"claim":"MetaAutomate develops AI and technology solutions.",
                           "source_reference":"Approved company positioning"}],
        "approved_cta":"Learn about MetaAutomate",
        "content_kinds":["social","video","ads"],
        "country":"Nigeria","evidence_owner":"editorial_team",
    }

SCRIPT="MetaAutomate explores practical technology solutions for everyday business workflows."

def package():
    return prepare_narrated_campaign(
        brief(),work_order_id="metareach_october:video:youtube",
        script=SCRIPT,evidence_checked=True,rights_checked=True)

def wav(tmp_path):
    root=tmp_path/"assets"
    root.mkdir(mode=0o700)
    path=root/"spoken.wav"
    with wave.open(str(path),"wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(22050)
        f.writeframes(b"\x01\x00"*22050)
    path.chmod(0o600)
    return root,path

def test_campaign_handoff_is_not_automatic_generation():
    result=package()
    assert result["status"]=="SCRIPT_REVIEW_CLAIM_ONLY_PENDING_VOICE_INFERENCE"
    assert result["speech_independently_verified"] is False
    assert result["publication_authorized"] is False
    assert result["scheduling_authorized"] is False

def test_rights_declaration_is_required_for_video():
    with pytest.raises(ContentHold,match="editorial review"):
        prepare_narrated_campaign(
            brief(),work_order_id="metareach_october:video:youtube",
            script=SCRIPT,evidence_checked=True,rights_checked=False)

def test_audio_attachment_cannot_claim_real_inference(tmp_path):
    root,path=wav(tmp_path)
    result=inspect_audio_attachment(
        package(),asset_root=root,audio_filename=path.name,
        audio_sha256=sha256(path.read_bytes()).hexdigest(),
        claimed_speech_job_sha256="a"*64,
        claimed_signed_review_sha256="b"*64)
    assert result["duration_seconds"] == 1.0
    assert result["sample_rate"] == 22050
    assert result["independent_model_execution_verified"] is False
    assert result["independent_human_signature_verified"] is False
    assert result["published"] is False

def test_tampered_wav_rejected(tmp_path):
    root,path=wav(tmp_path)
    with pytest.raises(ContentHold,match="digest mismatch"):
        inspect_audio_attachment(package(),asset_root=root,
            audio_filename=path.name,audio_sha256="0"*64,
            claimed_speech_job_sha256="a"*64,
            claimed_signed_review_sha256="b"*64)

def test_symlink_audio_rejected(tmp_path):
    root,path=wav(tmp_path)
    path.rename(root/"original.wav")
    path.symlink_to(root/"original.wav")
    with pytest.raises(ContentHold,match="Private bounded"):
        inspect_audio_attachment(package(),asset_root=root,
            audio_filename="spoken.wav",audio_sha256="0"*64,
            claimed_speech_job_sha256="a"*64,
            claimed_signed_review_sha256="b"*64)

def test_no_missing_signed_claim_hash(tmp_path):
    root,path=wav(tmp_path)
    with pytest.raises(ContentHold,match="evidence references"):
        inspect_audio_attachment(package(),asset_root=root,
            audio_filename="spoken.wav",
            audio_sha256=sha256(path.read_bytes()).hexdigest(),
            claimed_speech_job_sha256="a"*64,
            claimed_signed_review_sha256="missing")

def test_unapproved_script_handoff_rejected():
    with pytest.raises(ContentHold):
        prepare_narrated_campaign(
            brief(),work_order_id="metareach_october:video:youtube",
            script="short",evidence_checked=True,rights_checked=True)
