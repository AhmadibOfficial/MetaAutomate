"""Private OIDC v2 source contracts; no network, DB or migration changes."""
from pathlib import Path
import runpy

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_oidc_migration_after_operational_core_without_collision():
    assessment = ROOT / "database/migrations/011_operational_assessments.sql"
    extension = ROOT / "database/migrations/012_oidc_identities.sql"
    assert assessment.exists() and extension.exists()
    sql = extension.read_text()
    assert "CREATE TABLE oidc_identities" in sql
    assert "ALTER TABLE workspace_sessions" in sql
    assert "app.create_oidc_workspace_session" in sql
    assert "GRANT EXECUTE ON FUNCTION app.create_oidc_workspace_session" in sql
    assert "REVOKE ALL ON oidc_identities FROM metaautomate_runtime" in sql


def test_private_mode_requires_secure_identity_and_restricted_runtime():
    main = (ROOT / "apps/api/app/main.py").read_text()
    auth = (ROOT / "apps/api/app/workspace_auth.py").read_text()
    assert 'WORKSPACE_AUTH_MODE' in main
    assert 'WORKSPACE_COOKIE_SECURE' in main
    assert 'APP_DATABASE_URL' in main and 'metaautomate_runtime' in main
    assert 'Privileged DATABASE_URL prohibited' in main
    assert 'app.include_router(assessment_router)' in main
    assert 'if auth_mode() != "dev_key"' in auth
    assert '"code_challenge_method": "S256"' in auth


def test_production_container_defaults_to_oidc_and_no_root():
    dockerfile = (ROOT / "apps/api/Dockerfile.prod").read_text()
    assert "WORKSPACE_AUTH_MODE=oidc" in dockerfile
    assert "WORKSPACE_COOKIE_SECURE=1" in dockerfile
    assert "USER meta" in dockerfile
    assert "DATABASE_URL=" not in dockerfile
    assert "COPY --chown=meta:meta apps/web/" in dockerfile


def test_identity_ui_preserves_assessment_pages_and_uses_explicit_sso():
    web = (ROOT / "apps/web/index.html").read_text()
    js = (ROOT / "apps/web/assets/app.js").read_text()
    assert 'id="oidc-login-button"' in web
    assert 'id="assessment-detail-view"' in web
    assert "/v1/workspace/config" in js
    assert 'window.location.assign("/v1/workspace/oidc/login")' in js



def _oidc_sql_function(signature: str) -> str:
    """Extract one still-unapplied SQL function for a source-only guard."""
    sql = (ROOT / "database/migrations/012_oidc_identities.sql").read_text()
    assert sql.count(signature) == 1
    return sql.split(signature, 1)[1].split("$$;", 1)[0]


def test_oidc_sql_clears_stale_tenant_context_before_auth():
    """A failed login must not inherit another identity in the same transaction.

    Source-contract only: actual PostgreSQL execution and RLS remain unverified.
    """
    cases = (
        ("CREATE FUNCTION app.create_oidc_workspace_session(",
         "IF p_issuer IS NULL"),
        ("CREATE OR REPLACE FUNCTION app.authenticate_workspace_session(",
         "IF p_session_sha256 IS NULL"),
    )
    for signature, validation in cases:
        body = _oidc_sql_function(signature)
        assert body.count("BEGIN") == 1
        early = body.split("BEGIN", 1)[1].split(validation, 1)[0]
        assert "set_config('app.organization_id', '', true)" in early
        assert "set_config('app.user_id', '', true)" in early
        assert body.count("PERFORM pg_catalog.set_config('app.organization_id', '', true)") == 2
        assert body.count("PERFORM pg_catalog.set_config('app.user_id', '', true)") == 2


