"""Transportation source-evidence proposal: never apply to lifecycle/registry."""
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_capability_lifecycle as lc  # noqa: E402

PROPOSAL = ROOT / "docs/registry/proposals/P2_03F_TRANSPORTATION_EVIDENCE_REFRESH.v1.json"
CONTRACT = ROOT / "contracts/domains/v1/cross_sector_workflow_contract.v1.json"


def read_proposal():
    return json.loads(PROPOSAL.read_text(encoding="utf-8"))


def sources():
    return lc.load_sources(ROOT)


def historical_before_acceptance():
    """Exercise the old proposal against its actual baseline, not the new accepted state."""
    manifest, policy, history, foundation, catalog, root = sources()
    assert len(history["events"]) == 1
    assert history["events"][0]["event_id"] == "LCE-0001"
    original = copy.deepcopy(next(
        x for x in history["baseline"]["entries"] if x["id"] == "CAP-BUSINESS"
    ))
    manifest["entries"] = [
        original if entry["id"] == "CAP-BUSINESS" else entry
        for entry in manifest["entries"]
    ]
    history["events"] = []
    return manifest, policy, history, foundation, catalog, root


def errors_for(proposal):
    return lc.evaluate(*historical_before_acceptance(), proposal)[0]


def test_transportation_proposal_is_historically_valid_and_event_replay_matches():
    manifest, policy, history, foundation, catalog, root = sources()
    original_manifest = copy.deepcopy(manifest)
    original_history = copy.deepcopy(history)
    proposal = read_proposal()
    assert lc.evaluate(manifest, policy, history, foundation, catalog, root)[0] == []
    assert errors_for(proposal) == []
    assert manifest == original_manifest
    assert history == original_history
    assert proposal["example_only"] is False
    assert proposal["change_type"] == "EVIDENCE_REFRESH"
    assert proposal["from_maturity"] == proposal["to_maturity"] == "LOCAL_SYNTHETIC_DEMO"
    assert proposal["after"]["operational_status"] == "NO_GO"
    assert proposal["capability_id"] == proposal["after"]["id"] == "CAP-BUSINESS"
    assert len(history["events"]) == 1
    current = next(x for x in manifest["entries"] if x["id"] == "CAP-BUSINESS")
    assert current == proposal["after"]
    baseline = next(x for x in history["baseline"]["entries"] if x["id"] == "CAP-BUSINESS")
    assert len(baseline["modules"]) == 2
    assert len(current["modules"]) == 5
    assert current["maturity"] == baseline["maturity"]
    assert sum(x["status"] == "verified" for x in foundation["checks"]) == 3


def test_proposal_has_full_transport_source_tests_and_controls():
    p = read_proposal()
    evidence = p["evidence"]
    assert evidence["ci_run_url"] == "https://github.com/AhmadibOfficial/MetaAutomate/actions/runs/38850185421"
    assert "tests/test_synthetic_transportation.py" in evidence["positive_test_paths"]
    assert "tests/test_synthetic_transportation.py" in evidence["negative_test_paths"]
    assert "tests/test_cross_sector_workflow_contract.py" in evidence["negative_test_paths"]
    assert "apps/api/app/synthetic_transportation.py" in evidence["source_paths"]
    assert all(Path(ROOT / filename).is_file() for filename in evidence["source_paths"])
    assert {x["id"]: x["state"] for x in p["control_assessments"]} == {
        "EXPLICIT_APPROVAL": "DESIGNED",
        "EXTERNAL_ACTION_DENY": "SOURCE_TESTED",
        "TENANT_ISOLATION": "UNVERIFIED",
        "AUDIT_TRAIL": "UNVERIFIED",
    }
    assert {x["id"] for x in p["dependency_assessments"]} == {"SYS-DATA", "SYS-INTEGRATIONS"}


def test_transportation_cross_sector_profile_stays_design_only():
    p = read_proposal()
    contract = json.loads(CONTRACT.read_text())
    sector = next(x for x in contract["sector_profiles"] if x["sector"] == "transportation")
    assert sector["readiness"] == "DESIGN_MAPPING_ONLY"
    assert sector["source_scenario"] is None
    assert sector["execution_available"] is False
    assert contract["operational_status"] == "NO_GO"
    assert p["after"]["operational_status"] == "NO_GO"
    assert set(p["after"]["unmet_release_gates"]) == {"F04", "F05", "F06", "F07", "F08", "F09"}


def test_changing_maturity_without_review_is_rejected():
    p = read_proposal()
    p["to_maturity"] = p["after"]["maturity"] = "SOURCE_TESTED"
    assert any("disallowed lifecycle transition" in e for e in errors_for(p))


def test_operational_activation_or_gate_waiver_is_rejected():
    p = read_proposal()
    p["after"]["operational_status"] = "GO"
    assert any("operational status cannot change" in e for e in errors_for(p))
    p = read_proposal()
    p["after"]["unmet_release_gates"].remove("F09")
    assert any("Foundation gate state cannot change" in e for e in errors_for(p))


def test_missing_transport_evidence_rejected():
    p = read_proposal()
    p["after"]["verification_evidence"] = [
        e for e in p["after"]["verification_evidence"]
        if e["path"] != "tests/test_synthetic_transportation.py"
    ]
    assert any("positive/negative test not in scoped" in e for e in errors_for(p))


def test_missing_dependency_and_control_assessments_rejected():
    p = read_proposal()
    p["dependency_assessments"].pop()
    assert any("every dependency requires one review" in e for e in errors_for(p))
    p = read_proposal()
    p["control_assessments"].pop()
    assert any("every security control requires one review" in e for e in errors_for(p))


def test_wrong_ci_url_rejected_and_no_source_fields_cannot_gain_permissions():
    p = read_proposal()
    p["evidence"]["ci_run_url"] = "https://example.com/not-a-verified-run"
    assert any("optional CI URL is malformed" in e for e in errors_for(p))
    p = read_proposal()
    p["after"]["enable_customer_dispatch"] = True
    assert any("unexpected/missing entry fields" in e for e in errors_for(p))
