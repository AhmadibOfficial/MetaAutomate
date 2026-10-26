"""Offline QDB evidence gate: fixture repos only, no cloud or investor submission."""
from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/qdb_start_readiness.py"
spec = importlib.util.spec_from_file_location("qdb_start_readiness", SCRIPT)
qdb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qdb)


def git(path, *args):
    r = subprocess.run(["git", *args], cwd=path, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "tester@example.invalid")
    git(root, "config", "user.name", "Offline Test")
    root.joinpath(qdb.FOUNDATION).parent.mkdir(parents=True)
    payload = {"policy": "NO_GO_UNTIL_ALL_NINE_VERIFIED", "checks": [
        {"id": f"F{i:02}", "status": "verified" if i <= 3 else "blocked",
         "source_path": f"docs/operational-core/fixture-F{i:02}.md" if i <= 3 else "",
         "reason": "Fixture-only committed source" if i <= 3 else "Blocked in fixture"}
        for i in range(1, 10)
    ]}
    root.joinpath(qdb.FOUNDATION).write_text(json.dumps(payload))
    for paths in qdb.CAPABILITIES.values():
        for path in paths:
            p = root / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("# fixture\n")
    for i in range(1, 4):
        (root / f"docs/operational-core/fixture-F{i:02}.md").write_text(
            f"# Fixture source F{i:02} (not an acceptance certificate)\\n"
        )
    git(root, "add", ".")
    git(root, "commit", "-qm", "Fictional offline evidence fixtures")
    return root


def test_source_index_never_reports_operational_eligibility(repo):
    x = qdb.assess(repo)
    assert x["foundation"]["verified_count"] == 3
    assert x["foundation"]["blocked_count"] == 6
    assert x["foundation"]["status"] == "OPERATIONAL_NO_GO"
    assert all(v["source_presence"] == "SOURCE_FILES_PRESENT" for v in x["capabilities"].values())
    assert all(v["publicly_operational"] is False for v in x["capabilities"].values())
    assert x["eligibility_verified"] is False
    assert x["revenue_verified"] is False
    assert x["customer_traction_verified"] is False
    assert x["application_submitted"] is False
    assert x["independent_ci_verified"] is False
    assert x["investment_requested_usd"] is None
    assert len(x["qdb_start_readiness"]) == 8
    assert x["synthetic_functional_demo"] == {"status": "NOT_RUN", "independently_verified": False}


def test_missing_technical_module_marked_incomplete_not_live(repo):
    missing = repo / qdb.CAPABILITIES["creative_images_video"][0]
    missing.unlink()
    git(repo, "add", "-u")
    git(repo, "commit", "-qm", "Remove fictional source module")
    x = qdb.assess(repo)
    assert x["capabilities"]["creative_images_video"]["source_presence"] == "SOURCE_INCOMPLETE"
    assert x["capabilities"]["creative_images_video"]["missing_source_paths"]


def test_uncommitted_work_refused_without_changing_it(repo):
    path = repo / qdb.CAPABILITIES["data_research"][0]
    path.write_text("# in progress\n")
    before = path.read_bytes()
    with pytest.raises(qdb.ReadinessError, match="uncommitted"):
        qdb.assess(repo)
    assert path.read_bytes() == before


def test_missing_foundation_and_bad_policy_fail_closed(repo):
    f = repo / qdb.FOUNDATION
    data = json.loads(f.read_text())
    data["policy"] = "GO"
    f.write_text(json.dumps(data))
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "Bad fixture policy")
    with pytest.raises(qdb.ReadinessError, match="NO-GO"):
        qdb.assess(repo)


def test_verified_foundation_source_missing_is_rejected(repo):
    evidence = repo / qdb.FOUNDATION
    data = json.loads(evidence.read_text())
    data["checks"][0]["source_path"] = "docs/operational-core/nonexistent-proof.md"
    evidence.write_text(json.dumps(data))
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "Fixture: missing claimed foundation source")
    with pytest.raises(qdb.ReadinessError, match="regular committed source"):
        qdb.assess(repo)


def test_new_verified_status_without_source_is_rejected(repo):
    evidence = repo / qdb.FOUNDATION
    data = json.loads(evidence.read_text())
    data["checks"][3]["status"] = "verified"
    data["checks"][3]["reason"] = "Source not supplied"
    evidence.write_text(json.dumps(data))
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "Fixture: unsupported promotion")
    with pytest.raises(qdb.ReadinessError, match="F04"):
        qdb.assess(repo)


def test_verified_foundation_rationale_must_not_be_blank(repo):
    evidence = repo / qdb.FOUNDATION
    data = json.loads(evidence.read_text())
    data["checks"][0]["reason"] = "   "
    evidence.write_text(json.dumps(data))
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "Fixture: no evidence rationale")
    with pytest.raises(qdb.ReadinessError, match="evidence rationale"):
        qdb.assess(repo)


def test_verified_foundation_source_symlink_is_rejected(repo, tmp_path):
    external = tmp_path / "outside-commit.md"
    external.write_text("Not a committed repository evidence file\\n")
    path = repo / "docs/operational-core/fixture-F01.md"
    path.unlink()
    path.symlink_to(external)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "Fixture: symlink instead of committed evidence")
    with pytest.raises(qdb.ReadinessError, match="regular committed source"):
        qdb.assess(repo)


