"""P2-04v voice tests: PCM fixtures are tones, NEVER real intelligible speech."""
from array import array
from pathlib import Path
import math
import struct
import wave

import pytest

from app.creative_voice_quality import (
    VoiceQualityHold, inspect_narration_pcm, require_technically_ready_narration,
    word_error_rate,
)

SCRIPT="This is a simple educational narration explaining practical business workflows."

def wav(tmp_path,*,sections=(("tone",4.0),),rate=22050,amplitude=3200):
    root=tmp_path/"private"
    root.mkdir(mode=0o700)
    path=root/"narration.wav"
    with wave.open(str(path),"wb") as writer:
        writer.setnchannels(1); writer.setsampwidth(2); writer.setframerate(rate)
        for kind,seconds in sections:
            size=int(seconds*rate)
            if kind=="tone":
                signal=(
                    struct.pack("<h",int(amplitude*math.sin(2*math.pi*220*i/rate)))
                    for i in range(size))
            else:
                signal=(b"\x00\x00" for _ in range(size))
            # Explicit synthetic data: unspoken sine wave, not an AI narrator.
            writer.writeframes(b"".join(signal))
    path.chmod(0o600)
    return path

def test_healthy_pcm_is_never_automatically_accepted(tmp_path):
    path=wav(tmp_path)
    result=inspect_narration_pcm(path,SCRIPT,transcript=SCRIPT)
    assert result["technical_checks_passed"] is True
    assert result["status"]=="HOLD_INDEPENDENT_SIGNED_LISTENING_REVIEW"
    assert result["acoustic_intelligibility_proven"] is False
    assert result["signed_human_listening_review_proven"] is False
    assert result["publication_authorized"] is False

def test_three_second_middle_gap_fails_quality_gate(tmp_path):
    path=wav(tmp_path,sections=(("tone",2),("silence",3),("tone",2)))
    report=inspect_narration_pcm(path,SCRIPT)
    assert "EXCESSIVE_MID_SENTENCE_SILENCE" in report["technical_issues"]
    with pytest.raises(VoiceQualityHold,match="technically unsuitable"):
        require_technically_ready_narration(path,SCRIPT)

def test_long_trailing_silence_rejected(tmp_path):
    path=wav(tmp_path,sections=(("tone",3),("silence",2)))
    report=inspect_narration_pcm(path,SCRIPT)
    assert "EXCESSIVE_END_SILENCE" in report["technical_issues"]

def test_all_silence_is_not_speech(tmp_path):
    path=wav(tmp_path,sections=(("silence",4),))
    report=inspect_narration_pcm(path,SCRIPT)
    assert "NO_AUDIBLE_SPEECH" in report["technical_issues"]
    assert report["technical_checks_passed"] is False

def test_clipped_waveform_rejected(tmp_path):
    path=wav(tmp_path,amplitude=32767)
    report=inspect_narration_pcm(path,SCRIPT)
    assert ("POSSIBLE_CLIPPING" in report["technical_issues"]
            or "INSUFFICIENT_SAMPLE_PEAK_HEADROOM" in report["technical_issues"])

def test_overspeed_script_rejected(tmp_path):
    path=wav(tmp_path,sections=(("tone",2),))
    rapid=" ".join(["word"]*25)
    report=inspect_narration_pcm(path,rapid)
    assert "SCRIPT_MAY_BE_RUSHED" in report["technical_issues"]

def test_piper_native_22050_pcm_is_supported(tmp_path):
    path=wav(tmp_path,rate=22050)
    assert inspect_narration_pcm(path,SCRIPT)["sample_rate"]==22050

def test_transcript_word_mismatch_blocks(tmp_path):
    path=wav(tmp_path)
    report=inspect_narration_pcm(
        path,SCRIPT,transcript="Completely unrelated spoken message different words.")
    assert "TRANSCRIPT_WORD_MISMATCH" in report["technical_issues"]

def test_word_error_rate_computation_is_exact():
    result=word_error_rate("Clear spoken words matter",
                           "Clear spoken words matter")
    assert result["word_error_rate"]==0
    assert result["transcript_source_independently_authenticated"] is False
    assert word_error_rate("one two three four","one two five four")["word_error_rate"]==0.25

def test_group_readable_audio_is_rejected(tmp_path):
    path=wav(tmp_path)
    path.chmod(0o644)
    with pytest.raises(VoiceQualityHold,match="Private absolute"):
        inspect_narration_pcm(path,SCRIPT)

def test_no_file_symlink_is_accepted(tmp_path):
    path=wav(tmp_path)
    original=path.with_name("original.wav")
    path.rename(original)
    path.symlink_to(original)
    with pytest.raises(VoiceQualityHold,match="Private absolute"):
        inspect_narration_pcm(path,SCRIPT)
