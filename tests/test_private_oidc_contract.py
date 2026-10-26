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
