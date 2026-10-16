"""P2-05b local one-command verification helper: no-write safety contract."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts/verify_phase02_local_gate.py"
spec = importlib.util.spec_from_file_location("phase02_local_gate", PATH)
assert spec and spec.loader
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def git_mock(monkeypatch, *, branch="feat/p2-05b-demo",
             sha="a" * 40, status=""):
    def emulate(*args):
        if args == ("branch", "--show-current"):
            return branch
        if args == ("rev-parse", "HEAD"):
            return sha
        if args == ("status", "--porcelain", "--untracked-files=normal"):
            return status
        raise AssertionError(f"Unexpected git call {args}")
    monkeypatch.setattr(gate, "_git", emulate)


def test_only_phase02_clean_feature_checkout_accepted(monkeypatch):
    git_mock(monkeypatch)
    assert gate.identify_checkout() == ("feat/p2-05b-demo", "a" * 40)


@pytest.mark.parametrize("kwargs", [
    {"branch": "main"},
    {"branch": "develop"},
    {"branch": ""},
    {"branch": "feat/random"},
    {"sha": "not-an-immutable-hash"},
    {"status": " M apps/api/app/main.py"},
    {"status": "?? private_credentials.txt"},
])
def test_dirty_or_wrong_checkouts_denied(monkeypatch, kwargs):
    git_mock(monkeypatch, **kwargs)
    with pytest.raises(gate.LocalGateError):
        gate.identify_checkout()


def test_optional_pinned_sha_mismatch_rejected(monkeypatch):
    git_mock(monkeypatch)
    with pytest.raises(gate.LocalGateError):
        gate.identify_checkout("b" * 40)


def test_local_tests_are_phase02_only():
    paths = gate.select_tests()
    assert paths
    assert all(p.parent.name == "tests"
               and p.name.startswith("test_phase02_")
               and p.suffix == ".py" for p in paths)


def test_runner_invokes_offline_pytest_and_prints_readable_result(
    monkeypatch, capsys,
):
    git_mock(monkeypatch)
    calls = []
    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(gate.subprocess, "run", fake_run)
    assert gate.run_local_gate("a" * 40) == 0
    assert len(calls) == 1
    cmd, opts = calls[0]
    assert cmd[:3] == [gate.sys.executable, "-m", "pytest"]
    assert "no:cacheprovider" in cmd
    assert "--import-mode=importlib" in cmd
    assert "apps/api" in opts["env"]["PYTHONPATH"]
    assert opts["env"]["PYTHONDONTWRITEBYTECODE"] == "1"
    assert opts["cwd"] == ROOT
    assert opts["timeout"] <= 180
    out = capsys.readouterr().out
    assert "PHASE02_RESULT=PASS" in out
    assert "PHASE01_FOUNDATION=3/9_NO_GO" in out
    assert "MERGE_PERMITTED=false" in out


def test_pytest_failure_reports_failure_not_false_success(monkeypatch, capsys):
    git_mock(monkeypatch)
    monkeypatch.setattr(gate.subprocess, "run",
                        lambda *a, **kw: SimpleNamespace(returncode=1))
    assert gate.run_local_gate() == 1
    assert "PHASE02_RESULT=FAIL" in capsys.readouterr().out


def test_helper_does_not_contain_merge_deploy_or_net_fetch_commands():
    source = PATH.read_text(encoding="utf-8")
    for forbidden in (
        "git push", "git merge ", "git fetch ", "git pull ",
        "docker compose", "kubectl ", "requests.", "httpx.",
        "terraform apply", "gh pr merge", "pip install ",
    ):
        assert forbidden not in source