def test_oidc_sql_revoked_membership_clears_both_tenant_settings():
    """After identity lookup, inactive membership must clear org and user GUCs."""
    for signature in (
        "CREATE FUNCTION app.create_oidc_workspace_session(",
        "CREATE OR REPLACE FUNCTION app.authenticate_workspace_session(",
    ):
        body = _oidc_sql_function(signature)
        membership = body.split("SELECT m.role::text INTO v_role", 1)[1]
        rejection = membership.split("IF NOT FOUND THEN", 1)[1].split("END IF;", 1)[0]
        assert "set_config('app.organization_id', '', true)" in rejection
        assert "set_config('app.user_id', '', true)" in rejection
        assert "RETURN;" in rejection


def test_oidc_disposable_postgres_script_enforces_context_denials():
    """Source check only: never connect to PostgreSQL during ordinary pytest."""
    script = (ROOT / "scripts/verify_oidc_identity.py").read_text()
    assert 'os.environ.get("GITHUB_ACTIONS") != "true"' in script
    assert "def require_context(cursor, expected_org=None, expected_user=None):" in script
    assert "current_setting('app.organization_id', true)" in script
    assert "current_setting('app.user_id', true)" in script
    assert 'status=\'SUSPENDED\'' in script
    assert 'status=\'ACTIVE\'' in script
    assert "SELECT app.revoke_workspace_session(%s)" in script
    assert "require_ci_database_urls(admin, runtime)" in script
    assert script.count("require_context(c)") >= 5
    assert script.count("require_context(c, org, user)") >= 3


def test_oidc_disposable_denials_are_rechecked_inside_same_transaction():
    """Keep the denied-CSRF and unknown-session cases beside a prior success."""
    script = (ROOT / "scripts/verify_oidc_identity.py").read_text()
    check = script.split("with psycopg.connect(runtime) as conn:", 2)[2]
    before = check.split("# Real PostgreSQL membership revocation", 1)[0]
    assert "require_context(c, org, user)" in before
    assert "bad-csrf" in before
    assert "unapproved-subject" in before
    assert '"0"*64' in before
    assert before.count("require_context(c)") >= 3



def test_oidc_disposable_two_tenants_never_share_session_or_csrf():
    """Offline source guard: actual PostgreSQL proof awaits isolated CI."""
    script = (ROOT / "scripts/verify_oidc_identity.py").read_text()
    assert 'os.environ.get("GITHUB_ACTIONS") != "true"' in script
    assert "CI OIDC Second Organization" in script
    assert "OIDC CI Second Member" in script
    assert "other_session_hash=" in script
    assert "other_csrf_hash=" in script
    assert 'Tenant B CSRF unlocked tenant A' in script
    assert 'Tenant A CSRF unlocked tenant B' in script
    assert 'Tenant A session binding drifted' in script
    assert 'Tenant B session binding drifted' in script
    assert 'Revoking tenant A identity unexpectedly revoked tenant B' in script


def test_oidc_tenant_switches_are_checked_against_database_context():
    """Successful A -> B -> A admission must rebind both session GUCs."""
    script = (ROOT / "scripts/verify_oidc_identity.py").read_text()
    section = script.split(
        "# Validate real session separation across two fictional organizations.", 1
    )[1].split("# Real PostgreSQL membership revocation/reinstatement", 1)[0]
    required = (
        "require_context(c, other_org, other_user)",
        "require_context(c, org, user)",
        "require_context(c)",
    )
    for check in required:
        assert check in section
    assert section.count("require_context(c, other_org, other_user)") >= 2
    assert section.count("require_context(c, org, user)") >= 2
    assert section.count("require_context(c)") >= 2



def test_oidc_sql_null_digests_deny_before_insert():
    """PostgreSQL NULL OR predicates must not fall through to session INSERT."""
    body = _oidc_sql_function("CREATE FUNCTION app.create_oidc_workspace_session(")
    early = body.split("BEGIN", 1)[1].split("SELECT i.organization_id", 1)[0]
    for digest in ("p_subject_sha256", "p_session_sha256", "p_csrf_sha256"):
        assert f"OR {digest} IS NULL" in early
        assert f"OR {digest} !~ '^[0-9a-f]{{64}}$'" in early
    assert early.index("p_subject_sha256 IS NULL") < early.index("END IF;")


