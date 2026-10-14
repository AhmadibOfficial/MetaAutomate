"""Phase 02 human release evidence handoff is never an automated grant."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "contracts/engineering/phase02_external_acceptance_tasks.json"


def test_strict_gate_ids_and_unambiguous_exit_criteria():
    obj = json.loads(LEDGER.read_text(encoding="utf-8"))
    assert obj["schema_version"] == 1
    assert obj["project"] == "MetaAutomate"
    assert obj["phase"] == "02"
    assert obj["scope"] == "HUMAN_OPERATED_ACCEPTANCE_ONLY"
    assert obj["default_release_decision"] == "NO_GO"
    assert obj["machine_can_authorize_execution"] is False
    assert obj["foundation_verified_last_observed"] == 3
    assert obj["foundation_required"] == 9
    assert obj["source_evidence"]["scope"] == "SOURCE_ONLY_NOT_DEPLOYMENT"
    assert obj["execution_authorized"] is False
    assert obj["staging_authorized"] is False
    assert obj["commercial_pilot_authorized"] is False
    gates = obj["gates"]
    assert [g["id"] for g in gates] == [f"P2-G{i:02}" for i in range(1, 13)]
    assert len({g["track"] for g in gates}) == 12
    assert all(g["status"] == "blocked" for g in gates)
    assert all(g["independent_review_verified"] is False for g in gates)
    assert all(g["evidence_reference"] is None for g in gates)
    assert all(g["authorized_to_perform_live_actions"] is False for g in gates)
    for row in gates:
        assert len(row["required_acceptance"]) > 35
        assert len(row["required_evidence"]) > 20
        assert len(row["accountability"]) > 15
    assert "cannot grant authorization" in obj["manual_release_rule"]


def test_offline_validator_unrouted_and_no_external_fetch():
    module = ROOT / "apps/api/app/provider_read_boundary.py"
    assert module.is_file()
    main = (ROOT / "apps/api/app/main.py").read_text()
    assert "provider_read_boundary" not in main
    source = module.read_text()
    assert "network_request_performed: bool = False" in source
    assert "execution_authorized: bool = False" in source
    forbidden = ("httpx", "requests.get(", "APIRouter(", "urllib",
                 "socket.socket(", "psycopg", "subprocess.run(", "os.system(")
    for expression in forbidden:
        assert expression not in source
