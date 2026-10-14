#!/usr/bin/env python3
"""Read-only source contract: never deploys, starts Docker, or touches data.

Passing means static source controls, NOT private-cloud readiness or release approval.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "deploy" / "staging" / "compose.yaml"
DEFAULT_REPORT = ROOT / ".buildlog" / "validation" / "staging-contract.json"
PROFILE = ["owner-approved-staging"]


def required_parameter(value, variable: str) -> bool:
    return (isinstance(value, str) and
            value.startswith(chr(36) + "{" + variable + ":?") and
            value.endswith("}"))


def check(config: object) -> list[str]:
    errors: list[str] = []

    def require(condition: bool, code: str) -> None:
        if not condition:
            errors.append(code)

    if not isinstance(config, dict):
        return ["invalid_compose_document"]
    require(set(config) == {"name", "services", "networks", "volumes"},
            "unexpected_top_level_compose_field")
    require(config.get("name") == "metaautomate-private-staging",
            "staging_project_not_isolated")
    services = config.get("services")
    if not isinstance(services, dict) or set(services) != {"postgres", "api"}:
        return errors + ["unexpected_services"]
    db, api = services["postgres"], services["api"]
    if not isinstance(db, dict) or not isinstance(api, dict):
        return errors + ["invalid_services"]

    for name, svc in (("postgres", db), ("api", api)):
        require(svc.get("profiles") == PROFILE, f"{name}_manual_profile_required")
        require(svc.get("restart") == "no", f"{name}_must_not_autorestart")
        require(svc.get("privileged") is not True, f"{name}_privileged_forbidden")
        require(svc.get("network_mode") is None, f"{name}_network_mode_forbidden")
        require("no-new-privileges:true" in svc.get("security_opt", []),
                f"{name}_no_new_privileges_required")

    require(db.get("image") == "postgres:16-alpine", "postgres_image_not_reviewed")
    require("ports" not in db and "expose" not in db,
            "postgres_must_have_no_published_ports")
    require(db.get("networks") == ["db"], "postgres_must_use_internal_network_only")
    require(db.get("volumes") == ["staging_pgdata:/var/lib/postgresql/data"],
            "staging_database_volume_must_be_unique")
    db_env = db.get("environment")
    if not isinstance(db_env, dict):
        return errors + ["postgres_environment_missing"]
    require(db_env.get("POSTGRES_DB") == "metaautomate_staging",
            "staging_database_name_not_isolated")
    require(db_env.get("POSTGRES_USER") == "metaautomate_staging_admin",
            "staging_database_admin_not_isolated")
    require(set(db_env) == {"POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD"},
            "postgres_unreviewed_environment_field")
    require(required_parameter(db_env.get("POSTGRES_PASSWORD"), "STAGING_POSTGRES_PASSWORD"),
            "staging_admin_secret_must_be_required")
    require(isinstance(db.get("healthcheck"), dict), "postgres_healthcheck_missing")

    require(api.get("build") == {"context": "../..",
                                  "dockerfile": "apps/api/Dockerfile.prod"},
            "api_must_use_reviewed_nonroot_prod_image")
    require("image" not in api and "volumes" not in api,
            "api_image_or_writable_bind_override_forbidden")
    require(api.get("ports") == ["127.0.0.1:8081:8000"],
            "api_must_bind_loopback_only")
    require(api.get("networks") == ["db", "egress"],
            "api_must_keep_database_internal_and_egress_separate")
    require(api.get("depends_on") == {"postgres": {"condition": "service_healthy"}},
            "postgres_health_dependency_missing")
    require(api.get("read_only") is True, "api_rootfs_must_be_readonly")
    require(api.get("user") == "10001:10001", "api_must_not_run_as_root")
    require(api.get("cap_drop") == ["ALL"], "api_capabilities_must_be_dropped")
    require(isinstance(api.get("tmpfs"), list) and
            len(api["tmpfs"]) == 1 and api["tmpfs"][0].startswith("/tmp:rw,noexec,nosuid,"),
            "api_requires_restricted_tmpfs")
    require(isinstance(api.get("healthcheck"), dict), "api_healthcheck_missing")

    env = api.get("environment")
    if not isinstance(env, dict):
        return errors + ["api_environment_missing"]
    require(env.get("WORKSPACE_AUTH_MODE") == "oidc", "private_staging_must_use_oidc")
    require(str(env.get("WORKSPACE_COOKIE_SECURE")) == "1",
            "private_staging_requires_secure_cookies")
    require(env.get("WORKSPACE_WEB_ROOT") == "/srv/metaautomate/web",
            "private_web_root_changed")
    require("DATABASE_URL" not in env and "REGISTRY_READ_API_KEY" not in env,
            "privileged_development_secrets_forbidden")
    substitutions = {
        "WORKSPACE_ORIGIN": "STAGING_WORKSPACE_ORIGIN",
        "APP_DATABASE_URL": "STAGING_APP_DATABASE_URL",
        "OIDC_ISSUER": "STAGING_OIDC_ISSUER",
        "OIDC_CLIENT_ID": "STAGING_OIDC_CLIENT_ID",
        "OIDC_CLIENT_SECRET": "STAGING_OIDC_CLIENT_SECRET",
        "OIDC_REDIRECT_URI": "STAGING_OIDC_REDIRECT_URI",
        "OIDC_STATE_SECRET": "STAGING_OIDC_STATE_SECRET",
    }
    expected_env = set(substitutions) | {
        "WORKSPACE_AUTH_MODE", "WORKSPACE_COOKIE_SECURE", "WORKSPACE_WEB_ROOT"}
    require(set(env) == expected_env, "api_environment_contains_unreviewed_fields")
    for key, variable in substitutions.items():
        require(required_parameter(env.get(key), variable),
                "staging_parameter_required_" + key.lower())
    networks = config.get("networks")
    require(isinstance(networks, dict) and set(networks) == {"db", "egress"}
            and networks["db"] == {"internal": True} and networks["egress"] == {},
            "staging_network_perimeter_invalid")
    require(config.get("volumes") == {"staging_pgdata": {}},
            "unexpected_staging_volumes")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        config = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
        errors = check(config)
    except (OSError, yaml.YAMLError):
        errors = ["compose_missing_or_invalid_yaml"]
    report = {
        "schema_version": 1,
        "gate": "private-staging-source-contract",
        "result": "SOURCE_PASS" if not errors else "FAIL",
        "errors": errors,
        "deployment_authorized": False,
        "live_private_perimeter_verified": False,
        "real_oidc_mfa_verified": False,
        "migration_012_executed": False,
        "customer_access_enabled": False,
    }
    try:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                               encoding="utf-8")
    except OSError:
        print("FAIL: Could not save staging source gate report", file=sys.stderr)
        return 1
    if errors:
        print("FAIL: Private staging source contract: " + ", ".join(errors))
        return 1
    print("SOURCE_PASS: isolated staging template meets reviewed static boundaries.")
    print("NOT READY: no cloud/edge/IdP/MFA/backup verified; no deployment authorized.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
