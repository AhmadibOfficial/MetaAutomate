"""Private OIDC v2 source contracts; no network, DB or migration changes."""
from pathlib import Path

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