def _local_report(repo, path, **changes):
    data = {"gate": "LOCAL_SOURCE_CHECK_ONLY", "commit": git(repo, "rev-parse", "HEAD"),
            "result": "LOCAL_TESTS_PASS", "github_ci_verified": False,
            "merge_approved": False, "deployment_approved": False}
    data.update(changes)
    path.write_text(json.dumps(data))
    return path


def test_local_test_report_is_explicitly_unattested(repo, tmp_path):
    path = _local_report(repo, tmp_path / "test.json")
    result = qdb.assess(repo, local_report=path)
    assert result["local_validation"]["status"] == "DEVELOPER_REPORTED_LOCAL_TESTS_PASS"
    assert result["local_validation"]["independently_verified"] is False
    assert result["independent_ci_verified"] is False


@pytest.mark.parametrize("alter", [
    {"commit": "0" * 40},
    {"github_ci_verified": True},
    {"merge_approved": True},
    {"deployment_approved": True},
    {"result": "EVERYTHING_APPROVED"},
])
def test_wrong_commit_or_false_approvals_refused(repo, tmp_path, alter):
    path = _local_report(repo, tmp_path / "evidence.json", **alter)
    with pytest.raises(qdb.ReadinessError):
        qdb.assess(repo, local_report=path)


def test_report_inside_repo_refused(repo):
    with pytest.raises(qdb.ReadinessError):
        qdb._write_new(repo, repo / "report.json", b"{}")
    assert not (repo / "report.json").exists()


def test_private_new_file_only_no_overwrite(repo, tmp_path):
    out = tmp_path / "report.json"
    qdb._write_new(repo, out, b"{}")
    assert out.read_bytes() == b"{}"
    assert (out.stat().st_mode & 0o077) == 0
    with pytest.raises(FileExistsError):
        qdb._write_new(repo, out, b"changed")
    assert out.read_bytes() == b"{}"


def test_source_script_no_network_external_submission_or_payments():
    src = SCRIPT.read_text()
    for forbidden in ("requests.post", "urllib.request", "httpx.post", "webbrowser.open",
                      "subprocess.Popen", "git push", "git merge", "f6s.com/api"):
        assert forbidden not in src


def test_symlinked_capability_source_cannot_count_as_committed_evidence(repo, tmp_path):
    """Git commits symlink paths; external contents are not source proof."""
    external = tmp_path / "untracked-outside.js"
    external.write_text("// not a repository source\n")
    name = qdb.CAPABILITIES["data_research"][0]
    source = repo / name
    source.unlink()
    source.symlink_to(external)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "Fixture: tracked symlink to outside file")
    result = qdb.assess(repo)
    assert result["capabilities"]["data_research"]["source_presence"] == "SOURCE_INCOMPLETE"
    assert name in result["capabilities"]["data_research"]["missing_source_paths"]


def test_symlinked_foundation_record_is_rejected(repo, tmp_path):
    """A tracked symlink cannot import an external NO-GO record as evidence."""
    source = repo / qdb.FOUNDATION
    external = tmp_path / "external-foundation.json"
    external.write_bytes(source.read_bytes())
    source.unlink()
    source.symlink_to(external)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "Fixture: external Foundation record symlink")
    with pytest.raises(qdb.ReadinessError, match="symlinked"):
        qdb.assess(repo)


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js unavailable")
def test_opt_in_synthetic_campaign_demo_runs_real_committed_engine(repo):
    """Actual deterministic functionality, but not CI or customer proof."""
    source = SCRIPT.parents[1] / qdb.CAPABILITIES["data_research"][0]
    target = repo / qdb.CAPABILITIES["data_research"][0]
    target.write_bytes(source.read_bytes())
    git(repo, "add", qdb.CAPABILITIES["data_research"][0])
    git(repo, "commit", "-qm", "Add genuine engine to synthetic fixture repo")
    result = qdb.assess(repo, run_synthetic_demo=True)
    evidence = result["synthetic_functional_demo"]
    assert evidence["status"] == "DEVELOPER_LOCAL_SYNTHETIC_PASS"
    assert evidence["independently_verified"] is False
    assert evidence["browser_e2e_verified"] is False
    assert evidence["commercial_traction_verified"] is False
    assert result["release_approved"] is False


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js unavailable")
def test_opt_in_synthetic_demo_rejects_placeholder_engine(repo):
    with pytest.raises(qdb.ReadinessError, match="demonstration failed"):
        qdb.assess(repo, run_synthetic_demo=True)


def test_opt_in_synthetic_demo_rejects_symlinked_engine(repo, tmp_path):
    path = qdb.CAPABILITIES["data_research"][0]
    source = repo / path
    external = tmp_path / "external-engine.js"
    external.write_text(source.read_text())
    source.unlink()
    source.symlink_to(external)
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "Symlinked demo engine fixture")
    with pytest.raises(qdb.ReadinessError, match="regular committed"):
        qdb.assess(repo, run_synthetic_demo=True)
