"""F05: every synthetic DB/worker perimeter override must fail closed."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys

import pytest
import yaml

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/"scripts/verify_f05_isolation_rehearsal.py"
spec=importlib.util.spec_from_file_location("f05_rehearsal_inspector",path)
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)


@pytest.fixture
def source():
    c=yaml.safe_load(mod.YAML.read_text())
    return (c,mod.SQL.read_text(),mod.PROBE.read_text())


def test_current_rehearsal_source_is_sealed(source,tmp_path):
    c,sql,probe=source
    assert mod.inspect(c,sql,probe)==[]
    outcome=mod.build()
    assert outcome["status"]=="SOURCE_POLICY_PASSED_NOT_LIVE_STAGING"
    assert outcome["source_errors"]==[]
    assert all(len(x)==64 for x in outcome["source_sha256"].values())
    assert outcome["production_release_authorized"] is False
    assert outcome["private_staging_provisioned"] is False
    assert outcome["live_branch_protection_verified"] is False
    assert outcome["real_staff_mfa_verified"] is False
    assert outcome["independent_offhost_backup_verified"] is False
    assert outcome["customer_data_used"] is False
    assert outcome["subscription_approved_or_purchased"] is False
    report=tmp_path/"f05.json"
    assert mod.main(["--report",str(report)])==0
    assert mod.main(["--report",str(report),"--require-live-staging"])==1


@pytest.mark.parametrize("mutate,error",[
    (lambda d:d["networks"]["sealed"].update({"internal":False}),
     "unrestricted_network"),
    (lambda d:d["networks"]["sealed"].update({"driver":"host"}),
     "unrestricted_network"),
    (lambda d:d["services"]["postgres"].update({"ports":["5432:5432"]}),
     "published_port_forbidden_postgres"),
    (lambda d:d["services"]["worker"].update({"ports":["8000:8000"]}),
     "published_port_forbidden_worker"),
    (lambda d:d["services"]["worker"].update({"network_mode":"host"}),
     "privileged_network_override_worker"),
    (lambda d:d["services"]["worker"].update({"privileged":True}),
     "privileged_network_override_worker"),
    (lambda d:d["services"]["worker"].update({"user":"0:0"}),
     "worker_must_be_nonroot"),
    (lambda d:d["services"]["worker"].update({"read_only":False}),
     "worker_root_must_be_readonly"),
    (lambda d:d["services"]["worker"].update({"cap_drop":[]}),
     "worker_has_linux_capabilities"),
    (lambda d:d["services"]["worker"].update({"volumes":["/var/run/docker.sock:/var/run/docker.sock"]}),
     "worker_must_not_mount_runtime_or_secrets"),
    (lambda d:d["services"]["worker"].update({"environment":{"MODEL_API_KEY":"fake"}}),
     "worker_must_not_receive_secrets"),
    (lambda d:d["services"]["postgres"]["environment"].update({"POSTGRES_DB":"live_customer"}),
     "external_or_real_db_credentials_detected"),
    (lambda d:d["services"]["worker"].update({"restart":"always"}),
     "restart_forbidden_worker"),
    (lambda d:d["services"]["worker"].update({"profiles":[]}),
     "mandatory_profile_missing_worker"),
    (lambda d:d["services"]["postgres"].update({"profiles":[]}),
     "mandatory_profile_missing_postgres"),
    (lambda d:d["services"]["worker"].update({"pids_limit":10000}),
     "worker_resource_limits"),
    (lambda d:d["services"]["worker"].update({"depends_on":{}}),
     "database_dependency_changed"),
    (lambda d:d["services"]["worker"].update({"image":"node:latest"}),
     "image_not_reviewed_worker"),
])
def test_compose_trust_boundaries_cannot_be_weakened(source,mutate,error):
    c,sql,probe=source
    mutate(c)
    assert error in mod.inspect(c,sql,probe)


@pytest.mark.parametrize("target,snippet,expected",[
    ("sql","ALTER TABLE public.synthetic_stage_events FORCE ROW LEVEL SECURITY;",
     "missing_sql_defense_FORCE_ROW_LEVEL_SECURITY"),
    ("sql","WITH CHECK (tenant_role = CURRENT_USER)",
     "missing_sql_defense_WITH_CHECK_(tenant_role_=_CURRENT_USER)"),
    ("probe","SET ROLE ci_academy",
     "missing_negative_security_probe_SET_ROLE_ci_academy"),
    ("probe","FOREIGN_WRITE",
     "missing_negative_security_probe_FOREIGN_WRITE"),
    ("probe","/proc/net/route",
     "missing_negative_security_probe_/proc/net/route"),
    ("probe","PGHOST=1.1.1.1",
     "missing_negative_security_probe_PGHOST=1.1.1.1"),
])
def test_source_guard_checks_cannot_silently_disappear(source,target,snippet,expected):
    c,sql,probe=source
    if target=="sql":sql=sql.replace(snippet,"")
    else:probe=probe.replace(snippet,"")
    assert expected in mod.inspect(c,sql,probe)
