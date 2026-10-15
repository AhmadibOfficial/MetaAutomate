"""P3-08: validate local independent-review handoff, NEVER sign off a review.

The source packet is deliberately PENDING-only. GitHub identities/reviews,
provider authorization, branch protections and live outcomes require real
external evidence and cannot be asserted by editing a local JSON file.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

from app.phase03_contract_audit import (
    OfflineContractDenied, _read_strict_manifest, audit_local_contracts,
)

ROOT = Path(__file__).resolve().parents[3]
QUEUE = "contracts/engineering/phase03_independent_review_queue.json"
EXPECTED_PARENT_SHA = "c59dab15defc89ecb8b19db869afa1ea0007ade9"
RISK_IDS = tuple(f"P3T-{index:02}" for index in range(1, 11))


class ReviewReadinessDenied(ValueError):
    """Unknown or falsely approved review packet rejected."""


def _deny() -> None:
    raise ReviewReadinessDenied(
        "Review readiness source data is invalid; NOT APPROVED"
    )


@dataclass(frozen=True)
class ReviewPreparation:
    parent_source_sha: str
    github_ci_python_passed: int
    owner_kali_source_passed: int
    reviewer_risks_pending: int
    source_contracts_compatible: bool
    decision: str = "NO_GO"
    status: str = "INDEPENDENT_REVIEW_NOT_PERFORMED"
    external_evidence_verified: bool = False
    reviewer_identity_authenticated: bool = False
    private_branch_protection_verified: bool = False
    live_provider_receipt_verified: bool = False
    provider_access_permitted: bool = False
    customer_data_permitted: bool = False
    independent_human_review_completed: bool = False
    production_execution_authorized: bool = False
    merge_authorized: bool = False


def build_review_preparation(root: Path = ROOT) -> ReviewPreparation:
    """Read an immutable-style source TODO list; it cannot certify anything."""
    try:
        queue = _read_strict_manifest(root, QUEUE)
        audit = audit_local_contracts(root)
    except (OfflineContractDenied, OSError, TypeError, ValueError) as exc:
        raise ReviewReadinessDenied("Missing or unsafe review source material") from exc
    if type(queue) is not dict:
        _deny()
    target = queue.get("review_target")
    acceptance = queue.get("source_acceptance")
    foundation = queue.get("foundational_status")
    tasks = queue.get("unverified_tasks")
    if any(type(x) is not dict for x in (target, acceptance, foundation)):
        _deny()
    if not (
        type(queue.get("schema_version")) is int
        and queue["schema_version"] == 1
        and queue.get("milestone") == "P3-08"
        and queue.get("purpose")
        == "INDEPENDENT_REVIEW_PREPARATION_NOT_INDEPENDENT_APPROVAL"
        and queue.get("review_state") == "NOT_REVIEWED"
        and queue.get("release_decision") == "NO_GO"
        and queue.get("merge_authorized") is False
        and target.get("source_commit") == EXPECTED_PARENT_SHA
        and re.fullmatch(r"[0-9a-f]{40}", target.get("source_commit", "")) is not None
        and type(target.get("pr_number")) is int
        and target["pr_number"] == 53
        and target.get("repository") == "AhmadibOfficial/MetaAutomate"
        and target.get("review_target_is_parent_source") is True
        and target.get("reviewed_by_independent_human") is False
        and type(acceptance.get("github_ci_run")) is int
        and acceptance["github_ci_run"] == 157
        and type(acceptance.get("github_ci_python_passed")) is int
        and acceptance["github_ci_python_passed"] == 903
        and type(acceptance.get("owner_kali_phase03_passed")) is int
        and acceptance["owner_kali_phase03_passed"] == 572
        and type(acceptance.get("owner_kali_suites")) is int
        and acceptance["owner_kali_suites"] == 9
        and acceptance.get("owner_kali_provided_not_independent") is True
        and type(foundation.get("phase01_verified")) is int
        and foundation["phase01_verified"] == 3
        and type(foundation.get("phase01_required")) is int
        and foundation["phase01_required"] == 9
        and foundation.get("phase02_operational_approved") is False
        and foundation.get("phase03_live_execution_authorized") is False
        and type(tasks) is list
        and len(tasks) == len(RISK_IDS)
        and audit.source_compatible is True
        and audit.merge_authorized is False
    ):
        _deny()
    for task, expected_id in zip(tasks, RISK_IDS):
        if (
            type(task) is not dict
            or task.get("id") != expected_id
            or type(task.get("threat")) is not str
            or not 5 <= len(task["threat"]) <= 128
            or type(task.get("required_external_evidence")) is not str
            or not 10 <= len(task["required_external_evidence"]) <= 256
            or task.get("status") != "PENDING_INDEPENDENT_REVIEW"
            or task.get("evidence_provided") is not False
        ):
            _deny()
    return ReviewPreparation(
        parent_source_sha=EXPECTED_PARENT_SHA,
        github_ci_python_passed=903,
        owner_kali_source_passed=572,
        reviewer_risks_pending=len(tasks),
        source_contracts_compatible=True,
    )
