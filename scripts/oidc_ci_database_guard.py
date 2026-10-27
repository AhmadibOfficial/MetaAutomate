"""Fail-closed connection-target interlock for disposable OIDC CI tests.

This guard prevents accidental use of remote, arbitrary or developer-local
PostgreSQL DSNs. Environment variables are not proof of database provenance:
the CI service still needs an independent isolated-runner acceptance.
"""
import os
import re


def require_ci_database_urls(admin_url: str, runtime_url: str, environ=None) -> None:
    """Validate the repository's expected loopback PostgreSQL CI fixture.

    No database or network connection is made by this function.
    """
    env = os.environ if environ is None else environ
    expected = {
        "GITHUB_ACTIONS": "true",
        "CI": "true",
        "GITHUB_REPOSITORY": "AhmadibOfficial/MetaAutomate",
        "RUNNER_ENVIRONMENT": "github-hosted",
    }
    if any(env.get(key) != value for key, value in expected.items()):
        raise RuntimeError("OIDC database integration requires the expected GitHub-hosted CI job")
    if env.get("GITHUB_EVENT_NAME") not in ("push", "pull_request"):
        raise RuntimeError("OIDC database integration requires a reviewed CI event")
    run_id = env.get("GITHUB_RUN_ID", "")
    if not run_id.isascii() or not run_id.isdecimal():
        raise RuntimeError("OIDC database integration requires a GitHub run ID")

    # Require the actual repository workflow and its database test job,
    # not just a generic GitHub Actions environment in another job.
    # These variables remain spoofable; this is accident prevention only.
    if env.get("GITHUB_WORKFLOW") != "MetaAutomate CI" or env.get("GITHUB_JOB") != "test":
        raise RuntimeError("OIDC database integration requires the designated CI test job")
    workflow_ref = env.get("GITHUB_WORKFLOW_REF", "")
    workflow_prefix = "AhmadibOfficial/MetaAutomate/.github/workflows/ci.yml@"
    if not workflow_ref.startswith(workflow_prefix):
        raise RuntimeError("OIDC database integration requires the reviewed CI workflow path")

    # The workflow source ref and event ref must be the *same* allowed
    # GitHub checkout target. Merely accepting any refs/ suffix could allow
    # a synthetic or accidental run on an unrelated feature/tag ref.
    # See .github/workflows/ci.yml trigger filters. These environment
    # strings are still spoofable and do not prove database provenance.
    ref = env.get("GITHUB_REF", "")
    if workflow_ref != workflow_prefix + ref:
        raise RuntimeError("OIDC database integration requires matching CI refs")
    event = env["GITHUB_EVENT_NAME"]
    if event == "push":
        if ref != "refs/heads/main" or env.get("GITHUB_BASE_REF"):
            raise RuntimeError("OIDC database integration requires a main-branch push")
    elif event == "pull_request":
        if (re.fullmatch(r"refs/pull/[1-9][0-9]*/merge", ref, flags=re.ASCII) is None
                or env.get("GITHUB_BASE_REF") not in ("main", "feat/vscode-workspace-v1")):
            raise RuntimeError("OIDC database integration requires an allowed PR merge ref and base")

    # libpq can fill omitted connection parameters from PG* environment
    # variables even when the URL spells out a host. In particular,
    # PGHOSTADDR can select a different network address than localhost.
    # Reject shadow connection settings before opening a connection.
    # CI's PGPASSWORD is intentionally permitted: both URLs supply their
    # own explicit fixture passwords.
    for key in (
        "PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE",
        "PGSYSCONFDIR", "PGOPTIONS",
    ):
        if env.get(key):
            raise RuntimeError(
                "OIDC database integration refuses libpq environment overrides"
            )

    # Only the exact throwaway service credentials and URL spellings in
    # .github/workflows/ci.yml are accepted. Merely checking host/database
    # would also admit a developer DB using different local credentials.
    # Exact string equality avoids URL-parser normalization differences.
    expected_urls = (
        ("admin", admin_url,
         "postgresql://metaautomate:ci_only_password@localhost:5432/metaautomate"),
        ("runtime", runtime_url,
         "postgresql://metaautomate_runtime:ci_runtime_password@localhost:5432/metaautomate"),
    )
    for label, supplied, expected_url in expected_urls:
        if supplied != expected_url:
            raise RuntimeError(
                f"OIDC {label} PostgreSQL URL must exactly match the disposable CI fixture"
            )
