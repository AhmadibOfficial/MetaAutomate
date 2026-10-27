"""Fail-closed connection-target interlock for disposable OIDC CI tests.

This guard prevents accidental use of remote, arbitrary or developer-local
PostgreSQL DSNs. Environment variables are not proof of database provenance:
the CI service still needs an independent isolated-runner acceptance.
"""
import os
from urllib.parse import urlsplit


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

    for label, dsn, expected_user in (
        ("admin", admin_url, "metaautomate"),
        ("runtime", runtime_url, "metaautomate_runtime"),
    ):
        try:
            parsed = urlsplit(dsn)
            valid = (
                parsed.scheme == "postgresql"
                and parsed.hostname in ("localhost", "127.0.0.1")
                and parsed.port == 5432
                and parsed.path == "/metaautomate"
                and parsed.username == expected_user
                and bool(parsed.password)
                and parsed.netloc.count("@") == 1
                and not parsed.query
                and not parsed.fragment
            )
        except (TypeError, ValueError):
            valid = False
        if not valid:
            raise RuntimeError(
                f"OIDC {label} PostgreSQL URL must target the expected loopback-only CI fixture"
            )
