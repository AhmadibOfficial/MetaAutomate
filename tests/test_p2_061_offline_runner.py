"""Source-only acceptance for the read-only offline CI fallback runner."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "scripts/verify_p2_061_offline.py"


def load():
    spec = importlib.util.spec_from_file_location("verify_p2_061_offline", FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runner_discloses_no_release_authorization():
    runner = load()
    assert runner.GATE == "LOCAL_SOURCE_CHECK_ONLY"
    source = FILE.read_text(encoding="utf-8")
    assert '"github_ci_verified": False' in source
    assert '"deployment_approved": False' in source
    assert '"merge_approved": False' in source
    for forbidden in ("merge_pull_request", "trigger_deploy",
                      "git push", "DROP DATABASE", "ALTER ROLE"):
        assert forbidden not in source


def test_dirty_worktree_is_blocked_before_running_tests(monkeypatch):
    runner = load()
    def fake_git(*args):
        key = args[0]
        if key == "rev-parse":
            return str(runner.ROOT) if "--show-toplevel" in args else "a" * 40
        if key == "branch":
            return "feature/p2-061-secure-business-data-lab"
        if key == "status":
            return " M apps/api/app/main.py"
        raise AssertionError("Unexpected git operation")
    monkeypatch.setattr(runner, "_git", fake_git)
    with patch.object(runner, "command") as execute:
        report = runner.generate_report()
        execute.assert_not_called()
    assert report["result"] == "BLOCKED"
    assert report["github_ci_verified"] is False


def test_clean_checkout_runs_source_tests_without_claiming_production(monkeypatch, tmp_path):
    runner = load()
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    all_sources = (*runner.SOURCE_FILES, *runner.TEST_FILES, *runner.NODE_FILES,
                   runner.CAMPAIGN_TEST)
    for name in all_sources:
        file = tmp_path / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("# offline fake fixture\n")
    def fake_git(*args):
        if "--show-toplevel" in args:
            return str(tmp_path)
        if args[0] == "rev-parse":
            return "a" * 40
        if args[0] == "branch":
            return "feature/p2-061-secure-business-data-lab"
        if args[0] == "status":
            return ""
        raise AssertionError("Unexpected git operation")
    monkeypatch.setattr(runner, "_git", fake_git)
    monkeypatch.setattr(runner, "validate_source", lambda: {"status": "PASS"})
    monkeypatch.setattr(runner, "command", lambda *a, **k: {"status": "PASS"})
    monkeypatch.setattr(runner.shutil, "which", lambda binary: "/usr/bin/node")
    report = runner.generate_report()
    assert report["result"] == "LOCAL_TESTS_PASS"
    assert report["github_ci_verified"] is False
    assert report["merge_approved"] is False
    assert report["deployment_approved"] is False
    assert report["working_tree_unchanged"] is True
    assert len(report["tests"]) == 6


def test_missing_node_is_blocked_not_considered_pass(monkeypatch, tmp_path):
    runner = load()
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    for name in (*runner.SOURCE_FILES, *runner.TEST_FILES, *runner.NODE_FILES,
                 runner.CAMPAIGN_TEST):
        file = tmp_path / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text("fixture")
    monkeypatch.setattr(runner, "_git", lambda *args:
        str(tmp_path) if "--show-toplevel" in args else
        "a" * 40 if args[0] == "rev-parse" else
        "feature/p2-061" if args[0] == "branch" else "")
    monkeypatch.setattr(runner, "validate_source", lambda: {"status": "PASS"})
    monkeypatch.setattr(runner, "command", lambda *a, **k: {"status": "PASS"})
    monkeypatch.setattr(runner.shutil, "which", lambda binary: None)
    report = runner.generate_report()
    assert report["result"] == "BLOCKED_OR_FAILED"
    assert report["tests"]["node_runtime"]["status"] == "BLOCKED"
