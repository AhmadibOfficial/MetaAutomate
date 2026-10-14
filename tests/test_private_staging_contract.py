"""Static private staging safety tests. No Docker, cloud or database access."""
from copy import deepcopy
import importlib.util
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "staging_contract", ROOT / "scripts" / "verify_private_staging_contract.py")
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)

BASE = yaml.safe_load((ROOT / "deploy" / "staging" / "compose.yaml").read_text())


def test_reviewed_template_is_source_safe():
    assert gate.check(BASE) == []


@pytest.mark.parametrize(("service", "field", "value", "code"), [
    ("postgres", "ports", ["0.0.0.0:5432:5432"], "postgres_must_have_no_published_ports"),
    ("api", "ports", ["0.0.0.0:8081:8000"], "api_must_bind_loopback_only"),
    ("api", "profiles", [], "api_manual_profile_required"),
    ("postgres", "profiles", [], "postgres_manual_profile_required"),
    ("api", "read_only", False, "api_rootfs_must_be_readonly"),
    ("api", "privileged", True, "api_privileged_forbidden"),
    ("api", "user", "0:0", "api_must_not_run_as_root"),
    ("api", "cap_drop", [], "api_capabilities_must_be_dropped"),
])
def test_gate_blocks_unsafe_changes(service, field, value, code):
    changed = deepcopy(BASE)
    changed["services"][service][field] = value
    assert code in gate.check(changed)


def test_gate_rejects_dev_keys_and_embedded_secrets():
    changed = deepcopy(BASE)
    changed["services"]["api"]["environment"]["WORKSPACE_AUTH_MODE"] = "dev_key"
    assert "private_staging_must_use_oidc" in gate.check(changed)
    changed = deepcopy(BASE)
    changed["services"]["api"]["environment"]["OIDC_CLIENT_SECRET"] = "hardcoded-secret"
    assert "staging_parameter_required_oidc_client_secret" in gate.check(changed)
    changed = deepcopy(BASE)
    changed["services"]["postgres"]["environment"]["POSTGRES_PASSWORD"] = "hardcoded"
    assert "staging_admin_secret_must_be_required" in gate.check(changed)


def test_gate_rejects_live_db_and_network_expansion():
    changed = deepcopy(BASE)
    changed["services"]["postgres"]["environment"]["POSTGRES_DB"] = "metaautomate"
    assert "staging_database_name_not_isolated" in gate.check(changed)
    changed = deepcopy(BASE)
    changed["networks"]["db"]["internal"] = False
    assert "staging_network_perimeter_invalid" in gate.check(changed)
    changed = deepcopy(BASE)
    changed["services"]["backup_job"] = {"image": "postgres:16"}
    assert "unexpected_services" in gate.check(changed)
