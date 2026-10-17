"""P2-04q operator wrapper must never initialize a fake model by default."""
import json

from app.creative_speech_operator_acceptance import main

def test_operator_cli_fails_closed_without_isolation(tmp_path,monkeypatch,capsys):
    monkeypatch.delenv("MAT_SPEECH_OPERATOR_ISOLATION_EVIDENCE_CONFIRMED",raising=False)
    code=main([
        "--job",str(tmp_path/"missing-job.json"),
        "--authorization",str(tmp_path/"missing-auth.json"),
        "--text",str(tmp_path/"missing-text.txt"),
        "--voice-onnx",str(tmp_path/"missing-voice.onnx"),
        "--piper-bin",str(tmp_path/"missing-piper"),
        "--quarantine",str(tmp_path),
        "--owner-public-key","no_trust",
        "--reviewer-public-key","no_trust",
    ])
    assert code==2
    assert "SPEECH ACCEPTANCE HOLD" in capsys.readouterr().err

def test_operator_cli_requires_real_private_inputs(tmp_path,monkeypatch,capsys):
    monkeypatch.setenv("MAT_SPEECH_OPERATOR_ISOLATION_EVIDENCE_CONFIRMED","1")
    job=tmp_path/"job.json"
    job.write_text(json.dumps({"not":"an approved job"}))
    job.chmod(0o600)
    code=main([
        "--job",str(job),
        "--authorization",str(tmp_path/"missing-auth.json"),
        "--text",str(tmp_path/"missing-text.txt"),
        "--voice-onnx",str(tmp_path/"missing-voice.onnx"),
        "--piper-bin",str(tmp_path/"missing-piper"),
        "--quarantine",str(tmp_path),
        "--owner-public-key","no_trust",
        "--reviewer-public-key","no_trust",
    ])
    assert code==2
    assert "SPEECH ACCEPTANCE HOLD" in capsys.readouterr().err
