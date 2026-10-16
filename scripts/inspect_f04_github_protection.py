#!/usr/bin/env python3
"""F04: read-only, fail-closed verification of GitHub private main protection.

Default: offline source review only; NEVER claims enforced protection.
--live: uses F04_GITHUB_READ_TOKEN, requires GitHub live REST proof, but still
returns REVIEW_REQUIRED until independently tested blocked merge is supplied.
This script NEVER modifies GitHub, grants access, or creates a release token.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO="AhmadibOfficial/MetaAutomate"
BRANCH="main"
REQUIRED_CHECK="Release Evidence Gate"
ORIGIN="https://api.github.com/repos/"+REPO
DEFAULT_REPORT=Path("artifacts/validation/f04-github-release-protection.json")


def fail_reasons(branch:dict, protection:dict|None=None)->list[str]:
    problems=[]
    if type(branch) is not dict or branch.get("name")!=BRANCH:
        return ["branch_metadata_unavailable"]
    if branch.get("protected") is not True:
        problems.append("main_branch_is_not_protected")
    if type(protection) is not dict:
        problems.append("branch_protection_configuration_unreadable")
        return problems
    required=protection.get("required_status_checks")
    if type(required) is not dict:
        problems.append("required_checks_not_configured")
    else:
        names={c for c in required.get("contexts",[]) if type(c) is str} if type(
            required.get("contexts")) is list else set()
        items=required.get("checks")
        if type(items) is list:
            names |= {x["context"] for x in items if type(x) is dict
                      and type(x.get("context")) is str}
        if REQUIRED_CHECK not in names:
            problems.append("release_evidence_gate_not_required")
        if required.get("strict") is not True:
            problems.append("required_checks_must_be_current")
    review=protection.get("required_pull_request_reviews")
    if type(review) is not dict or type(review.get("required_approving_review_count")) is not int or (
        review.get("required_approving_review_count",0)<1):
        problems.append("independent_pull_request_review_not_required")
    elif review.get("dismiss_stale_reviews") is not True:
        problems.append("stale_reviews_not_dismissed")
    admin=protection.get("enforce_admins")
    if type(admin) is not dict or admin.get("enabled") is not True:
        problems.append("administrators_may_bypass_rules")
    force_pushes=protection.get("allow_force_pushes")
    if type(force_pushes) is not dict or force_pushes.get("enabled") is not False:
        problems.append("force_push_state_not_explicitly_disabled")
    deletions=protection.get("allow_deletions")
    if type(deletions) is not dict or deletions.get("enabled") is not False:
        problems.append("branch_deletion_state_not_explicitly_disabled")
    conversation=protection.get("required_conversation_resolution")
    if type(conversation) is not dict or conversation.get("enabled") is not True:
        problems.append("review_conversation_resolution_not_required")
    return problems


def get_json(path:str, token:str)->dict:
    # URLs are program-owned constants; never interpolate untrusted host/path.
    allowed={"/branches/main","/branches/main/protection"}
    if path not in allowed:
        raise ValueError("Only approved read-only GitHub metadata endpoints")
    request=Request(ORIGIN+path, headers={
        "Authorization":"Bearer "+token,
        "Accept":"application/vnd.github+json",
        "X-GitHub-Api-Version":"2022-11-28",
        "User-Agent":"MetaAutomate-F04-ReadOnly-Audit",
    },method="GET")
    with urlopen(request,timeout=9) as response:
        payload=response.read(250_000)
    data=json.loads(payload.decode("utf-8"))
    if type(data) is not dict:
        raise ValueError("Unexpected live GitHub API JSON")
    return data


def inspect(*,live:bool=False,token:str="")->dict:
    result={
        "schema_version":1, "gate":"F04", "repo":REPO,
        "branch":BRANCH, "required_check":REQUIRED_CHECK,
        "mode":"LIVE_READ_ONLY" if live else "OFFLINE_SOURCE_ONLY",
        "source_ci_is_enforcement":False,
        "github_branch_rule_enforced":False,
        "blocked_merge_negative_test_verified":False,
        "foundation_f04_verified":False,
        "repository_visibility_must_remain_private":True,
        "release_authorized":False,
        "deployment_authorized":False,
        "reasons":[],
    }
    if not live:
        result["status"]="NO_LIVE_VERIFICATION"
        result["reasons"]=["Live branch-protection enforcement was not queried"]
        return result
    if not token:
        result["status"]="BLOCKED"
        result["reasons"]=["No read-only GitHub API authorization provided"]
        return result
    try:
        branch=get_json("/branches/main",token)
        if branch.get("protected") is True:
            protection=get_json("/branches/main/protection",token)
        else:
            protection=None
        errors=fail_reasons(branch,protection)
        if errors:
            result["status"]="BLOCKED"
            result["reasons"]=errors
            return result
        result["github_branch_rule_enforced"]=True
        # A real intentionally failing CI/PR negative test and independent
        # evidence are still missing, so F04 cannot become VERIFIED here.
        result["status"]="CONFIGURATION_CONFIRMED_INDEPENDENT_PROOF_PENDING"
        result["reasons"]=[
            "Obtain independently witnessed failed-check merge denial",
            "Obtain distinct owner and reviewer attestation",
        ]
    except HTTPError as exc:
        result["status"]="BLOCKED"
        result["reasons"]=[f"GitHub API denied branch evidence (HTTP {exc.code})"]
    except (URLError,TimeoutError,OSError,ValueError,json.JSONDecodeError) as exc:
        result["status"]="BLOCKED"
        result["reasons"]=["Live branch-protection verification unavailable"]
    return result


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--live",action="store_true")
    parser.add_argument("--require-enforced",action="store_true")
    parser.add_argument("--report",type=Path,default=DEFAULT_REPORT)
    args=parser.parse_args(argv)
    data=inspect(live=args.live,
                 token=os.environ.get("F04_GITHUB_READ_TOKEN","") if args.live else "")
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(data,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print("F04: "+data["status"]+"; operational phase remains NO-GO")
    for reason in data["reasons"]:print("- "+reason)
    # An independent observed failed-merge attempt cannot be generated by
    # this read-only script, even when settings are correctly configured.
    if args.require_enforced:
        print("F04 release refused: independent live negative proof and approvals required",
              file=sys.stderr)
        return 1
    return 0


if __name__=="__main__":
    raise SystemExit(main())
