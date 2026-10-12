from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "database" / "migrations"


def load_all_sql() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(MIGRATIONS.glob("*.sql")))


def test_required_migration_order_exists():
    names = [p.name for p in sorted(MIGRATIONS.glob("*.sql"))]
    assert names == [
        "001_extensions_and_enums.sql",
        "002_identity_business.sql",
        "003_leads_workflows.sql",
        "004_execution.sql",
        "005_business_outcomes_audit.sql",
        "006_security_triggers_rls.sql",
        "007_utility_functions.sql",
        "008_capability_registry.sql",
        "009_objective_operations.sql",
        "010_workspace_sessions.sql",
        "011_oidc_identities.sql",
    ]


def test_core_tenant_tables_have_organization_id():
    sql = load_all_sql()
    tables = [
        "organization_memberships",
        "business_profiles",
        "integrations",
        "leads",
        "objectives",
        "workflows",
        "tasks",
        "agents",
        "tools",
        "agent_permissions",
        "agent_runs",
        "tool_calls",
        "approvals",
        "verifications",
        "verification_evidence",
        "recovery_attempts",
        "communications",
        "appointments",
        "workflow_outcomes",
        "idempotency_keys",
        "audit_events",
    ]
    for table in tables:
        marker = f"CREATE TABLE {table} ("
        start = sql.index(marker)
        end = sql.index(");", start)
        body = sql[start:end]
        assert "organization_id uuid" in body, table


def test_composite_cross_tenant_foreign_keys_are_present():
    sql = load_all_sql()
    required_fragments = [
        "FOREIGN KEY (organization_id, workflow_id)\n        REFERENCES workflows(organization_id, id)",
        "FOREIGN KEY (organization_id, task_id)\n        REFERENCES tasks(organization_id, id)",
        "FOREIGN KEY (organization_id, agent_id)\n        REFERENCES agents(organization_id, id)",
        "FOREIGN KEY (organization_id, tool_id)\n        REFERENCES tools(organization_id, id)",
        "FOREIGN KEY (organization_id, lead_id)\n        REFERENCES leads(organization_id, id)",
    ]
    for fragment in required_fragments:
        assert fragment in sql


def test_idempotency_contract_is_present():
    sql = load_all_sql()
    assert "idempotency_key text NOT NULL" in sql
    assert "request_hash text NOT NULL" in sql
    assert "ON tool_calls(organization_id, tool_id, idempotency_key);" in sql
    assert "UNIQUE (organization_id, scope, idempotency_key)" in sql


def test_audit_is_append_only():
    sql = load_all_sql()
    assert "CREATE TRIGGER trg_audit_events_no_update" in sql
    assert "CREATE TRIGGER trg_audit_events_no_delete" in sql
    assert "RAISE EXCEPTION 'audit_events is append-only'" in sql


def test_rls_is_forced_on_core_tenant_tables():
    sql = load_all_sql()
    for table in (
        "leads",
        "workflows",
        "tasks",
        "tool_calls",
        "appointments",
        "audit_events",
    ):
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;" in sql
        assert f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;" in sql
        assert f"CREATE POLICY tenant_{table}" in sql


def test_registry_has_all_six_tables():
    sql = (MIGRATIONS / "008_capability_registry.sql").read_text(encoding="utf-8")
    for table in (
        "capability_definitions",
        "capability_versions",
        "capability_dependencies",
        "capability_permissions",
        "organization_capabilities",
        "capability_executions",
    ):
        assert f"CREATE TABLE {table} (" in sql


def test_registry_tenant_rls_is_forced():
    sql = (MIGRATIONS / "008_capability_registry.sql").read_text(encoding="utf-8")
    for table in ("organization_capabilities", "capability_executions"):
        assert f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;" in sql
        assert f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;" in sql
        assert f"CREATE POLICY tenant_{table}" in sql


def test_objective_operations_has_restricted_auth_contract():
    sql = (MIGRATIONS / "009_objective_operations.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE api_access_tokens" in sql
    assert "ALTER TABLE api_access_tokens FORCE ROW LEVEL SECURITY;" in sql
    assert "SECURITY DEFINER" in sql
    assert "GRANT EXECUTE ON FUNCTION app.authenticate_api_token(text) TO metaautomate_runtime;" in sql
    assert "REVOKE ALL ON FUNCTION app.authenticate_api_token(text) FROM PUBLIC;" in sql


def test_workspace_browser_sessions_are_revocable_and_tenant_scoped():
    sql = (MIGRATIONS / "010_workspace_sessions.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE workspace_sessions" in sql
    assert "ALTER TABLE workspace_sessions FORCE ROW LEVEL SECURITY;" in sql
    assert "CREATE FUNCTION app.authenticate_workspace_session(" in sql
    assert "CREATE FUNCTION app.revoke_workspace_session(" in sql
    assert "REVOKE ALL ON workspace_sessions FROM metaautomate_runtime;" in sql


def test_production_oidc_identity_contract():
    sql=(MIGRATIONS/"011_oidc_identities.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE oidc_identities" in sql
    assert "ALTER TABLE oidc_identities FORCE ROW LEVEL SECURITY;" in sql
    assert "REVOKE ALL ON oidc_identities FROM metaautomate_runtime;" in sql
    assert "CREATE FUNCTION app.create_oidc_workspace_session(" in sql
    assert "CREATE OR REPLACE FUNCTION app.authenticate_workspace_session(" in sql
