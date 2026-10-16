"""P3-08: never self-certify review; strict source parser and denial gates."""
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import subprocess
import sys

import pytest

from app.phase03_contract_audit import (
    CONTRACTS, MAX_LOCAL_CONTRACT_BYTES, OfflineContractDenied,
    audit_local_contracts,
)
from app.phase03_review_readiness import (
    QUEUE, RISK_IDS, EXPECTED_PARENT_SHA,
    ReviewReadinessDenied, build_review_preparation,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/phase03_review_readiness.py"


def _copy(tmp_path):
    for path in (*CONTRACTS.values(), QUEUE):
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / path).read_bytes())
    return tmp_path


def _update(root, name, change):
    path = root / name
    document = json.loads(path.read_text(encoding="utf-8"))
    change(document)
    path.write_text(json.dumps(document), encoding="utf-8")


def test_initial_review_packet_is_pending_and_cannot_mint_permissions():
    r = build_review_preparation(ROOT)
    assert r.parent_source_sha == EXPECTED_PARENT_SHA
    assert r.github_ci_python_passed == 903
    assert r.owner_kali_source_passed == 572
    assert r.reviewer_risks_pending == 10
    assert r.source_contracts_compatible
    assert r.status == "INDEPENDENT_REVIEW_NOT_PERFORMED"
    assert r.decision == "NO_GO"
    assert not r.external_evidence_verified
    assert not r.reviewer_identity_authenticated
    assert not r.private_branch_protection_verified
    assert not r.live_provider_receipt_verified
    assert not r.provider_access_permitted
    assert not r.customer_data_permitted
    assert not r.independent_human_review_completed
    assert not r.production_execution_authorized
    assert not r.merge_authorized
    with pytest.raises(FrozenInstanceError):
        r.merge_authorized = True


@pytest.mark.parametrize("key,value", [
    ("release_decision", "GO"),
    ("merge_authorized", True),
    ("merge_authorized", 0),
    ("review_state", "APPROVED"),
    ("review_state", False),
    ("schema_version", True),
    ("purpose", "SELF_APPROVED"),
])
def test_malformed_or_falsely_approved_review_packet_rejected(tmp_path, key, value):
    root = _copy(tmp_path)
    _update(root, QUEUE, lambda x: x.__setitem__(key, value))
    with pytest.raises(ReviewReadinessDenied):
        build_review_preparation(root)


@pytest.mark.parametrize("key,value", [
    ("reviewed_by_independent_human", True),
    ("review_target_is_parent_source", False),
    ("source_commit", "f"*40),
    ("pr_number", 0),
    ("repository", "fake/repository"),
])
def test_review_target_cannot_fake_provenance(tmp_path, key, value):
    root = _copy(tmp_path)
    _update(root, QUEUE, lambda x: x["review_target"].__setitem__(key, value))
    with pytest.raises(ReviewReadinessDenied):
        build_review_preparation(root)


@pytest.mark.parametrize("key,value", [
    ("github_ci_python_passed", 0),
    ("github_ci_run", 0),
    ("owner_kali_phase03_passed", 0),
    ("owner_kali_provided_not_independent", False),
    ("owner_kali_suites", 8),
])
def test_source_evidence_claim_cannot_be_overridden(tmp_path, key, value):
    root = _copy(tmp_path)
    _update(root, QUEUE, lambda x: x["source_acceptance"].__setitem__(key, value))
    with pytest.raises(ReviewReadinessDenied):
        build_review_preparation(root)


@pytest.mark.parametrize("key,value", [
    ("phase01_verified", 9),
    ("phase01_required", 8),
    ("phase02_operational_approved", True),
    ("phase03_live_execution_authorized", True),
])
def test_foundation_and_execution_gates_stay_no_go(tmp_path, key, value):
    root = _copy(tmp_path)
    _update(root, QUEUE, lambda x: x["foundational_status"].__setitem__(key, value))
    with pytest.raises(ReviewReadinessDenied):
        build_review_preparation(root)


@pytest.mark.parametrize("field,value", [
    ("status", "PASS"),
    ("status", "REVIEWED"),
    ("evidence_provided", True),
    ("evidence_provided", 0),
    ("id", "P3T-99"),
    ("required_external_evidence", ""),
    ("threat", ""),
])
def test_ten_risk_queue_remains_unverified(tmp_path, field, value):
    root = _copy(tmp_path)
    _update(
        root, QUEUE,
        lambda x: x["unverified_tasks"][0].__setitem__(field, value),
    )
    with pytest.raises(ReviewReadinessDenied):
        build_review_preparation(root)


