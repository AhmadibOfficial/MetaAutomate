"""P2 live release NO-GO gate: independent evidence cannot be forged in source."""
from copy import deepcopy
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
module_path = ROOT / "scripts/assess_phase02_operational_exit.py"
spec = spec_from_file_location("p2_operational_assessor", module_path)
assert spec and spec.loader
gate = module_from_spec(spec)
spec.loader.exec_module(gate)


@pytest.fixture
def source_data():
    f = json.loads(gate.FOUNDATION.read_text(encoding="utf-8"))
    p = json.loads(gate.SOURCE.read_text(encoding="utf-8"))
    return f, p


def test_phase02_operational_gate_is_valid_no_go(source_data):
    f, p = source_data
    result = gate.assess(f, p)
    assert result["status"] == "NO_GO"
    assert result["integrity_errors"] == []
    assert result["foundation_verified"] == 3
    assert result["foundation_required"] == 9
    assert result["submitted_phase02_gate_count"] == 0
    assert result["phase02_total_gates"] == 12
    for field in (
        "external_evidence_authenticated", "independent_security_review_verified",
        "private_branch_protection_verified", "real_tenant_identity_verified",
        "real_provider_authorized", "live_recovery_verified",
        "real_customer_pilot_verified", "production_release_authorized",
        "commercial_pilot_authorized", "provider_execution_performed",
        "staging_provisioned",
    ):
        assert result[field] is False


@pytest.mark.parametrize("field,new", [
    ("release_authorized", True),
    ("execution_authorized", True),
    ("commercial_pilot_authorized", True),
    ("no_autonomous_merging", False),
    ("no_autonomous_staging", False),
    ("provider_reads_performed", True),
    ("staging_provisioned", True),
    ("repo_visibility", "public"),
    ("budget_ceiling_authorized", True),
    ("policy", "AUTOMATIC_GO"),
    ("phase", "03"),
])
def test_source_cannot_claim_unauthorized_release(source_data, field, new):
    foundation, ledger = source_data
    ledger[field] = new
    result = gate.assess(foundation, ledger)
    assert result["status"] == "INVALID"
    assert result["production_release_authorized"] is False


def test_unknown_phase02_ids_and_duplicates_rejected(source_data):
    f, p = source_data
    p["gates"][0]["id"] = "P2-G99"
    assert gate.assess(f, p)["status"] == "INVALID"
    f, p = source_data
    p["gates"].append(deepcopy(p["gates"][-1]))
    assert gate.assess(f, p)["status"] == "INVALID"


@pytest.mark.parametrize("status", ["verified", "completed", "GO", "green", True])
def test_cannot_self_attest_verified_status(source_data, status):
    f, p = source_data
    p["gates"][0]["status"] = status
    assert gate.assess(f, p)["status"] == "INVALID"


def test_false_github_branch_protection_evidence_rejected(source_data):
    f, p = source_data
    p["github_protection_observation"]["observation"] = "ENFORCED"
    result = gate.assess(f, p)
    assert result["status"] == "INVALID"
    assert not result["private_branch_protection_verified"]


def test_evidence_requires_two_distinct_reviewer_refs(source_data):
    f, p = source_data
    first = p["gates"][0]
    first["status"] = "evidence-submitted"
    first["owner_attestation"] = {
        "identity": "independent?", "review_reference": "https://example.org/review",
    }
    first["independent_reviewer_attestation"] = first["owner_attestation"].copy()
    first["evidence"] = [{
        "kind": "independent-review",
        "reference": "https://example.org/audit",
        "sha256": "0"*64,
    }]
    r = gate.assess(f, p)
    assert r["status"] == "INVALID"
    assert not r["independent_security_review_verified"]


def test_evidence_is_not_auto_verified_even_with_two_actors(source_data):
    f, p = source_data
    first = p["gates"][0]
    first["status"] = "evidence-submitted"
    first["owner_attestation"] = {
        "identity": "person-one", "review_reference": "https://example.org/owner",
    }
    first["independent_reviewer_attestation"] = {
        "identity": "person-two", "review_reference": "https://example.org/reviewer",
    }
    first["evidence"] = [{
        "kind": "independent-review",
        "reference": "https://example.org/audit",
        "sha256": "a"*64,
    }]
    r = gate.assess(f, p)
    assert r["integrity_errors"] == []
    assert r["submitted_phase02_gate_count"] == 1
    assert r["status"] == "NO_GO"
    assert not r["external_evidence_authenticated"]


def test_even_all_submitted_and_foundation_claimed_does_not_auto_go(source_data):
    f, p = source_data
    for row in f["checks"]:
        row["status"] = "verified"  # tampered/unverified claim, NOT actual proof
    for row in p["gates"]:
        row["status"] = "evidence-submitted"
        row["owner_attestation"] = {
            "identity": "owner-demo", "review_reference": "https://example.org/owner",
        }
        row["independent_reviewer_attestation"] = {
            "identity": "reviewer-demo", "review_reference": "https://example.org/reviewer",
        }
        row["evidence"] = [{
            "kind": "independent-review",
            "reference": "https://example.org/demonstration",
            "sha256": "a"*64,
        }]
    result = gate.assess(f, p)
    assert result["status"] == "EXTERNAL_REVIEW_REQUIRED"
    assert result["production_release_authorized"] is False
    assert result["external_evidence_authenticated"] is False


def test_missing_or_malformed_foundation_denied(source_data):
    _, p = source_data
    r = gate.assess(None, p)
    assert r["status"] == "INVALID"


def test_untrusted_new_fields_cannot_grant_privileges(source_data):
    f, p = source_data
    p["gates"][0]["execution_authorized"] = True
    assert gate.assess(f, p)["status"] == "INVALID"


def test_report_written_and_explicit_production_request_fails_closed(
    source_data, tmp_path, capsys,
):
    report = tmp_path / "operational.json"
    assert gate.main(["--report", str(report)]) == 0
    data = json.loads(report.read_text())
    assert data["status"] == "NO_GO"
    assert not data["production_release_authorized"]
    assert gate.main([
        "--report", str(report), "--require-production-go",
    ]) == 1
    assert "DENIED" in capsys.readouterr().err


def test_source_gate_has_no_network_or_deployment_effects():
    source = module_path.read_text(encoding="utf-8")
    for forbidden in (
        "import requests", "import httpx", "import socket",
        "subprocess", "docker", "terraform apply", "git merge",
        "GitHubApiClient", "import boto", "eval(",
    ):
        assert forbidden not in source



def test_existing_release_report_imports_real_operational_no_go_assessor():
    from importlib.util import module_from_spec, spec_from_file_location
    release_path = ROOT / "scripts/verify_release_gate.py"
    release_spec = spec_from_file_location("p2_release_status", release_path)
    assert release_spec and release_spec.loader
    release = module_from_spec(release_spec)
    release_spec.loader.exec_module(release)
    result = release.read_phase02_operational_status()
    assert result["status"] == "NO_GO"
    assert result["foundation_verified"] == 3
    assert result["production_release_authorized"] is False
    release_source = release_path.read_text(encoding="utf-8")
    assert "'scope': 'CI_SOURCE_EVIDENCE_ONLY'" in release_source
    assert "'phase03_execution_authorized': False" in release_source
