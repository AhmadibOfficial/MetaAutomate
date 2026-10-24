#!/usr/bin/env python3
"""QDB START source-evidence register; offline, deterministic and fail-closed.

The report is a developer-generated due-diligence index, not a funding
application, production audit, automated application submission or proof of
customers, revenue, traction, eligibility, real AI, or verified controls.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FOUNDATION = "docs/operational-core/FOUNDATION_EXIT_EVIDENCE.json"
PROGRAM_URL = "https://www.qdb.qa/en/financing-and-funding/equity-and-investment/startup-qatar-investment-program"
APPLICATION_URL = "https://www.f6s.com/sqinvestmentprogram"

CAPABILITIES = {
    "agent_orchestration": ("apps/site/intelligence/workbench.js", "apps/api/app/objective_ops.py"),
    "creative_images_video": ("apps/site/assets/creative-maker.js", "apps/site/assets/creative-video.js"),
    "social_media_workflow": ("apps/site/assets/campaign-workbench.js", "apps/site/campaigns/index.html"),
    "data_research": ("apps/site/assets/campaign-engine.js", "apps/site/intelligence-lab/lab.js"),
    "business_automation": ("apps/site/automation/workspace.js", "apps/api/app/synthetic_inventory_import.py"),
    "secure_data_lab": ("apps/api/app/secure_inventory_lab.py", "apps/api/app/secure_data_lab_api.py"),
}

START_EVIDENCE = (
    ("market_need", "Independently researched Qatar buyer problem and competitor map"),
    ("validated_concept", "Demonstrable functional workflow and honest technical acceptance"),
    ("execution_roadmap", "Milestones, risks, owners, acceptance criteria and budget"),
    ("market_research", "Qatar customer interviews and market research with citations"),
    ("business_model", "Unit economics, cost assumptions and monetization strategy"),
    ("founding_team", "Consent-cleared biographies, roles, and availability"),
    ("qatar_entry", "Qatar establishment and market-entry feasibility, independently checked"),
    ("commercial_traction", "Permissioned pilots, referenceable outcomes or genuine revenue records"),
)

class ReadinessError(ValueError):
    pass


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=root, capture_output=True,
                          text=True, check=False, timeout=10)
    if proc.returncode:
        raise ReadinessError("Git metadata unavailable; use a local git checkout")
    return proc.stdout.strip()


def _source_inventory(root: Path) -> tuple[str, str, set[str]]:
    if Path(_git(root, "rev-parse", "--show-toplevel")).resolve() != root.resolve():
        raise ReadinessError("Repository root mismatch")
    if _git(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise ReadinessError("Worktree has uncommitted files; do not produce clean-checkout evidence")
    commit = _git(root, "rev-parse", "HEAD")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ReadinessError("Invalid commit fingerprint")
    branch = _git(root, "branch", "--show-current")
    if not branch:
        raise ReadinessError("Detached HEAD must be documented explicitly before generating evidence")
    inventory = set(_git(root, "ls-tree", "-r", "--name-only", "HEAD").splitlines())
    return commit, branch, inventory


def _regular_committed_source(root: Path, path: str, inventory: set[str]) -> bool:
    """Count only regular committed files; never follow source or parent symlinks.

    Git tracks symlinks as paths, and Path.is_file() follows them. Without this
    guard, a checkout could report source presence or read Foundation evidence
    from an untracked file outside the repository.
    """
    if path not in inventory:
        return False
    relative = Path(path)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        return False
    candidate = root
    for component in relative.parts:
        candidate = candidate / component
        if candidate.is_symlink():
            return False
    return candidate.is_file()


def _foundation(root: Path, inventory: set[str]) -> dict:
    if not _regular_committed_source(root, FOUNDATION, inventory):
        raise ReadinessError("Foundation evidence missing, symlinked or not a regular committed file")
    with (root / FOUNDATION).open(encoding="utf-8") as file:
        data = json.load(file)
    entries = data.get("checks")
    if (data.get("policy") != "NO_GO_UNTIL_ALL_NINE_VERIFIED"
            or not isinstance(entries, list) or len(entries) != 9):
        raise ReadinessError("Foundation evidence is not the expected nine-check NO-GO record")
    statuses = {}
    for entry in entries:
        if not isinstance(entry, dict) or entry.get("id") not in {f"F{x:02}" for x in range(1, 10)}:
            raise ReadinessError("Malformed foundation entry")
        if entry["id"] in statuses or entry.get("status") not in ("verified", "blocked"):
            raise ReadinessError("Duplicate or unsupported foundation status")
        statuses[entry["id"]] = entry["status"]
    if len(statuses) != 9:
        raise ReadinessError("Incomplete foundation evidence")
    counts = Counter(statuses.values())
    return {
        "status": "OPERATIONAL_NO_GO",
        "verified_count": counts["verified"],
        "blocked_count": counts["blocked"],
        "total": 9,
        "source_path": FOUNDATION,
        "checks": statuses,
        "do_not_infer_operational_readiness": True,
    }


def _local_report(path: Path | None, repo: Path, commit: str) -> dict:
    if path is None:
        return {"status": "NOT_PROVIDED", "independently_verified": False}
    resolved = path.expanduser().resolve()
    if resolved.is_relative_to(repo.resolve()) or not resolved.is_file() or resolved.stat().st_size > 128_000:
        raise ReadinessError("Local test report must be a small existing file outside the repository")
    with resolved.open(encoding="utf-8") as file:
        doc = json.load(file)
    if not isinstance(doc, dict) or doc.get("gate") != "LOCAL_SOURCE_CHECK_ONLY":
        raise ReadinessError("Unexpected local validation format")
    if doc.get("commit") != commit:
        raise ReadinessError("Local test evidence refers to a different commit")
    if doc.get("github_ci_verified") is not False or doc.get("merge_approved") is not False or doc.get("deployment_approved") is not False:
        raise ReadinessError("Refusing report that claims independent approvals")
    reported = doc.get("result")
    if reported not in ("LOCAL_TESTS_PASS", "BLOCKED_OR_FAILED", "BLOCKED"):
        raise ReadinessError("Unknown local report status")
    return {
        "status": "DEVELOPER_REPORTED_" + reported,
        "independently_verified": False,
        "commit_matches": True,
        "note": "User-provided local test report, not authenticated runner or hosted CI evidence",
    }


# Optional deterministic synthetic demo: trusted checked-out source only.
# This is not a secure sandbox for untrusted JavaScript. Nothing runs by default.
_SYNTHETIC_DEMO_JS = "// Synthetic fixtures only: this is not a customer, CI or deployment test.\nconst assert = require(\"node:assert/strict\");\nconst engine = require(\"./apps/site/assets/campaign-engine.js\");\nconst data = engine.parseCSV([\n  \"sku,name,stock,weekly_sales,unit_price_kobo\",\n  \"SLOW-01,Canvas Tote,18,0,850000\",\n  \"HIGH-02,Blue Scarf,30,5,350000\",\n  \"OUT-03,No Stock,0,0,20000\",\n  \"LOW-04,Almost Gone,2,8,20000\"\n].join(\"\\n\") + \"\\n\");\nassert.equal(data.length, 4);\nconst analysis = engine.analyze(data);\nassert.deepEqual(analysis.opportunities.map(x => x.sku), [\"SLOW-01\", \"HIGH-02\"]);\nconst draft = engine.makeCampaign(analysis.opportunities[0], \"Synthetic Demo Shop\", \"Instagram\");\nassert.match(draft.post, /₦8,500\\.00/);\nassert.match(draft.post, /confirm before ordering/);\nassert.doesNotMatch(draft.post, /free delivery|guaranteed|% off/i);\nassert.throws(() => engine.makeCampaign(data[2], \"Synthetic Demo Shop\", \"Instagram\"), engine.CampaignError);\nassert.throws(() => engine.makeCampaign(data[0], \"Synthetic Demo Shop\", \"Unsupported\"), engine.CampaignError);\nconst metrics = engine.summarizeMetrics({\n  impressions: \"100\", clicks: \"20\", orders: \"3\", sourceNote: \"Synthetic demo numbers only\"\n});\nassert.equal(metrics.clickThroughRatePct, 20);\nassert.equal(metrics.clickToOrderPct, 15);\nassert.equal(metrics.evidence, \"SELF_REPORTED_NOT_INDEPENDENTLY_VERIFIED\");\nassert.equal(Object.hasOwn(metrics, \"revenue\"), false);\nassert.throws(() => engine.summarizeMetrics({\n  impressions: \"10\", clicks: \"11\", orders: \"1\", sourceNote: \"Synthetic invalid funnel\"\n}), engine.CampaignError);\nprocess.stdout.write(\"QDB_SYNTHETIC_DEMO_PASS\\n\");"


def _synthetic_demo(root: Path, inventory: set[str], *, enabled: bool) -> dict:
    if not enabled:
        return {"status": "NOT_RUN", "independently_verified": False}
    path = "apps/site/assets/campaign-engine.js"
    if not _regular_committed_source(root, path, inventory):
        raise ReadinessError("Synthetic demonstration requires a regular committed campaign engine")
    node = shutil.which("node")
    if node is None:
        raise ReadinessError("Node.js unavailable; synthetic demo was not executed")
    env = os.environ.copy()
    env.pop("NODE_OPTIONS", None)
    env.pop("NODE_PATH", None)
    try:
        run = subprocess.run(
            [node, "-e", _SYNTHETIC_DEMO_JS], cwd=root,
            stdin=subprocess.DEVNULL, capture_output=True,
            text=True, timeout=20, check=False, env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise ReadinessError("Synthetic campaign demonstration timed out") from exc
    if run.returncode != 0 or run.stdout != "QDB_SYNTHETIC_DEMO_PASS\n":
        raise ReadinessError("Synthetic campaign demonstration failed; no success evidence recorded")
    return {
        "status": "DEVELOPER_LOCAL_SYNTHETIC_PASS",
        "capability": "inventory_to_campaign_decision_engine",
        "source_path": path,
        "fixture": "BUILT_IN_SYNTHETIC_INVENTORY_AND_METRICS",
        "scenario": "CSV import, stock-priority selection, safety guards, draft generation, metric arithmetic",
        "independently_verified": False,
        "browser_e2e_verified": False,
        "real_customer_data_used": False,
        "commercial_traction_verified": False,
        "production_release_approved": False,
        "note": "Node assertions against local committed code, not authenticated browser, live AI, CI or Qatar customer validation",
    }


def assess(root: Path = ROOT, *, local_report: Path | None = None, run_synthetic_demo: bool = False) -> dict:
    root = root.resolve()
    commit, branch, inventory = _source_inventory(root)
    capabilities = {}
    for name, paths in CAPABILITIES.items():
        present = [path for path in paths if _regular_committed_source(root, path, inventory)]
        capabilities[name] = {
            "source_presence": "SOURCE_FILES_PRESENT" if len(present) == len(paths) else "SOURCE_INCOMPLETE",
            "committed_source_paths": present,
            "missing_source_paths": [path for path in paths if path not in present],
            "functional_e2e_verified": False,
            "publicly_operational": False,
        }
    return {
        "schema_version": 1,
        "packet_type": "QDB_START_PRE_APPLICATION_SOURCE_INVENTORY",
        "applicant_product": "MetaAutomate",
        "program": "QDB Startup Qatar Investment Program - START (candidate, not confirmed eligible)",
        "program_url": PROGRAM_URL,
        "application_link": APPLICATION_URL,
        "git": {"commit": commit, "branch": branch, "dirty": False},
        "capabilities": capabilities,
        "foundation": _foundation(root, inventory),
        "local_validation": _local_report(local_report, root, commit),
        "synthetic_functional_demo": _synthetic_demo(root, inventory, enabled=run_synthetic_demo),
        "qdb_start_readiness": {
            key: {"status": "EVIDENCE_NOT_IN_THIS_SOURCE_INVENTORY", "needed": description}
            for key, description in START_EVIDENCE
        },
        "eligibility_verified": False,
        "qatar_market_demand_verified": False,
        "customer_traction_verified": False,
        "revenue_verified": False,
        "funding_approved": False,
        "investment_requested_usd": None,
        "application_submitted": False,
        "live_ai_agents_verified": False,
        "independent_ci_verified": False,
        "release_approved": False,
        "note": "A committed path proves source presence only. No funding or commercial claims validated.",
    }


def _write_new(root: Path, target: Path, payload: bytes):
    path = target.expanduser().resolve()
    if path.is_relative_to(root.resolve()):
        raise ReadinessError("Evidence output must not be inside the repository")
    if not path.parent.is_dir() or target.is_symlink():
        raise ReadinessError("Choose an existing destination directory and non-symlink output")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as file:
            file.write(payload)
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--local-test-report", type=Path, help="Existing P2-061 local JSON report outside source checkout")
    p.add_argument("--output", type=Path, help="Create a NEW JSON report outside checkout; never overwrite")
    p.add_argument("--run-synthetic-demo", action="store_true", help="Opt-in local Node smoke check with synthetic inputs; not browser/CI evidence")
    opts = p.parse_args(argv)
    try:
        report = assess(local_report=opts.local_test_report, run_synthetic_demo=opts.run_synthetic_demo)
        body = (json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode()
        if opts.output:
            _write_new(ROOT, opts.output, body)
        else:
            sys.stdout.write(body.decode())
        return 0
    except (ReadinessError, OSError, ValueError, json.JSONDecodeError) as exc:
        print("QDB_EVIDENCE_BLOCKED: " + str(exc)[:350], file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