def test_oidc_disposable_null_digests_clear_context_after_prior_success():
    """Source guard for three real PostgreSQL NULL-denial integration cases."""
    script = (ROOT / "scripts/verify_oidc_identity.py").read_text()
    assert 'os.environ.get("GITHUB_ACTIONS") != "true"' in script
    section = script.split(
        "# NULL digests must fail as ordinary denials", 1
    )[1].split("# Every denial starts after a successful tenant binding", 1)[0]
    for label in ("subject", "session", "csrf"):
        assert f'("{label}",' in section
    assert "NULL OIDC {label} digest was admitted" in section
    assert "require_context(c)" in section
    assert "require_context(c, org, user)" in section
    assert "Valid session failed after NULL OIDC {label} denial" in section


def test_oidc_disposable_same_subject_is_bound_to_exact_issuer():
    """Source-only guard: two synthetic issuers must not alias one subject."""
    script = (ROOT / "scripts/verify_oidc_identity.py").read_text()
    assert 'os.environ.get("GITHUB_ACTIONS") != "true"' in script
    assert 'SECOND_ISSUER = ISSUER + "/independent"' in script
    assert "(other_org,other_user,SECOND_ISSUER,DIGEST)" in script
    section = script.split(
        "# The same opaque subject can exist under a different trusted issuer.", 1
    )[1].split("# Real PostgreSQL membership revocation/reinstatement", 1)[0]
    assert "(SECOND_ISSUER,DIGEST,issuer_session_hash,issuer_csrf_hash)" in section
    assert "Same subject from second issuer resolved wrong tenant" in section
    assert "require_context(c, other_org, other_user)" in section
    assert "Issuer confusion admitted an unprovisioned subject" in section
    assert "require_context(c)" in section
    assert "Cross-issuer denial changed original tenant binding" in section
    assert "require_context(c, org, user)" in section


def test_oidc_disposable_cross_issuer_revocation_is_independent():
    """Revoking issuer A must not revoke an unrelated issuer B identity."""
    script = (ROOT / "scripts/verify_oidc_identity.py").read_text()
    section = script.split(
        "Revoked OIDC identity retained access", 1
    )[1].split("env=os.environ.copy()", 1)[0]
    assert "(issuer_session_hash,issuer_csrf_hash)" in section
    assert "Revoking issuer A identity invalidated issuer B identity" in section
    assert "require_context(c, other_org, other_user)" in section


def test_oidc_sql_revocation_is_scoped_to_authenticated_principal():
    """Source-only: revoked session digest alone cannot cross tenant boundaries."""
    body = _oidc_sql_function("CREATE OR REPLACE FUNCTION app.revoke_workspace_session(")
    assert "SECURITY DEFINER" in body
    assert "current_setting('app.organization_id', true)" in body
    assert "current_setting('app.user_id', true)" in body
    assert "p_session_sha256 IS NULL" in body
    assert "v_org IS NULL OR v_org = ''" in body
    assert "v_user IS NULL OR v_user = ''" in body
    assert "AND organization_id = v_org::uuid" in body
    assert "AND user_id = v_user::uuid" in body
    assert "AND revoked_at IS NULL" in body
    legacy = (ROOT / "database/migrations/010_workspace_sessions.sql").read_text()
    assert "REVOKE ALL ON FUNCTION app.revoke_workspace_session(text) FROM PUBLIC" in legacy
    assert "GRANT EXECUTE ON FUNCTION app.revoke_workspace_session(text)" in legacy


def test_oidc_disposable_revocation_requires_own_authenticated_context():
    """Source guard for actual ephemeral PostgreSQL negative mutation checks."""
    script = (ROOT / "scripts/verify_oidc_identity.py").read_text()
    assert 'os.environ.get("GITHUB_ACTIONS") != "true"' in script
    section = script.split(
        "# Revocation is a privileged mutation:", 1
    )[1].split("# The same opaque subject can exist", 1)[0]
    assert section.count("SELECT app.revoke_workspace_session(%s)") == 2
    assert section.count("(other_session_hash,)") == 2
    assert "Tenant A revoked tenant B's session" in section
    assert "Unauthenticated runtime revoked tenant B's session" in section
    assert "require_context(c, org, user)" in section
    assert section.count("require_context(c)") >= 2
    assert section.count("require_context(c, other_org, other_user)") == 2


