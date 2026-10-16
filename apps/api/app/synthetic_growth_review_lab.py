"""P2-03l: deterministic, non-operational workflow review and consent safety lab.

Input is strictly validated invented fixture data and bounded synthetic review intents.
This is not a provider outbox, real approval, user account, authenticated authorization,
consent registry, messaging system, or tamper-proof persistent audit ledger.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re
from typing import Any

from .synthetic_growth_autopilot import (
    FIXTURE, SyntheticGrowthError, parse_growth_fixture,
)
from .synthetic_growth_orchestration import (
    GOALS, NON_OPERATIONAL, build_growth_work_plan,
)

MAX_INTENT_BYTES = 12_288
MAX_STEPS = 24
INTENT_ID = re.compile(r"SIM-INTENT-[A-Z0-9]{1,20}\Z")
OPERATIONS = frozenset({
    "INSPECT", "REVIEW_ACCEPT", "REVIEW_DECLINE",
    "REVOKE_CONSENT", "ACK_PROVIDER_OWNERSHIP",
})
ROLES = frozenset({"OWNER", "REVIEWER", "VIEWER"})
APPROVAL_ROLES = frozenset({"OWNER", "REVIEWER"})
ZERO_HASH = "0" * 64
STATES = frozenset({
    "REVIEW_REQUIRED", "REVIEWED_IN_SANDBOX", "DECLINED_IN_SANDBOX",
    "SUPPRESSED_PROVIDER_OWNS", "SUPPRESSED_CONSENT_UNVERIFIED",
    "DEFERRED_NOT_GOAL_RELEVANT", "BLOCKED_CONSENT_REVOKED",
})


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _digest(value: Any) -> str:
    return sha256(_canonical(value)).hexdigest()


def _pairs(values: list[tuple[str, Any]]) -> dict:
    result: dict = {}
    for key, value in values:
        if key in result:
            raise SyntheticGrowthError("Duplicate intent JSON field")
        result[key] = value
    return result


def _invalid_number(value: str) -> None:
    raise SyntheticGrowthError("Unsupported numeric constant")


def _exact(value: Any, keys: set[str], where: str) -> dict:
    if type(value) is not dict or set(value) != keys:
        raise SyntheticGrowthError(f"Invalid {where} shape")
    return value


def _intent_doc(raw: bytes) -> dict:
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_INTENT_BYTES or b"\x00" in raw:
        raise SyntheticGrowthError("Invalid bounded review-intent payload")
    try:
        doc = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                         parse_float=_invalid_number, parse_constant=_invalid_number)
    except SyntheticGrowthError:
        raise
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise SyntheticGrowthError("Malformed review-intent JSON") from exc
    _exact(doc, {"schema_version", "workspace", "goal", "steps"}, "intent document")
    if type(doc["schema_version"]) is not int or doc["schema_version"] != 1:
        raise SyntheticGrowthError("Unsupported review-intent schema")
    if type(doc["workspace"]) is not str or doc["workspace"] not in {
        "academy_demo", "bespoke_demo",
    }:
        raise SyntheticGrowthError("Invalid workspace scope")
    if type(doc["goal"]) is not str or doc["goal"] not in GOALS:
        raise SyntheticGrowthError("Invalid goal")
    steps = doc["steps"]
    if type(steps) is not list or not 1 <= len(steps) <= MAX_STEPS:
        raise SyntheticGrowthError("Invalid review-intent step count")
    for step in steps:
        _exact(step, {"intent_id", "action", "actor_role", "source_event"}, "step")
        if type(step["intent_id"]) is not str or not INTENT_ID.fullmatch(step["intent_id"]):
            raise SyntheticGrowthError("Invalid synthetic intent ID")
        if type(step["action"]) is not str or step["action"] not in OPERATIONS:
            raise SyntheticGrowthError("Unsupported action; no execution verbs are allowed")
        if type(step["actor_role"]) is not str or step["actor_role"] not in ROLES:
            raise SyntheticGrowthError("Unrecognized role")
        if type(step["source_event"]) is not str or not step["source_event"].startswith("DEMO-EVENT-"):
            raise SyntheticGrowthError("Only invented source event IDs accepted")
    return doc


def _audit_append(entries: list[dict], *, step: dict, result: str,
                  state_before: str, state_after: str, journey: str) -> None:
    """Digest-chain evidence for local regression review, not signed/nonrepudiable audit."""
    row = {
        "sequence": len(entries) + 1,
        "previous_hash": entries[-1]["record_hash"] if entries else ZERO_HASH,
        "intent_id": step["intent_id"],
        "action": step["action"],
        "actor_role": step["actor_role"],  # A test role, never an authenticated principal.
        "source_event": step["source_event"],
        "synthetic_journey": journey,
        "decision": result,
        "before": state_before,
        "after": state_after,
        "actual_provider_action": False,
        "actual_customer_consent_verified": False,
    }
    row["record_hash"] = _digest(row)
    entries.append(row)


def _verify_chain(entries: list[dict]) -> bool:
    previous = ZERO_HASH
    for idx, row in enumerate(entries, start=1):
        if type(row) is not dict or row.get("sequence") != idx:
            return False
        if row.get("previous_hash") != previous:
            return False
        if row.get("record_hash") != _digest({
            k: v for k, v in row.items() if k != "record_hash"
        }):
            return False
        previous = row["record_hash"]
    return True


def run_review_lab(raw_fixture: bytes, review_intents: bytes) -> dict:
    """Evaluate a bounded synthetic review sequence entirely in memory.

    Rejects unknown scopes and user-supplied customer details before any state
    change. Every initial proposal is the P2-03j decision for the selected goal.
    A "REVIEWED_IN_SANDBOX" state is never authorization to dispatch.
    """
    doc = _intent_doc(review_intents)
    fixture = parse_growth_fixture(raw_fixture)  # validate ALL workspaces
    planned = build_growth_work_plan(raw_fixture, goal=doc["goal"], workspace=doc["workspace"])
    if len(planned["workspaces"]) != 1:
        raise SyntheticGrowthError("Unresolved workspace")
    group = next(x for x in fixture["workspaces"] if x["workspace"] == doc["workspace"])
    business = planned["workspaces"][0]
    refs = {e["event_id"]: e for e in group["events"]}
    proposals = {p["source_event"]: p for p in business["workflow_proposals"]}
    current = {
        eid: ("REVIEW_REQUIRED" if p["state"] == "PROPOSED_HUMAN_REVIEW_ONLY"
              else p["state"]) for eid, p in proposals.items()
    }
    if any(s not in STATES for s in current.values()):
        raise SyntheticGrowthError("Unsupported source-engine state")
    # Full pre-validation also blocks referencing another workspace even if
    # this is a rejected action or repeated intent.
    for step in doc["steps"]:
        if step["source_event"] not in refs:
            raise SyntheticGrowthError("Cross-workspace or unknown event reference")
    audit: list[dict] = []
    seen: dict[str, str] = {}
    revocations: set[str] = set()
    provider_ack: set[str] = set()
    ignored_replays = 0
    for step in doc["steps"]:
        fingerprint = _digest(step)
        intent_id = step["intent_id"]
        if intent_id in seen:
            if seen[intent_id] != fingerprint:
                raise SyntheticGrowthError("Intent ID collision with mismatched payload")
            ignored_replays += 1  # same id and payload -> same effect, no extra audit
            continue
        seen[intent_id] = fingerprint
        eid = step["source_event"]
        journey = refs[eid]["journey_id"]
        before = current[eid]
        role = step["actor_role"]
        action = step["action"]
        decision = "DENIED_PRECONDITION"
        if action == "INSPECT":
            decision = "VIEWED_SOURCE_ONLY"
        elif action in {"REVIEW_ACCEPT", "REVIEW_DECLINE"}:
            if role not in APPROVAL_ROLES:
                decision = "DENIED_ROLE"
            elif before == "REVIEW_REQUIRED" and journey not in revocations:
                current[eid] = ("REVIEWED_IN_SANDBOX" if action == "REVIEW_ACCEPT"
                                else "DECLINED_IN_SANDBOX")
                decision = "REVIEW_RECORDED_NO_EXECUTION"
        elif action == "REVOKE_CONSENT":
            if role != "OWNER":
                decision = "DENIED_ROLE"
            elif journey in revocations:
                decision = "ALREADY_REVOKED"
            else:
                revocations.add(journey)
                for other_id, other in refs.items():
                    if other["journey_id"] == journey and current[other_id] != "SUPPRESSED_PROVIDER_OWNS":
                        current[other_id] = "BLOCKED_CONSENT_REVOKED"
                decision = "SYNTHETIC_JOURNEY_REVOKED"
        elif action == "ACK_PROVIDER_OWNERSHIP":
            if role != "OWNER":
                decision = "DENIED_ROLE"
            elif before == "SUPPRESSED_PROVIDER_OWNS":
                provider_ack.add(eid)
                decision = "NATIVE_PROVIDER_OWNER_NOTED_NO_CALL"
        _audit_append(audit, step=step, result=decision, state_before=before,
                      state_after=current[eid], journey=journey)
    ordered = [
        {
            "source_event": p["source_event"],
            "plan_id": p["plan_id"],
            "event_kind": p["event_kind"],
            "synthetic_journey": refs[p["source_event"]]["journey_id"],
            "initial_state": p["state"],
            "current_state": current[p["source_event"]],
            "provider_ownership_noted": p["source_event"] in provider_ack,
            "real_execution_permitted": False,
        }
        for p in business["workflow_proposals"]
    ]
    totals: dict[str, int] = {}
    for p in ordered:
        totals[p["current_state"]] = totals.get(p["current_state"], 0) + 1
    report = {
        "schema_version": 1,
        "milestone": "P2-03l_REVIEW_LIFECYCLE_LAB",
        "classification": "SYNTHETIC_SOURCE_ONLY",
        "workspace": doc["workspace"],
        "goal": doc["goal"],
        "records": ordered,
        "state_totals": totals,
        "review_audit": audit,
        "audit_chain_valid": _verify_chain(audit),
        "ignored_exact_intent_replays": ignored_replays,
        "synthetic_consent_revocations": sorted(revocations),
        "real_customer_consent_change_made": False,
        "audit_security_note": "Digest chain is not signed, durable, or tamper-proof",
        "non_operational_controls": dict(NON_OPERATIONAL),
        "real_approvals_recorded": 0,
        "real_actions_scheduled": 0,
        "real_actions_sent": 0,
        "customer_records_processed": 0,
        "subscriptions_started": 0,
        "fixture_sha256": sha256(raw_fixture).hexdigest(),
        "intents_sha256": sha256(review_intents).hexdigest(),
    }
    report["evidence_sha256"] = _digest(report)
    return report


def run_committed_review_lab(review_intents: bytes) -> dict:
    return run_review_lab(FIXTURE.read_bytes(), review_intents)


def validate_review_evidence(report: dict) -> bool:
    """Check local evidence integrity; not a cryptographic signature or identity proof."""
    if type(report) is not dict or report.get("audit_chain_valid") is not True:
        return False
    if not _verify_chain(report.get("review_audit", [])):
        return False
    if report.get("non_operational_controls") != NON_OPERATIONAL:
        return False
    if report.get("real_actions_sent") != 0 or report.get("subscriptions_started") != 0:
        return False
    evidence_hash = report.get("evidence_sha256")
    return type(evidence_hash) is str and evidence_hash == _digest({
        key: value for key, value in report.items() if key != "evidence_sha256"
    })
