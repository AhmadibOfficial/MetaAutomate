#!/usr/bin/env python3
"""Validate opt-in F05 disposable two-tenant isolation rehearsal, not live staging."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import yaml

ROOT=Path(__file__).resolve().parents[1]
YAML=ROOT/"deploy/staging/compose.isolation-rehearsal.yaml"
SQL=ROOT/"deploy/staging/rehearsal/seed.sql"
PROBE=ROOT/"deploy/staging/rehearsal/probe.sh"
OUTPUT=ROOT/"artifacts/validation/f05-isolation-rehearsal.json"
PROFILE=["source-rehearsal-only"]


def inspect(doc:object,seed:str,probe:str)->list[str]:
    problems=[]
    def need(condition:bool,message:str)->None:
        if not condition:problems.append(message)
    if type(doc) is not dict:
        return ["invalid_compose"]
    need(set(doc)=={"name","services","networks","volumes"},
         "top_level_configuration_drifts")
    need(doc.get("name")=="metaautomate-f05-rehearsal","non_disposable_project")
    networks=doc.get("networks")
    need(networks=={"sealed":{"driver":"bridge","internal":True}},
         "unrestricted_network")
    need(doc.get("volumes")=={"ephemeral_pgdata":{}},
         "unreviewed_volume")
    services=doc.get("services")
    if type(services) is not dict or set(services)!={"postgres","worker"}:
        return problems+["unreviewed_service"]
    for name,svc in services.items():
        if type(svc) is not dict:
            problems.append("invalid_"+name);continue
        need(svc.get("profiles")==PROFILE,"mandatory_profile_missing_"+name)
        need(svc.get("networks")==["sealed"],"network_is_not_internal_"+name)
        need(svc.get("restart")=="no","restart_forbidden_"+name)
        need("ports" not in svc and "expose" not in svc,
             "published_port_forbidden_"+name)
        need("privileged" not in svc and "network_mode" not in svc,
             "privileged_network_override_"+name)
        need("no-new-privileges:true" in svc.get("security_opt",[]),
             "new_privileges_forbidden_"+name)
        need(svc.get("image")=="postgres:16-alpine","image_not_reviewed_"+name)
    db=services["postgres"]
    worker=services["worker"]
    if type(db) is dict:
        need(db.get("environment")=={
            "POSTGRES_DB":"f05_ci_rehearsal",
            "POSTGRES_USER":"ci_stage_admin",
            "POSTGRES_PASSWORD":"ci_dummy_admin_only",
        },"external_or_real_db_credentials_detected")
        need(db.get("volumes")==[
            "ephemeral_pgdata:/var/lib/postgresql/data",
            "./rehearsal/seed.sql:/docker-entrypoint-initdb.d/seed.sql:ro",
        ],"unreviewed_database_storage")
        need("NET_RAW" in db.get("cap_drop",[]),
             "database_raw_network_capability_forbidden")
        need(type(db.get("healthcheck")) is dict,
             "database_health_check_missing")
    if type(worker) is dict:
        need(worker.get("read_only") is True,
             "worker_root_must_be_readonly")
        need(worker.get("user")=="65534:65534",
             "worker_must_be_nonroot")
        need(worker.get("cap_drop")==["ALL"],"worker_has_linux_capabilities")
        need(worker.get("depends_on")=={
            "postgres":{"condition":"service_healthy"},
        },"database_dependency_changed")
        need(worker.get("volumes")==[
            "./rehearsal/probe.sh:/rehearsal/probe.sh:ro",
        ],"worker_must_not_mount_runtime_or_secrets")
        need(worker.get("command")==[
            "/bin/sh","/rehearsal/probe.sh",
        ],"worker_must_run_scoped_probe_only")
        need(worker.get("tmpfs")==[
            "/tmp:rw,noexec,nosuid,size=16m",
        ],"worker_tmpfs_hardened")
        need(worker.get("pids_limit")==32 and
             worker.get("mem_limit")=="128m" and
             worker.get("cpus")==1,
             "worker_resource_limits")
        need("environment" not in worker,"worker_must_not_receive_secrets")
    for token in (
        "ENABLE ROW LEVEL SECURITY",
        "FORCE ROW LEVEL SECURITY",
        "USING (tenant_role = CURRENT_USER)",
        "WITH CHECK (tenant_role = CURRENT_USER)",
        "NOSUPERUSER",
        "NOCREATEDB",
        "NOCREATEROLE",
        "academy_demo",
        "bespoke_demo",
    ):
        need(token in seed,"missing_sql_defense_"+token.replace(" ","_"))
    for token in (
        "SELECT workspace FROM public.synthetic_stage_events",
        "SET ROLE ci_academy",
        "FOREIGN_WRITE",
        "/proc/net/route",
        "/proc/net/ipv6_route",
        "PGHOST=1.1.1.1",
        "nonroot",
    ):
        need(token in probe,"missing_negative_security_probe_"+token.replace(" ","_"))
    need("https://" not in probe and "curl " not in probe,
         "outbound_download_forbidden_in_ci_worker")
    return problems


def build()->dict:
    raw_yaml=YAML.read_bytes()
    raw_sql=SQL.read_bytes()
    raw_probe=PROBE.read_bytes()
    if any(len(s)>32_000 for s in (raw_yaml,raw_sql,raw_probe)):
        raise ValueError("Unbounded rehearsal configuration")
    doc=yaml.safe_load(raw_yaml.decode("utf-8"))
    errors=inspect(doc,raw_sql.decode("utf-8"),raw_probe.decode("utf-8"))
    return {
        "schema_version":1,
        "gate":"F05_DISPOSABLE_REHEARSAL",
        "status":"SOURCE_POLICY_PASSED_NOT_LIVE_STAGING" if not errors else
                 "SOURCE_POLICY_FAILED",
        "source_errors":errors,
        "source_sha256":{
            "compose":sha256(raw_yaml).hexdigest(),
            "seed":sha256(raw_sql).hexdigest(),
            "probe":sha256(raw_probe).hexdigest(),
        },
        "live_branch_protection_verified":False,
        "private_staging_provisioned":False,
        "real_staff_mfa_verified":False,
        "customer_data_used":False,
        "external_model_inference":False,
        "subscription_approved_or_purchased":False,
        "independent_offhost_backup_verified":False,
        "production_release_authorized":False,
    }


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--report",type=Path,default=OUTPUT)
    parser.add_argument("--require-live-staging",action="store_true")
    args=parser.parse_args(argv)
    try:
        result=build()
    except (OSError,ValueError,UnicodeDecodeError,yaml.YAMLError) as exc:
        print("FAIL: F05 source inspection incomplete",file=sys.stderr)
        return 1
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("F05: "+result["status"])
    if result["source_errors"]:
        for error in result["source_errors"]:print("FAIL: "+error)
        return 1
    if args.require_live_staging:
        print("DENIED: internal disposable CI is NOT independently secured staging",
              file=sys.stderr)
        return 1
    return 0


if __name__=="__main__":
    raise SystemExit(main())
