"""P2-03g: staged CAP-BUSINESS source evidence has separate owner review hold."""
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import verify_capability_lifecycle as lifecycle  # noqa: E402
import verify_lifecycle_owner_review as owner_review  # noqa: E402

PROPOSAL = ROOT / "docs/registry/proposals/P2_03F_TRANSPORTATION_EVIDENCE_REFRESH.v1.json"
SECTORS = ROOT / "contracts/domains/v1/cross_sector_workflow_contract.v1.json"


def ctx():
    return lifecycle.load_sources(ROOT)


def proof():
    return json.loads(PROPOSAL.read_text(encoding="utf-8"))


def verify(manifest, policy, history, foundation, catalog):
    return lifecycle.evaluate(manifest, policy, history, foundation, catalog, ROOT)[0]


def test_proposed_source_event_and_manifest_match_exact_prior_packet():
    manifest, policy, history, foundation, catalog, _ = ctx()
    p = proof()
    assert verify(manifest, policy, history, foundation, catalog) == []
    assert len(history["events"]) == 1
    event = history["events"][0]
    assert event["event_id"] == "LCE-0001"
    assert event["capability_id"] == "CAP-BUSINESS"
    assert event["change_type"] == "EVIDENCE_REFRESH"
    assert event["from_maturity"] == event["to_maturity"] == "LOCAL_SYNTHETIC_DEMO"
    current = next(e for e in manifest["entries"] if e["id"] == "CAP-BUSINESS")
    baseline = next(e for e in history["baseline"]["entries"] if e["id"] == "CAP-BUSINESS")
    assert current == p["after"] == event["after"]
    assert len(baseline["modules"]) == 2
    assert len(current["modules"]) == 5
    assert len(baseline["verification_evidence"]) == 2
    assert len(current["verification_evidence"]) == 5
    assert current["catalog_ids"] == baseline["catalog_ids"]
    assert current["security_requirements"] == baseline["security_requirements"]
    assert current["depends_on"] == baseline["depends_on"]
    for key in (
        "capability_id", "change_type", "from_maturity", "to_maturity",
        "motivation", "evidence", "dependency_assessments", "control_assessments"
    ):
        assert event[key] == p[key]
    assert event["review"]["decision"] == "SOURCE_REVIEWED_ONLY"
    assert event["review"]["review_ref"] == owner_review.EXPECTED_PR
    assert event["review"]["separation_statement"] == "NOT_OPERATIONAL_AUTHORIZATION"


def test_draft_requires_explicit_review_and_main_would_reject_pending_marker():
    _, _, history, _, _, _ = ctx()
    status = owner_review.review_status(history)
    assert status["result"] in {"PENDING_OWNER_APPROVAL", "SOURCE_REVIEW_METADATA_PRESENT"}
    assert status["owner_identity_authentication_performed"] is False
    assert status["real_execution_authorized"] is False
    if status["result"] == "PENDING_OWNER_APPROVAL":
        blocked = owner_review.review_status(history, require_owner_review=True)
        assert blocked["result"] == "BLOCKED"
        assert any("PENDING" in x for x in blocked["errors"])
    else:
        assert owner_review.review_status(history, require_owner_review=True)["errors"] == []


def test_unapproved_edit_to_registry_or_event_fails_ledger_replay():
    manifest, policy, history, foundation, catalog, _ = ctx()
    manifest["entries"][0]["known_limitations"] = "Unreviewed extra capability scope"
    assert any("sequential accepted" in x for x in verify(
        manifest, policy, history, foundation, catalog))
    manifest, policy, history, foundation, catalog, _ = ctx()
    history["events"][0]["event_id"] = "LCE-0003"
    assert any("sequential" in x for x in verify(
        manifest, policy, history, foundation, catalog))
    manifest, policy, history, foundation, catalog, _ = ctx()
    history["events"] = []
    assert any("sequential accepted" in x for x in verify(
        manifest, policy, history, foundation, catalog))


def test_runtime_activation_and_foundation_bypass_are_denied():
    manifest, policy, history, foundation, catalog, _ = ctx()
    target = next(e for e in manifest["entries"] if e["id"] == "CAP-BUSINESS")
    target["operational_status"] = "GO"
    assert any("cannot grant real execution" in x for x in verify(
        manifest, policy, history, foundation, catalog))
    manifest, policy, history, foundation, catalog, _ = ctx()
    history["events"][0]["after"]["unmet_release_gates"].remove("F09")
    assert any("Foundation gate state cannot change" in x for x in verify(
        manifest, policy, history, foundation, catalog))
    manifest, policy, history, foundation, catalog, _ = ctx()
    history["events"][0]["review"]["decision"] = "PRODUCTION_APPROVED"
    assert any("cannot authorize customer" in x for x in verify(
        manifest, policy, history, foundation, catalog))


def test_transportation_profile_stays_design_only_and_all_release_gates_blocked():
    manifest, policy, history, foundation, catalog, _ = ctx()
    sectors = json.loads(SECTORS.read_text(encoding="utf-8"))
    p = next(e for e in sectors["sector_profiles"] if e["sector"] == "transportation")
    assert p["readiness"] == "DESIGN_MAPPING_ONLY"
    assert p["source_scenario"] is None
    assert p["execution_available"] is False
    assert sectors["operational_status"] == "NO_GO"
    assert len(manifest["entries"]) == 19
    assert len(catalog) == 33
    assert all(x["lifecycle_status"] == "DRAFT" for x in catalog)
    assert sum(g["status"] == "verified" for g in foundation["checks"]) == 3
    assert all(x["operational_status"] == "NO_GO" for x in manifest["entries"])
