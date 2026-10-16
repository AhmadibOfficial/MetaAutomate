"""P2-03l: workflow-review governance, consent revocation and replay tests."""
import ast
from copy import deepcopy
import json
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.synthetic_growth_autopilot import SyntheticGrowthError, FIXTURE  # noqa: E402
from app.synthetic_growth_review_lab import (  # noqa: E402
    run_committed_review_lab, run_review_lab, validate_review_evidence, MAX_INTENT_BYTES,
)


def step(n, action, eid, role="OWNER"):
    return {"intent_id": f"SIM-INTENT-{n}", "action": action,
            "actor_role": role, "source_event": eid}


def payload(workspace="academy_demo", goal="CONTRIBUTION", steps=None):
    if steps is None:
        steps = [step("ONE", "INSPECT", "DEMO-EVENT-EDU03", "VIEWER")]
    return json.dumps({"schema_version": 1, "workspace": workspace,
                       "goal": goal, "steps": steps}, sort_keys=True).encode()


def test_reviewer_cannot_send_and_replay_is_idempotent():
    accept = step("ACCEPT1", "REVIEW_ACCEPT", "DEMO-EVENT-EDU03", "REVIEWER")
    r = run_committed_review_lab(payload(steps=[
        step("VIEW1", "INSPECT", "DEMO-EVENT-EDU03", "VIEWER"),
        accept, deepcopy(accept),  # repeated exact intent is ignored
        step("REVIEW2", "REVIEW_ACCEPT", "DEMO-EVENT-EDU03", "REVIEWER"),
    ]))
    records = {x["source_event"]: x for x in r["records"]}
    assert records["DEMO-EVENT-EDU03"]["current_state"] == "REVIEWED_IN_SANDBOX"
    assert r["ignored_exact_intent_replays"] == 1
    assert len(r["review_audit"]) == 3
    assert [x["decision"] for x in r["review_audit"]] == [
        "VIEWED_SOURCE_ONLY", "REVIEW_RECORDED_NO_EXECUTION", "DENIED_PRECONDITION",
    ]
    assert r["real_actions_sent"] == r["real_approvals_recorded"] == 0
    assert r["non_operational_controls"]["provider_calls"] == 0
    assert validate_review_evidence(r)
    assert r == run_committed_review_lab(payload(steps=[
        step("VIEW1", "INSPECT", "DEMO-EVENT-EDU03", "VIEWER"),
        accept, deepcopy(accept),
        step("REVIEW2", "REVIEW_ACCEPT", "DEMO-EVENT-EDU03", "REVIEWER"),
    ]))


def test_revocation_invalidates_accepted_and_unreviewed_same_journey():
    r = run_committed_review_lab(payload(steps=[
        step("A1", "REVIEW_ACCEPT", "DEMO-EVENT-EDU03", "OWNER"),
        step("REVOKE1", "REVOKE_CONSENT", "DEMO-EVENT-EDU03", "OWNER"),
        step("AFTER", "REVIEW_ACCEPT", "DEMO-EVENT-EDU04", "OWNER"),
        step("ACK1", "ACK_PROVIDER_OWNERSHIP", "DEMO-EVENT-EDU02", "OWNER"),
    ]))
    by_id = {x["source_event"]: x for x in r["records"]}
    for event in ("DEMO-EVENT-EDU01", "DEMO-EVENT-EDU03", "DEMO-EVENT-EDU04",
                  "DEMO-EVENT-EDU05"):
        assert by_id[event]["current_state"] == "BLOCKED_CONSENT_REVOKED"
    assert by_id["DEMO-EVENT-EDU02"]["current_state"] == "SUPPRESSED_PROVIDER_OWNS"
    assert by_id["DEMO-EVENT-EDU02"]["provider_ownership_noted"]
    assert by_id["DEMO-EVENT-EDU06"]["current_state"] == "SUPPRESSED_CONSENT_UNVERIFIED"
    assert r["review_audit"][2]["decision"] == "DENIED_PRECONDITION"
    assert len(r["synthetic_consent_revocations"]) == 1
    assert validate_review_evidence(r)


@pytest.mark.parametrize("role", ["VIEWER", "REVIEWER"])
def test_revocation_is_owner_only(role):
    r = run_committed_review_lab(payload(steps=[
        step("REVOKE1", "REVOKE_CONSENT", "DEMO-EVENT-EDU03", role),
    ]))
    assert r["review_audit"][0]["decision"] == "DENIED_ROLE"
    assert not r["synthetic_consent_revocations"]
    assert all(row["current_state"] != "BLOCKED_CONSENT_REVOKED" for row in r["records"])


def test_viewer_cannot_accept_and_non_goal_events_cannot_be_promoted():
    r = run_committed_review_lab(payload(goal="RETENTION", steps=[
        step("DENY1", "REVIEW_ACCEPT", "DEMO-EVENT-EDU03", "VIEWER"),
        step("DENY2", "REVIEW_ACCEPT", "DEMO-EVENT-EDU01", "OWNER"),
        step("DENY3", "REVIEW_ACCEPT", "DEMO-EVENT-EDU06", "OWNER"),
        step("DENY4", "REVIEW_ACCEPT", "DEMO-EVENT-EDU02", "OWNER"),
    ]))
    assert r["review_audit"][0]["decision"] == "DENIED_ROLE"
    assert all(row["decision"] != "REVIEW_RECORDED_NO_EXECUTION" for row in r["review_audit"])
    assert r["state_totals"]["DEFERRED_NOT_GOAL_RELEVANT"] == 1
    assert r["state_totals"]["SUPPRESSED_PROVIDER_OWNS"] == 1


