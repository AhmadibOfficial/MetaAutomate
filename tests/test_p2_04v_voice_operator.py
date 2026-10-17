"""P2-04v verify operator blocks audio-quality failures before final rendering."""
import json
import math
from pathlib import Path
import struct
import wave

import pytest

from app import creative_multimodal_operator as operator
from app.creative_voice_quality import VoiceQualityHold

def _case(tmp_path,monkeypatch,*,missing_review=False,bad_audio=True):
    asset_root=tmp_path/"private_assets"
    asset_root.mkdir(mode=0o700)
    voice=asset_root/"narration.wav"
    with wave.open(str(voice),"wb") as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(22050)
        seconds=[("tone",2),("silence",3),("tone",2)] if bad_audio else [("tone",6)]
        for kind,length in seconds:
            content=(struct.pack("<h",int(2800*math.sin(2*math.pi*220*i/22050)))
                     if kind=="tone" else b"\x00\x00"
                     for i in range(length*22050))
            wav.writeframes(b"".join(content))
    voice.chmod(0o600)
    script=asset_root/"script.txt"
    script.write_text("Clear, accurate narration for the MetaAutomate educational film.")
    script.chmod(0o600)
    transcript=asset_root/"recognized.txt"
    transcript.write_text(script.read_text())
    transcript.chmod(0o600)
    docs={
        "manifest.json":{"voice":{"file":"narration.wav"}},
        "source.json":{"sources":{}},
        "keys.json":{},
    }
    for name,value in docs.items():
        path=asset_root/name
        path.write_text(json.dumps(value))
        path.chmod(0o600)
    monkeypatch.setattr(operator,"_pinned_checkout",lambda *args:None)
    render_calls=[]
    monkeypatch.setattr(operator,"verify_source_bundle",
                        lambda *args,**kwargs: {"status":"SIGNED_FIXTURE"})
    monkeypatch.setattr(operator,"render_with_source_proofs",
                        lambda *args,**kwargs: render_calls.append(True) or {
                            "final_sha256":"0"*64,"published":False,
                            "publication_authorized":False})
    args=[
        "--repo-root",str(asset_root),
        "--expected-commit","a"*40,
        "--manifest",str(asset_root/"manifest.json"),
        "--source-evidence",str(asset_root/"source.json"),
        "--trusted-reviewer-keys",str(asset_root/"keys.json"),
        "--assets",str(asset_root),"--quarantine",str(asset_root),
        "--render",
    ]
    if not missing_review:
        args+=["--approved-script",str(script),
               "--recognized-transcript",str(transcript)]
    return args,render_calls

def test_missing_transcript_blocks_render(tmp_path,monkeypatch,capsys):
    args,calls=_case(tmp_path,monkeypatch,missing_review=True)
    assert operator.main(args)==2
    assert not calls
    assert "reviewed script" in capsys.readouterr().err

def test_three_second_gap_blocks_final_film(tmp_path,monkeypatch,capsys):
    args,calls=_case(tmp_path,monkeypatch,bad_audio=True)
    assert operator.main(args)==2
    assert not calls
    assert "EXCESSIVE_MID_SENTENCE_SILENCE" in capsys.readouterr().err

def test_good_pcm_still_does_not_claim_human_intelligibility(tmp_path,monkeypatch,capsys):
    args,calls=_case(tmp_path,monkeypatch,bad_audio=False)
    assert operator.main(args)==0
    assert calls==[True]
    output=json.loads(capsys.readouterr().out)
    assert output["published"] is False
    assert output["narration_technical_quality"]["technical_checks_passed"] is True
    assert output["narration_technical_quality"]["signed_human_listening_review_proven"] is False
    assert output["narration_technical_quality"]["natural_neural_voice_proven"] is False
