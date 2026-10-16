"""F04 governance tests: no mocked or unreviewed source can assert release GO."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"scripts/inspect_f04_github_protection.py"
spec=importlib.util.spec_from_file_location("f04_inspector",PATH)
f04=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=f04
spec.loader.exec_module(f04)


def good():
    branch={"name":"main","protected":True}
    protection={
        "required_status_checks":{"strict":True,"contexts":["Release Evidence Gate"],
                                  "checks":[{"context":"Release Evidence Gate"}]},
        "required_pull_request_reviews":{"required_approving_review_count":1,
                                         "dismiss_stale_reviews":True},
        "enforce_admins":{"enabled":True},
        "allow_force_pushes":{"enabled":False},
        "allow_deletions":{"enabled":False},
        "required_conversation_resolution":{"enabled":True},
    }
    return branch,protection


def test_offline_never_grants_f04():
    result=f04.inspect()
    assert result["status"]=="NO_LIVE_VERIFICATION"
    assert result["github_branch_rule_enforced"] is False
    assert result["foundation_f04_verified"] is False
    assert result["release_authorized"] is False
    assert result["deployment_authorized"] is False
    assert result["repository_visibility_must_remain_private"] is True


def test_no_token_does_not_call_network(monkeypatch):
    monkeypatch.setattr(f04,"get_json",lambda *_:pytest.fail("Network forbidden"))
    assert f04.inspect(live=True,token="")["status"]=="BLOCKED"


def test_unprotected_private_main_is_blocked():
    branch,protection=good()
    branch["protected"]=False
    errors=f04.fail_reasons(branch,protection)
    assert "main_branch_is_not_protected" in errors
    assert "branch_protection_configuration_unreadable" in f04.fail_reasons(branch,None)


@pytest.mark.parametrize("change,expected",[
    (lambda p:p["required_status_checks"].update({"contexts":[],"checks":[]}),
     "release_evidence_gate_not_required"),
    (lambda p:p["required_status_checks"].update({"strict":False}),
     "required_checks_must_be_current"),
    (lambda p:p.update({"required_status_checks":None}),
     "required_checks_not_configured"),
    (lambda p:p.update({"required_pull_request_reviews":None}),
     "independent_pull_request_review_not_required"),
    (lambda p:p["required_pull_request_reviews"].update({"required_approving_review_count":0}),
     "independent_pull_request_review_not_required"),
    (lambda p:p["required_pull_request_reviews"].update({"dismiss_stale_reviews":False}),
     "stale_reviews_not_dismissed"),
    (lambda p:p["enforce_admins"].update({"enabled":False}),
     "administrators_may_bypass_rules"),
    (lambda p:p["allow_force_pushes"].update({"enabled":True}),
     "force_push_state_not_explicitly_disabled"),
    (lambda p:p["allow_deletions"].update({"enabled":True}),
     "branch_deletion_state_not_explicitly_disabled"),
    (lambda p:p["required_conversation_resolution"].update({"enabled":False}),
     "review_conversation_resolution_not_required"),
])
def test_every_release_requirement_must_be_present(change,expected):
    b,p=good()
    change(p)
    assert expected in f04.fail_reasons(b,p)


def test_correct_configuration_still_needs_independent_merge_denial(monkeypatch):
    branch,protection=good()
    seen=[]
    def fake_fetch(path,_):
        seen.append(path)
        return branch if path=="/branches/main" else protection
    monkeypatch.setattr(f04,"get_json",fake_fetch)
    result=f04.inspect(live=True,token="test")
    assert seen==["/branches/main","/branches/main/protection"]
    assert result["status"]=="CONFIGURATION_CONFIRMED_INDEPENDENT_PROOF_PENDING"
    assert result["github_branch_rule_enforced"] is True
    assert result["foundation_f04_verified"] is False
    assert result["blocked_merge_negative_test_verified"] is False
    assert result["release_authorized"] is False


def test_live_unprotected_never_requests_admin_config(monkeypatch):
    seen=[]
    def fake_fetch(path,_):
        seen.append(path)
        return {"name":"main","protected":False}
    monkeypatch.setattr(f04,"get_json",fake_fetch)
    result=f04.inspect(live=True,token="test")
    assert result["status"]=="BLOCKED"
    assert seen==["/branches/main"]
    assert not result["github_branch_rule_enforced"]


def test_api_403_fails_closed(monkeypatch):
    from urllib.error import HTTPError
    def forbidden(*_):
        raise HTTPError("https://api.github.com",403,"Not accessible",{},None)
    monkeypatch.setattr(f04,"get_json",forbidden)
    result=f04.inspect(live=True,token="test")
    assert result["status"]=="BLOCKED"
    assert "HTTP 403" in result["reasons"][0]
    assert result["foundation_f04_verified"] is False


def test_refuses_live_release_even_with_green_fixture(tmp_path,monkeypatch):
    b,p=good()
    monkeypatch.setattr(f04,"get_json",lambda path,_: b if path=="/branches/main" else p)
    monkeypatch.setenv("F04_GITHUB_READ_TOKEN","not-a-secret")
    file=tmp_path/"report.json"
    assert f04.main(["--live","--require-enforced","--report",str(file)])==1
    assert __import__("json").loads(file.read_text())["release_authorized"] is False
