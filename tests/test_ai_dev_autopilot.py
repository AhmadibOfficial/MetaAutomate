"""Fail-closed acceptance tests for local MetaAutomate AI development."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "ai_dev_autopilot.py"
spec = importlib.util.spec_from_file_location("ai_dev_autopilot", SOURCE)
agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)


def workspace(tmp_path):
    root = tmp_path / "repo"
    path = root / "apps/site/assets/site.css"
    path.parent.mkdir(parents=True)
    path.write_text("body {color: navy;}\n")
    return root, path


def test_only_known_existing_source_paths(tmp_path):
    root, css = workspace(tmp_path)
    assert agent.target_file("apps/site/assets/site.css", root) == css
    for candidate in ["/etc/passwd", "apps/site/assets/../secrets.css",
                      "apps/site/assets/../../private.css", "apps/api/.env",
                      "apps/site/assets/new.css", ".github/workflows/ci.yml",
                      "apps/site/assets/x.yaml", "apps/site/assets\\site.css"]:
        with pytest.raises(agent.DevelopmentGateError):
            agent.target_file(candidate, root)


def test_reject_symlink_outside_source(tmp_path):
    root, _ = workspace(tmp_path)
    secret = tmp_path / "private.css"
    secret.write_text("super-secret")
    (root / "apps/site/assets/link.css").symlink_to(secret)
    with pytest.raises(agent.DevelopmentGateError):
        agent.target_file("apps/site/assets/link.css", root)


def test_generated_change_must_be_strict_and_real():
    original = "body{color:blue;}"
    good = json.dumps({"summary": "Improve color contrast", "content": "body{color:#00a7ed;}"})
    assert agent.validate_generation(good, original, ".css")[0] == "Improve color contrast"
    for value in [original, "not json", "{}", "[]",
                  '{"summary":"good summary","content":"new","content":"overwrite"}',
                  json.dumps({"summary": "improve", "content": original}),
                  json.dumps({"summary": "change", "content": ""}),
                  json.dumps({"summary": "test", "content": "updated", "script": "rm -rf /"})]:
        with pytest.raises(agent.DevelopmentGateError):
            agent.validate_generation(value, original, ".css")


def test_python_syntax_check_without_running_code():
    with pytest.raises(agent.DevelopmentGateError):
        agent.validate_generation(json.dumps({"summary": "Fix source parser", "content": "def broken(:\n pass"}), "x = 1", ".py")
    summary, _ = agent.validate_generation(json.dumps({"summary": "Fix source parser", "content": "x = 2"}), "x = 1", ".py")
    assert summary == "Fix source parser"


def test_requires_clean_main_and_approved_remote():
    with patch.object(agent, "git", side_effect=["develop"]):
        with pytest.raises(agent.DevelopmentGateError, match="main"):
            agent.require_clean_main()
    with patch.object(agent, "git", side_effect=["main", " M example.css"]):
        with pytest.raises(agent.DevelopmentGateError, match="non-clean"):
            agent.require_clean_main()
    with patch.object(agent, "git", side_effect=["main", "", "https://github.com/malicious/repo"]):
        with pytest.raises(agent.DevelopmentGateError, match="remote"):
            agent.require_clean_main()


def test_generate_uses_only_loopback_and_preview_does_not_edit(tmp_path):
    root, path = workspace(tmp_path)
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return None
        def read(self, size):
            return json.dumps({"response": json.dumps({"summary": "Improve brand blue", "content": "body {color: #00a7ed;}\n"})}).encode()
    class Opener:
        def open(self, request, timeout):
            assert request.full_url == "http://127.0.0.1:11434/api/generate"
            assert json.loads(request.data)["stream"] is False
            assert timeout == 180
            return Response()
    with patch.object(agent.urllib.request, "build_opener", return_value=Opener()):
        proposal = agent.propose("Improve the contrast for primary blue", "apps/site/assets/site.css", "qwen2.5-coder:7b", root)
    assert "00a7ed" in proposal["content"]
    assert "@@" in proposal["diff"]
    assert path.read_text() == "body {color: navy;}\n"
    assert proposal["source_sha256"]


def test_refuse_stale_proposal_before_branch(tmp_path):
    root, path = workspace(tmp_path)
    proposal = {"path": "apps/site/assets/site.css", "content": "body {color: red;}",
                "summary": "Update brand color", "source_sha256": "0" * 64}
    with patch.object(agent, "require_clean_main"):
        with patch.object(agent, "git") as git_call:
            with pytest.raises(agent.DevelopmentGateError, match="changed"):
                agent.apply_proposal(proposal, "Change the site color", root=root)
            git_call.assert_not_called()
    assert path.read_text() == "body {color: navy;}\n"


def test_no_remote_model_or_automatic_release_commands():
    source = SOURCE.read_text(encoding="utf-8")
    assert "127.0.0.1:11434" in source
    assert '"--draft"' in source
    assert "merge_pull_request" not in source
    assert "trigger_deploy" not in source
    assert "shell=True" not in source


def test_reject_bad_model_name_and_task(tmp_path):
    root, _ = workspace(tmp_path)
    with pytest.raises(agent.DevelopmentGateError):
        agent.propose("short", "apps/site/assets/site.css", "qwen", root)
    with pytest.raises(agent.DevelopmentGateError):
        agent.propose("Valid task description", "apps/site/assets/site.css", "https://server.local", root)


def test_refuse_automatic_pr_for_executable_generated_code(tmp_path):
    root, _ = workspace(tmp_path)
    py = root / "apps/api/app/sample.py"
    py.parent.mkdir(parents=True)
    py.write_text("value = 1\n")
    proposal = {"path": "apps/api/app/sample.py", "content": "value = 2\n",
                "summary": "Improve source", "source_sha256": agent.sha256(py.read_bytes()).hexdigest()}
    with patch.object(agent, "require_clean_main"):
        with patch.object(agent, "git") as git_call:
            with pytest.raises(agent.DevelopmentGateError, match="CSS-only"):
                agent.apply_proposal(proposal, "Improve source", root=root, publish=True)
            git_call.assert_not_called()
    assert py.read_text() == "value = 1\n"


def test_reject_symlinked_parent_within_repo(tmp_path):
    root, _ = workspace(tmp_path)
    other = root / "apps/api/app"
    other.mkdir(parents=True)
    (other / "foreign.css").write_text("safe")
    (root / "apps/site/assets/shortcut").symlink_to(other, target_is_directory=True)
    with pytest.raises(agent.DevelopmentGateError, match="Symlinked"):
        agent.target_file("apps/site/assets/shortcut/foreign.css", root)


def test_preview_checkout_accepts_clean_review_branch():
    trusted_origin = "https://github.com/AhmadibOfficial/MetaAutomate"
    with patch.object(agent, "git", side_effect=[
        "feature/p2-059-local-ai-development-autopilot", "", trusted_origin
    ]) as git_call:
        agent.require_clean_checkout()
        assert git_call.call_count == 3


def test_preview_refuses_detached_head():
    with patch.object(agent, "git", return_value=""):
        with pytest.raises(agent.DevelopmentGateError, match="Detached"):
            agent.require_clean_checkout()


def test_apply_still_refuses_review_branch():
    with patch.object(agent, "git", return_value="feature/p2-059-local-ai-development-autopilot"):
        with pytest.raises(agent.DevelopmentGateError, match="requires main"):
            agent.require_clean_main()
