"""Phase 03 one-command acceptance helper failure mode and exact-SHA tests."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_phase03_local_gate.py"
spec = importlib.util.spec_from_file_location("p3_local_gate", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

HEAD = "1" * 40


def fake_git(monkeypatch, *, branch="feat/p3-test", sha=HEAD, dirty=""):
    values = {
        ("branch", "--show-current"): branch,
        ("rev-parse", "HEAD"): sha,
        ("status", "--porcelain", "--untracked-files=normal"): dirty,
    }
    monkeypatch.setattr(module, "_git", lambda *args: values[args])


def test_correct_clean_feature_head(monkeypatch):
    fake_git(monkeypatch)
    assert module.identify(HEAD) == ("feat/p3-test", HEAD)


@pytest.mark.parametrize("branch,sha,dirty", [
    ("main", HEAD, ""),
    ("feat/p2-old", HEAD, ""),
    ("", HEAD, ""),
    ("feat/p3-test", "2"*40, ""),
    ("feat/p3-test", HEAD, " M customer.csv"),
    ("feat/p3-test", HEAD, "?? credentials.txt"),
])
def test_wrong_branch_sha_or_dirty_checkout_rejected(monkeypatch, branch, sha, dirty):
    fake_git(monkeypatch, branch=branch, sha=sha, dirty=dirty)
    with pytest.raises(module.SourceGateDenied):
        module.identify(HEAD)


@pytest.mark.parametrize("invalid", [
    "HEAD", "1"*39, "f"*41, None, True,
])
def test_invalid_sha_arg_rejected(monkeypatch, invalid):
    fake_git(monkeypatch)
    with pytest.raises(module.SourceGateDenied):
        module.identify(invalid)


def test_source_gate_does_not_have_checkout_or_network_actions():
    src = SCRIPT.read_text()
    assert '"git", "-C", str(ROOT), *args' in src
    assert "check=True" in src
    assert '"--untracked-files=normal"' in src
    assert "pytest" in src
    for forbidden in (
        'fetch', 'checkout', 'merge', 'push', 'deploy',
        'APIRouter(', 'requests.', 'httpx.', 'urllib.', 'urlopen(',
    ):
        # Permitted words in docs (e.g. 'does not fetch') are not executable;
        # disallow only known command invocations.
        if forbidden in ("fetch", "checkout", "merge", "push", "deploy"):
            assert f'_git("{forbidden}"' not in src
        else:
            assert forbidden not in src
