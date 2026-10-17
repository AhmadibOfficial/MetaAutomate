"""Local source-gate harness checks; deliberately no licensed model inference."""
import subprocess
from pathlib import Path
from scripts.verify_p2_04q_local_gate import TESTS, run_gate

def _git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def test_local_source_gate_can_issue_reproducible_fixture_evidence(tmp_path):
    root = tmp_path / "fixture-checkout"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Fixture Tester")
    _git(root, "config", "user.email", "fixture@example.invalid")
    for test in TESTS:
        path = root / test
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("def test_source_fixture_only(): assert True\n")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "non-AI runner fixture")
    head = _git(root, "rev-parse", "HEAD")
    evidence = tmp_path / "evidence"
    evidence.mkdir(mode=0o700)
    report = run_gate(root, head, evidence)
    assert report["source_test_result"] == "SOURCE_TESTS_PASS_ONLY"
    assert report["github_required_checks_satisfied"] is False
    assert report["real_piper_inference_verified"] is False
    assert (evidence / "p2-04q-local-evidence.json").exists()
    assert (evidence / "p2-04q-local-test.log").exists()

def test_mismatched_source_sha_must_block(tmp_path):
    root = tmp_path / "fixture-checkout"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.name", "Fixture Tester")
    _git(root, "config", "user.email", "fixture@example.invalid")
    (root / "README.md").write_text("fixture")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    evidence = tmp_path / "private"
    evidence.mkdir(mode=0o700)
    result = run_gate(root, "0"*40, evidence)
    assert result["source_test_result"] == "HOLD_NOT_EXECUTED"
    assert result["tests_executed"] is False
    assert result["release_authorized"] is False