def test_missing_risk_and_reordered_risk_is_denied(tmp_path):
    root = _copy(tmp_path)
    _update(root, QUEUE, lambda x: x["unverified_tasks"].pop())
    with pytest.raises(ReviewReadinessDenied):
        build_review_preparation(root)
    root = _copy(tmp_path)
    _update(root, QUEUE, lambda x: x["unverified_tasks"].reverse())
    with pytest.raises(ReviewReadinessDenied):
        build_review_preparation(root)


@pytest.mark.parametrize("path", [
    QUEUE, "contracts/intelligent/v1/planning.json",
    "contracts/intelligent/v1/developer_tools.json",
])
def test_duplicate_top_level_json_keys_are_refused(tmp_path, path):
    root = _copy(tmp_path)
    target = root / path
    # Last-wins JSON parsers would silently mask the injected field.
    original = target.read_bytes().rstrip()
    assert original.endswith(b"}")
    target.write_bytes(original[:-1] + b',"schema_version":false}\n')
    with pytest.raises((ReviewReadinessDenied, OfflineContractDenied)):
        if path == QUEUE:
            build_review_preparation(root)
        else:
            audit_local_contracts(root)


def test_nested_duplicate_json_key_refused(tmp_path):
    root = _copy(tmp_path)
    target = root / QUEUE
    src = target.read_text()
    src = src.replace('"status": "PENDING_INDEPENDENT_REVIEW"',
                      '"status": "PENDING_INDEPENDENT_REVIEW", "status": "REVIEWED"', 1)
    target.write_text(src)
    with pytest.raises(ReviewReadinessDenied):
        build_review_preparation(root)


@pytest.mark.parametrize("text", ['{"ok":NaN}', '{"ok":Infinity}', '{"ok":-Infinity}'])
def test_nonstandard_json_numbers_refused(tmp_path, text):
    root = _copy(tmp_path)
    (root / QUEUE).write_text(text)
    with pytest.raises(ReviewReadinessDenied):
        build_review_preparation(root)


def test_oversized_contract_denied_before_parsing(tmp_path):
    root = _copy(tmp_path)
    target = root / CONTRACTS["planning"]
    target.write_bytes(b" " * (MAX_LOCAL_CONTRACT_BYTES + 1))
    with pytest.raises(OfflineContractDenied):
        audit_local_contracts(root)


def test_symlinked_source_contract_cannot_escape_local_tree(tmp_path):
    root = _copy(tmp_path)
    target = root / CONTRACTS["planning"]
    outside = tmp_path.parent / "example-local-contract.json"
    outside.write_bytes(target.read_bytes())
    target.unlink()
    target.symlink_to(outside)
    with pytest.raises(OfflineContractDenied):
        audit_local_contracts(root)


def test_contract_audit_denies_malformed_utf8(tmp_path):
    root = _copy(tmp_path)
    (root / CONTRACTS["planning"]).write_bytes(b"\xff\xfe")
    with pytest.raises(OfflineContractDenied):
        audit_local_contracts(root)


def test_review_readiness_cli_prints_no_go_only():
    p = subprocess.run(
        [sys.executable, str(SCRIPT),
         "--expect-reviewed-source", EXPECTED_PARENT_SHA],
        capture_output=True, text=True, timeout=20, check=False,
    )
    assert p.returncode == 0, p.stderr
    report = json.loads(p.stdout)
    assert report["decision"] == "NO_GO"
    assert report["reviewer_risks_pending"] == len(RISK_IDS)
    assert report["merge_authorized"] is False
    assert report["independent_human_review_completed"] is False


@pytest.mark.parametrize("args", [
    [], ["--expect-reviewed-source", "0"*40],
    ["--expect-reviewed-source", EXPECTED_PARENT_SHA, "--approve"],
    ["--expect-reviewed-source", EXPECTED_PARENT_SHA, "--execute"],
])
def test_review_cli_has_no_approval_or_execution_switch(args):
    p = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=20, check=False,
    )
    assert p.returncode != 0
    assert p.stdout == ""


def test_review_readiness_module_has_no_provider_or_deploy_wiring():
    src = (ROOT / "apps/api/app/phase03_review_readiness.py").read_text()
    main = (ROOT / "apps/api/app/main.py").read_text()
    assert "phase03_review_readiness" not in main
    for forbidden in ("APIRouter(", "httpx", "requests.", "urllib.request",
                      "socket.socket(", "subprocess.", "openai.", "psycopg",
                      "redis.", "urlopen("):
        assert forbidden not in src
