"""Review-gated source capability lifecycle: offline, negative-first regression tests."""
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_capability_lifecycle as lifecycle  # noqa: E402


def sources():
    manifest, policy, history, foundation, catalog, _ = lifecycle.load_sources(ROOT)
    return manifest, policy, history, foundation, catalog


def sample():
    return json.loads(
        (ROOT / "docs/registry/examples/lifecycle-proposal.example.json").read_text(
            encoding="utf-8"
        )
    )


def evaluate(manifest, policy, history, foundation, catalog, proposal=None):
    return lifecycle.evaluate(
        manifest, policy, history, foundation, catalog, ROOT, proposal
    )[0]


def accepted_event(proposal):
    event = {
        key: copy.deepcopy(value)
        for key, value in proposal.items()
        if key not in {"example_only", "proposal_schema_version"}
    }
    event["event_id"] = "LCE-0002"
    event["evidence"]["ci_run_url"] = (
        "https://github.com/AhmadibOfficial/MetaAutomate/actions/runs/38844242125"
    )
    event["review"] = {
        "decision": "SOURCE_REVIEWED_ONLY",
        "review_ref": "https://github.com/AhmadibOfficial/MetaAutomate/pull/60",
        "reviewer": "Source reviewer recorded for in-memory test only",
        "decision_date": "2026-10-16",
        "separation_statement": "NOT_OPERATIONAL_AUTHORIZATION",
    }
    return event


def replace_entry(manifest, target):
    for index, entry in enumerate(manifest["entries"]):
        if entry["id"] == target["id"]:
            manifest["entries"][index] = target
            return
    raise AssertionError("Missing engineering capability")


def test_lifecycle_genesis_exact_and_source_only():
    manifest, policy, history, foundation, catalog = sources()
    assert evaluate(manifest, policy, history, foundation, catalog) == []
    assert len(history["events"]) == 1
    assert history["events"][0]["event_id"] == "LCE-0001"
    assert history["events"][0]["capability_id"] == "CAP-BUSINESS"
    assert len(history["baseline"]["entries"]) == 19
    assert history["baseline"]["commit"] == lifecycle.BASELINE_COMMIT
    assert all(x["operational_status"] == "NO_GO" for x in manifest["entries"])


def test_example_proposal_is_complete_but_requires_review():
    manifest, policy, history, foundation, catalog = sources()
    proposal = sample()
    assert proposal["example_only"] is True
    assert proposal["change_type"] == "EVIDENCE_REFRESH"
    assert evaluate(manifest, policy, history, foundation, catalog, proposal) == []
    baseline = {entry["id"]: entry for entry in history["baseline"]["entries"]}
    current = {entry["id"]: entry for entry in manifest["entries"]}
    assert all(current[key] == value for key, value in baseline.items() if key != "CAP-BUSINESS")
    assert current["CAP-BUSINESS"] == history["events"][0]["after"]


def test_silent_evidence_change_is_rejected():
    manifest, policy, history, foundation, catalog = sources()
    manifest["entries"][0]["known_limitations"] = "Concealed unreviewed change"
    errors = evaluate(manifest, policy, history, foundation, catalog)
    assert any("sequential accepted source lifecycle events" in error for error in errors)


def test_source_only_event_replay_changes_no_operational_policy():
    manifest, policy, history, foundation, catalog = sources()
    proposal = sample()
    event = accepted_event(proposal)
    history["events"].append(event)
    replace_entry(manifest, event["after"])
    assert evaluate(manifest, policy, history, foundation, catalog) == []
    assert all(x["operational_status"] == "NO_GO" for x in manifest["entries"])


def test_accepted_event_requires_review_metadata():
    manifest, policy, history, foundation, catalog = sources()
    event = accepted_event(sample())
    event["review"]["decision"] = "OPERATIONAL_APPROVED"
    history["events"].append(event)
    replace_entry(manifest, event["after"])
    errors = evaluate(manifest, policy, history, foundation, catalog)
    assert any("cannot authorize" in error for error in errors)


def test_operational_activation_never_follows_promotion():
    manifest, policy, history, foundation, catalog = sources()
    proposal = sample()
    proposal["after"]["operational_status"] = "ACTIVE"
    errors = evaluate(manifest, policy, history, foundation, catalog, proposal)
    assert any("operational status cannot change" in error for error in errors)


def test_shortcut_promotion_is_blocked():
    manifest, policy, history, foundation, catalog = sources()
    proposal = sample()
    proposal["change_type"] = "PROMOTE"
    proposal["from_maturity"] = "SOURCE_TESTED"
    proposal["to_maturity"] = "VISION"
    errors = evaluate(manifest, policy, history, foundation, catalog, proposal)
    assert any("disallowed lifecycle transition" in error for error in errors)


