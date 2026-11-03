"""Deterministic negative tests for AI-assisted development preflight."""
from pathlib import Path
import importlib.util
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
SCANNER=ROOT/"scripts/ai_security_preflight.py"
spec=importlib.util.spec_from_file_location("ai_preflight",SCANNER)
guard=importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

def test_restrict_sensitive_files():
    for p in (".env","apps/api/.env.production","secrets/x",
              "credentials/x","private.pem",".npmrc","nested/settings.local.json"):
        assert guard.inspect(p,b"clean") != [],p
    assert guard.inspect("src/safe.py",b"print('safe')")==[]

def test_recognize_secret_signatures():
    examples=[
        ("-----BEGIN PRIVATE KEY-----","private_key"),
        ("ghp_"+"A"*30,"github_token"),
        ("AKIA"+"A"*16,"aws_access_key"),
        ("AIza"+"A"*35,"google_api_key"),
        ("sk-proj-"+"X"*30,"openai_key"),
        ('api_key = "'+"Y"*24+'"',"secret_assignment")
    ]
    for value,rule in examples:
        assert any(item[0]==rule for item in guard.inspect("x.py",value.encode())),rule

def test_no_false_alarm_on_synthetic_and_fail_closed():
    assert guard.inspect("a.py",b'api_key = "synthetic_placeholder"')==[]
    assert guard.inspect("a.py",b"x"*(guard.MAX_BYTES+1))[0][0]=="oversize_uninspected"
    assert guard.inspect("a.py",b"\xff")[0][0]=="invalid_utf8"

def test_cli_rejects_invalid_base_without_leaking_command_output():
    p=subprocess.run([sys.executable,str(SCANNER),"--base","invalid"],
                     cwd=ROOT,capture_output=True,text=True)
    assert p.returncode==2
    assert "preflight failed" in p.stderr.lower()
    assert "Traceback" not in p.stderr

def test_security_files_and_standalone_gates():
    for path in (".claude/settings.json",".codex/config.toml",
                 ".githooks/pre-commit",".github/workflows/ai-security.yml",
                 "docs/security/AI_ASSISTED_DEVELOPMENT_SECURITY.md"):
        assert (ROOT/path).is_file()
