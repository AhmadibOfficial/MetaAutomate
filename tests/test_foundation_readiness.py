"""Foundation exit evidence is a strict no-go register until real-world gates pass."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/operational-core/FOUNDATION_EXIT_EVIDENCE.json"
SCRIPT = ROOT / "scripts/verify_foundation_readiness.py"
spec = importlib.util.spec_from_file_location("foundation_status", SCRIPT)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def load():
    return json.loads(SOURCE.read_text(encoding="utf-8"))


def test_current_foundation_is_no_go_and_only_three_confirmed():
    result = gate.evaluate(load())
    assert result["result"] == "NO_GO"
    assert result["verified"] == 3
    assert result["total"] == 9
    assert [x["id"] for x in result["blockers"]] == [
        "F04", "F05", "F06", "F07", "F08", "F09"]
    assert result["release_authorized"] is False


def test_no_unverified_external_gate_may_be_marked_complete():
    doc = load()
    doc["checks"][3]["status"] = "verified"
    assert gate.evaluate(doc)["result"] == "INVALID"
    assert any("F04" in error for error in gate.evaluate(doc)["integrity_errors"])


def test_even_nine_declared_gates_cannot_grant_release():
    doc = load()
    for entry in doc["checks"][3:]:
        entry["status"] = "verified"
        entry["external_evidence"] = [{
            "kind": "independent-test",
            "reference": "https://evidence.example.invalid/verification"}]
        entry["owner_signoff"] = {
            "identity": "owner",
            "review_reference": "https://evidence.example.invalid/owner"}
        entry["reviewer_signoff"] = {
            "identity": "independent-auditor",
            "review_reference": "https://evidence.example.invalid/auditor"}
    result = gate.evaluate(doc)
    assert result["result"] == "RELEASE_REVIEW_REQUIRED"
    assert result["release_authorized"] is False
    assert result["live_operations_automatically_verified"] is False


def test_missing_or_injected_evidence_is_invalid():
    doc = load()
    doc["checks"][2]["source_path"] = "../outside"
    assert gate.evaluate(doc)["result"] == "INVALID"
    doc = load()
    doc["checks"] = doc["checks"][:-1]
    assert gate.evaluate(doc)["result"] == "INVALID"
    doc = load()
    doc["checks"][0]["status"] = "complete"
    assert gate.evaluate(doc)["result"] == "INVALID"