def test_oidc_candidate_migration_has_valid_function_delimiters_and_single_commit():
    """Source-only guard against truncated SQL and premature COMMIT.

    This validates the candidate text, not execution on PostgreSQL.
    """
    sql = (ROOT / "database/migrations/012_oidc_identities.sql").read_text()
    assert sql.count("AS $$\n") == 3
    assert sql.count("\n$$;") == 3
    assert sql.count("$$") == 6
    assert sql.count("\nCOMMIT;") == 1
    assert sql.rstrip().endswith("COMMIT;")
    assert sql.count(
        "GRANT EXECUTE ON FUNCTION app.create_oidc_workspace_session("
    ) == 1
    assert sql.count(
        "REVOKE ALL ON FUNCTION app.create_oidc_workspace_session("
    ) == 1
    for chunk in sql.split("AS $$\n")[1:]:
        body, _remainder = chunk.split("\n$$;", 1)
        assert "BEGIN" in body and "END;" in body
        assert "COMMIT;" not in body
        assert "GRANT EXECUTE" not in body
        assert "REVOKE ALL" not in body
    revoker = _oidc_sql_function(
        "CREATE OR REPLACE FUNCTION app.revoke_workspace_session("
    )
    assert "p_session_sha256 !~ '^[0-9a-f]{64}$'" in revoker
    assert "AND organization_id = v_org::uuid" in revoker
    assert "AND user_id = v_user::uuid" in revoker


def _ci_guard():
    """Load only the standard-library safety interlock; no psycopg or DB."""
    return runpy.run_path(
        str(ROOT / "scripts/oidc_ci_database_guard.py")
    )["require_ci_database_urls"]


def _ci_fixture():
    env = {
        "GITHUB_ACTIONS": "true",
        "CI": "true",
        "GITHUB_REPOSITORY": "AhmadibOfficial/MetaAutomate",
        "RUNNER_ENVIRONMENT": "github-hosted",
        "GITHUB_EVENT_NAME": "pull_request",
        "GITHUB_RUN_ID": "123456789",
        "GITHUB_WORKFLOW": "MetaAutomate CI",
        "GITHUB_JOB": "test",
        "GITHUB_WORKFLOW_REF": "AhmadibOfficial/MetaAutomate/.github/workflows/ci.yml@refs/pull/131/merge",
    }
    admin = "postgresql://metaautomate:ci_only_password@localhost:5432/metaautomate"
    runtime = "postgresql://metaautomate_runtime:ci_runtime_password@localhost:5432/metaautomate"
    return env, admin, runtime


def test_oidc_ci_database_guard_rejects_untrusted_execution_context():
    """A forged CI flag alone must not permit disposable DB mutations."""
    guard = _ci_guard()
    env, admin, runtime = _ci_fixture()
    guard(admin, runtime, env)
    for key, value in (
        ("GITHUB_ACTIONS", "false"),
        ("CI", "false"),
        ("GITHUB_REPOSITORY", "someone-else/repository"),
        ("RUNNER_ENVIRONMENT", "self-hosted"),
        ("GITHUB_EVENT_NAME", "workflow_dispatch"),
        ("GITHUB_RUN_ID", "not-a-number"),
    ):
        unsafe = dict(env)
        unsafe[key] = value
        with pytest.raises(RuntimeError):
            guard(admin, runtime, unsafe)
    with pytest.raises(RuntimeError):
        guard(admin, runtime, {})