def test_rejection_prevents_later_accept_and_bespoke_scope_is_separate():
    r = run_committed_review_lab(payload(
        workspace="bespoke_demo", goal="COMPLETED_ORDERS", steps=[
            step("REJECT", "REVIEW_DECLINE", "DEMO-EVENT-FAS03", "REVIEWER"),
            step("LATER", "REVIEW_ACCEPT", "DEMO-EVENT-FAS03", "OWNER"),
        ],
    ))
    state = {x["source_event"]: x["current_state"] for x in r["records"]}
    assert state["DEMO-EVENT-FAS03"] == "DECLINED_IN_SANDBOX"
    assert r["review_audit"][1]["decision"] == "DENIED_PRECONDITION"
    assert len(r["records"]) == 6


def test_all_goals_and_workspaces_preserve_denials():
    for ws, source in (("academy_demo", "DEMO-EVENT-EDU02"),
                       ("bespoke_demo", "DEMO-EVENT-FAS02")):
        for goal in ("CONTRIBUTION", "RETENTION", "COMPLETED_ORDERS"):
            r = run_committed_review_lab(payload(
                workspace=ws, goal=goal,
                steps=[step("X", "REVIEW_ACCEPT", source)],
            ))
            assert r["review_audit"][0]["decision"] == "DENIED_PRECONDITION"
            assert r["state_totals"]["SUPPRESSED_PROVIDER_OWNS"] == 1
            assert all(not p["real_execution_permitted"] for p in r["records"])
            assert validate_review_evidence(r)


def test_replay_collision_fails_closed():
    a = step("SAME", "INSPECT", "DEMO-EVENT-EDU03")
    b = step("SAME", "REVIEW_ACCEPT", "DEMO-EVENT-EDU03")
    with pytest.raises(SyntheticGrowthError, match="Intent ID collision"):
        run_committed_review_lab(payload(steps=[a, b]))


@pytest.mark.parametrize("source", [
    b"", b"\xff", b"\x00", b"[]", b'{"schema_version":1, "schema_version":1}',
    b'{"schema_version":NaN}', b'{"schema_version":1.5}',
    b" " * (MAX_INTENT_BYTES+1),
])
def test_malformed_input_denied(source):
    with pytest.raises(SyntheticGrowthError):
        run_committed_review_lab(source)


@pytest.mark.parametrize("field,value", [
    ("workspace", "unknown_tenant"), ("goal", "SEND_MONEY"),
    ("schema_version", True), ("extra", "customer@example.com"),
])
def test_unknown_schema_and_real_tenant_data_rejected(field, value):
    obj = json.loads(payload())
    obj[field] = value
    with pytest.raises(SyntheticGrowthError):
        run_committed_review_lab(json.dumps(obj).encode())


@pytest.mark.parametrize("action", ["SEND", "SCHEDULE", "PUBLISH", "BILL", "AUTHENTICATE", "EXECUTE"])
def test_no_external_action_can_be_requested(action):
    with pytest.raises(SyntheticGrowthError, match="Unsupported action"):
        run_committed_review_lab(payload(steps=[
            step("NOTALLOWED", action, "DEMO-EVENT-EDU03")
        ]))


def test_unknown_or_cross_workspace_events_fail_closed():
    with pytest.raises(SyntheticGrowthError, match="Cross-workspace or unknown"):
        run_committed_review_lab(payload(steps=[
            step("FOREIGN", "INSPECT", "DEMO-EVENT-FAS03")
        ]))
    with pytest.raises(SyntheticGrowthError, match="Cross-workspace or unknown"):
        run_committed_review_lab(payload(steps=[
            step("UNKNOWN", "INSPECT", "DEMO-EVENT-UNKNOWN")
        ]))


def test_unexpected_step_fields_such_as_contact_data_denied():
    doc = json.loads(payload())
    doc["steps"][0]["phone"] = "+234000000000"
    with pytest.raises(SyntheticGrowthError, match="Invalid step shape"):
        run_committed_review_lab(json.dumps(doc).encode())


def test_broken_hash_chain_and_report_detected():
    r = run_committed_review_lab(payload())
    assert validate_review_evidence(r)
    altered = deepcopy(r)
    altered["review_audit"][0]["decision"] = "REVIEW_RECORDED_NO_EXECUTION"
    assert not validate_review_evidence(altered)
    altered = deepcopy(r)
    altered["records"][0]["real_execution_permitted"] = True
    assert not validate_review_evidence(altered)
    assert not validate_review_evidence({"audit_chain_valid":True})


def test_source_has_no_provider_or_network_effect_imports():
    path = ROOT / "apps/api/app/synthetic_growth_review_lab.py"
    source = path.read_text()
    main = (ROOT / "apps/api/app/main.py").read_text()
    assert "include_router(synthetic_growth_review_lab" not in main
    mods = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            mods.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split(".")[0])
    assert mods.isdisjoint({"requests","httpx","urllib","redis","sqlalchemy","psycopg",
                           "smtplib","socket","fastapi","subprocess","celery","stripe"})
    assert "NON_OPERATIONAL" in source
    assert "REVIEWED_IN_SANDBOX" in source