def test_policy_cannot_add_direct_vision_to_source_tested():
    manifest, policy, history, foundation, catalog = sources()
    policy["change_types"]["PROMOTE"]["allowed_pairs"].append(
        ["VISION", "SOURCE_TESTED"]
    )
    errors = evaluate(manifest, policy, history, foundation, catalog)
    assert any("transition policy changed" in error for error in errors)


def test_missing_negative_test_or_module_is_blocked():
    manifest, policy, history, foundation, catalog = sources()
    proposal = sample()
    proposal["evidence"]["negative_test_paths"] = []
    proposal["evidence"]["source_paths"] = ["apps/api/app/does_not_exist.py"]
    errors = evaluate(manifest, policy, history, foundation, catalog, proposal)
    assert any("positive test, negative test and source path" in error for error in errors)


def test_stale_dependency_assessment_is_rejected():
    manifest, policy, history, foundation, catalog = sources()
    proposal = sample()
    proposal["dependency_assessments"][0]["current_maturity"] = "VISION"
    errors = evaluate(manifest, policy, history, foundation, catalog, proposal)
    assert any("dependency maturity review is stale" in error for error in errors)


def test_missing_security_control_review_is_rejected():
    manifest, policy, history, foundation, catalog = sources()
    proposal = sample()
    proposal["control_assessments"].pop()
    errors = evaluate(manifest, policy, history, foundation, catalog, proposal)
    assert any("every security control requires one review" in error for error in errors)


def test_unreviewed_gate_change_cannot_be_bundled():
    manifest, policy, history, foundation, catalog = sources()
    proposal = sample()
    proposal["after"]["unmet_release_gates"].remove("F09")
    errors = evaluate(manifest, policy, history, foundation, catalog, proposal)
    assert any("Foundation gate state cannot change" in error for error in errors)


def test_reviewed_downgrade_may_archive_but_not_keep_evidence():
    manifest, policy, history, foundation, catalog = sources()
    proposal = sample()
    proposal["change_type"] = "DOWNGRADE"
    proposal["to_maturity"] = "VISION"
    proposal["after"]["maturity"] = "VISION"
    proposal["after"]["modules"] = []
    proposal["after"]["verification_evidence"] = []
    proposal["after"]["implementation_scope"] = (
        "Source reclassified to a concept after negative security review."
    )
    proposal["after"]["known_limitations"] = (
        "No confirmed source proof remains for this feature or its operation."
    )
    proposal["evidence"]["scope_note"] = (
        "Existing source code no longer proves the previously claimed capability."
    )
    errors = evaluate(manifest, policy, history, foundation, catalog, proposal)
    assert errors == []


def test_history_replay_rejects_unsequenced_event():
    manifest, policy, history, foundation, catalog = sources()
    event = accepted_event(sample())
    event["event_id"] = "LCE-0008"
    history["events"].append(event)
    replace_entry(manifest, event["after"])
    errors = evaluate(manifest, policy, history, foundation, catalog)
    assert any("sequential" in error for error in errors)


def test_promotion_with_no_relevant_source_evidence_is_blocked():
    manifest, policy, history, foundation, catalog = sources()
    proposal = sample()
    proposal["capability_id"] = "CAP-ISLAMIC"
    proposal["change_type"] = "PROMOTE"
    proposal["from_maturity"] = "VISION"
    proposal["to_maturity"] = "SOURCE_CANDIDATE"
    proposal["after"] = copy.deepcopy(next(
        x for x in manifest["entries"] if x["id"] == "CAP-ISLAMIC"
    ))
    proposal["after"]["maturity"] = "SOURCE_CANDIDATE"
    proposal["after"]["next_acceptance"] = "Needs genuinely reviewed linked code and tests."
    proposal["dependency_assessments"] = [
        {"id": dep, "current_maturity": next(
            x["maturity"] for x in manifest["entries"] if x["id"] == dep
        ), "impact": "Unreleased upstream boundary remains unverified."}
        for dep in proposal["after"]["depends_on"]
    ]
    proposal["control_assessments"] = [
        {"id": control, "state": "UNVERIFIED",
         "note": "Independent expert validation remains outstanding."}
        for control in proposal["after"]["security_requirements"]
    ]
    errors = evaluate(manifest, policy, history, foundation, catalog, proposal)
    assert any("insufficient implementation or test" in error for error in errors)