def test_oidc_ci_database_guard_rejects_libpq_shadow_settings():
    """A literal localhost URL must not be redirected by libpq PG* defaults."""
    guard = _ci_guard()
    env, admin, runtime = _ci_fixture()
    # Existing CI exports PGPASSWORD; explicit URLs carry fixture passwords.
    guard(admin, runtime, {**env, "PGPASSWORD": "ci_only_password"})
    for key, value in (
        ("PGHOSTADDR", "203.0.113.17"),
        ("PGHOSTADDR", "127.0.0.1"),
        ("PGSERVICE", "developer-db"),
        ("PGSERVICEFILE", "/tmp/unsafe-service.conf"),
        ("PGSYSCONFDIR", "/tmp/unsafe-libpq"),
        ("PGOPTIONS", "-c search_path=public"),
    ):
        with pytest.raises(RuntimeError, match="libpq environment overrides"):
            guard(admin, runtime, {**env, key: value})



def test_oidc_ci_database_guard_rejects_non_fixture_urls():
    """Never connect to remote, arbitrary, socket or query-overridden DSNs."""
    guard = _ci_guard()
    env, admin, runtime = _ci_fixture()
    for unsafe_admin in (
        admin.replace("localhost", "db.example.com"),
        admin.replace(":5432/", ":5433/"),
        admin.replace("/metaautomate", "/production"),
        admin.replace("metaautomate:", "postgres:"),
        admin + "?host=production.example.com",
        admin.replace("ci_only_password", "developer_password"),
        admin.replace("localhost", "127.0.0.1"),
        admin.replace("localhost", "local\nhost"),
        "host=/var/run/postgresql dbname=metaautomate user=metaautomate",
        "postgresql://metaautomate@localhost:5432/metaautomate",
    ):
        with pytest.raises(RuntimeError):
            guard(unsafe_admin, runtime, env)
    for unsafe_runtime in (
        runtime.replace("localhost", "db.example.com"),
        runtime.replace("metaautomate_runtime:", "metaautomate:"),
        runtime + "?hostaddr=203.0.113.10",
        runtime.replace("ci_runtime_password", "developer_password"),
        runtime.replace("localhost", "127.0.0.1"),
        runtime.replace("localhost", "local\thost"),
        runtime.replace("/metaautomate", "/developer"),
    ):
        with pytest.raises(RuntimeError):
            guard(admin, unsafe_runtime, env)


def test_oidc_ci_database_guard_is_bound_to_expected_workflow_and_job():
    """Reject accidental execution in unrelated GitHub Actions workflows/jobs.

    Source-only standard-library check; no psycopg or database connection.
    """
    guard = _ci_guard()
    env, admin, runtime = _ci_fixture()
    guard(admin, runtime, env)
    guard(admin, runtime, {
        **env,
        "GITHUB_WORKFLOW_REF": (
            "AhmadibOfficial/MetaAutomate/.github/workflows/ci.yml@refs/heads/main"
        ),
    })
    for key, value in (
        ("GITHUB_WORKFLOW", "Unrelated workflow"),
        ("GITHUB_JOB", "release-evidence-gate"),
        ("GITHUB_WORKFLOW_REF",
         "AhmadibOfficial/MetaAutomate/.github/workflows/other.yml@refs/pull/131/merge"),
        ("GITHUB_WORKFLOW_REF",
         "someone-else/MetaAutomate/.github/workflows/ci.yml@refs/pull/131/merge"),
        ("GITHUB_WORKFLOW_REF", ""),
        ("GITHUB_WORKFLOW_REF",
         "AhmadibOfficial/MetaAutomate/.github/workflows/ci.yml"),
    ):
        with pytest.raises(RuntimeError, match="CI (test job|workflow path)"):
            guard(admin, runtime, {**env, key: value})
    for key in ("GITHUB_WORKFLOW", "GITHUB_JOB", "GITHUB_WORKFLOW_REF"):
        missing = dict(env)
        missing.pop(key)
        with pytest.raises(RuntimeError):
            guard(admin, runtime, missing)

    # The interlock must remain before the first PostgreSQL connection.
    script = (ROOT / "scripts/verify_oidc_identity.py").read_text()
    assert script.index("require_ci_database_urls(admin, runtime)") < script.index(
        "with psycopg.connect(admin) as conn:"
    )
