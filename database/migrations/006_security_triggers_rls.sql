BEGIN;

CREATE SCHEMA IF NOT EXISTS app;

CREATE OR REPLACE FUNCTION app.current_org_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
    SELECT NULLIF(current_setting('app.organization_id', true), '')::uuid;
$$;

CREATE OR REPLACE FUNCTION app.current_user_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
    SELECT NULLIF(current_setting('app.user_id', true), '')::uuid;
$$;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    NEW.lock_version = OLD.lock_version + 1;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION set_updated_at_only()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION prevent_audit_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION 'audit_events is append-only';
END;
$$;

CREATE OR REPLACE FUNCTION enforce_tenant()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    current_tenant uuid;
BEGIN
    current_tenant := app.current_org_id();
    IF current_tenant IS NULL THEN
        RAISE EXCEPTION 'organization context is required';
    END IF;

    IF TG_OP IN ('INSERT','UPDATE') THEN
        IF NEW.organization_id IS NULL THEN
            NEW.organization_id := current_tenant;
        END IF;
        IF NEW.organization_id <> current_tenant THEN
            RAISE EXCEPTION 'cross-tenant write rejected';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

-- Prevent direct tenant changes on existing records.
CREATE OR REPLACE FUNCTION prevent_tenant_reassignment()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.organization_id <> NEW.organization_id THEN
        RAISE EXCEPTION 'organization_id is immutable';
    END IF;
    RETURN NEW;
END;
$$;

-- UPDATE trigger + optimistic locking.
CREATE TRIGGER trg_business_profiles_updated
BEFORE UPDATE ON business_profiles FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_integrations_updated
BEFORE UPDATE ON integrations FOR EACH ROW EXECUTE FUNCTION set_updated_at_only();
CREATE TRIGGER trg_leads_updated
BEFORE UPDATE ON leads FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_objectives_updated
BEFORE UPDATE ON objectives FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_workflows_updated
BEFORE UPDATE ON workflows FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_tasks_updated
BEFORE UPDATE ON tasks FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER trg_agents_updated
BEFORE UPDATE ON agents FOR EACH ROW EXECUTE FUNCTION set_updated_at_only();
CREATE TRIGGER trg_tools_updated
BEFORE UPDATE ON tools FOR EACH ROW EXECUTE FUNCTION set_updated_at_only();
CREATE TRIGGER trg_agent_permissions_updated
BEFORE UPDATE ON agent_permissions FOR EACH ROW EXECUTE FUNCTION set_updated_at_only();
CREATE TRIGGER trg_approvals_updated
BEFORE UPDATE ON approvals FOR EACH ROW EXECUTE FUNCTION set_updated_at_only();
CREATE TRIGGER trg_communications_updated
BEFORE UPDATE ON communications FOR EACH ROW EXECUTE FUNCTION set_updated_at_only();
CREATE TRIGGER trg_appointments_updated
BEFORE UPDATE ON appointments FOR EACH ROW EXECUTE FUNCTION set_updated_at_only();
CREATE TRIGGER trg_workflow_outcomes_updated
BEFORE UPDATE ON workflow_outcomes FOR EACH ROW EXECUTE FUNCTION set_updated_at_only();

-- organization_id must never be changed after insert.
CREATE TRIGGER trg_business_profiles_tenant_immutable
BEFORE UPDATE ON business_profiles FOR EACH ROW EXECUTE FUNCTION prevent_tenant_reassignment();
CREATE TRIGGER trg_integrations_tenant_immutable
BEFORE UPDATE ON integrations FOR EACH ROW EXECUTE FUNCTION prevent_tenant_reassignment();
CREATE TRIGGER trg_leads_tenant_immutable
BEFORE UPDATE ON leads FOR EACH ROW EXECUTE FUNCTION prevent_tenant_reassignment();
CREATE TRIGGER trg_objectives_tenant_immutable
BEFORE UPDATE ON objectives FOR EACH ROW EXECUTE FUNCTION prevent_tenant_reassignment();
CREATE TRIGGER trg_workflows_tenant_immutable
BEFORE UPDATE ON workflows FOR EACH ROW EXECUTE FUNCTION prevent_tenant_reassignment();
CREATE TRIGGER trg_tasks_tenant_immutable
BEFORE UPDATE ON tasks FOR EACH ROW EXECUTE FUNCTION prevent_tenant_reassignment();
CREATE TRIGGER trg_agents_tenant_immutable
BEFORE UPDATE ON agents FOR EACH ROW EXECUTE FUNCTION prevent_tenant_reassignment();
CREATE TRIGGER trg_tools_tenant_immutable
BEFORE UPDATE ON tools FOR EACH ROW EXECUTE FUNCTION prevent_tenant_reassignment();
CREATE TRIGGER trg_agent_permissions_tenant_immutable
BEFORE UPDATE ON agent_permissions FOR EACH ROW EXECUTE FUNCTION prevent_tenant_reassignment();
CREATE TRIGGER trg_agent_runs_tenant_immutable
BEFORE UPDATE ON agent_runs FOR EACH ROW EXECUTE FUNCTION prevent_tenant_reassignment();
CREATE TRIGGER trg_tool_calls_tenant_immutable
BEFORE UPDATE ON tool_calls FOR EACH ROW EXECUTE FUNCTION prevent_tenant_reassignment();
CREATE TRIGGER trg_approvals_tenant_immutable
BEFORE UPDATE ON approvals FOR EACH ROW EXECUTE FUNCTION prevent_tenant_reassignment();
CREATE TRIGGER trg_verifications_tenant_immutable
BEFORE UPDATE ON verifications FOR EACH ROW EXECUTE FUNCTION prevent_tenant_reassignment();
CREATE TRIGGER trg_verification_evidence_tenant_immutable
BEFORE UPDATE ON verification_evidence FOR EACH ROW EXECUTE FUNCTION prevent_tenant_reassignment();
CREATE TRIGGER trg_recovery_attempts_tenant_immutable
BEFORE UPDATE ON recovery_attempts FOR EACH ROW EXECUTE FUNCTION prevent_tenant_reassignment();
CREATE TRIGGER trg_communications_tenant_immutable
BEFORE UPDATE ON communications FOR EACH ROW EXECUTE FUNCTION prevent_tenant_reassignment();
CREATE TRIGGER trg_appointments_tenant_immutable
BEFORE UPDATE ON appointments FOR EACH ROW EXECUTE FUNCTION prevent_tenant_reassignment();
CREATE TRIGGER trg_workflow_outcomes_tenant_immutable
BEFORE UPDATE ON workflow_outcomes FOR EACH ROW EXECUTE FUNCTION prevent_tenant_reassignment();
CREATE TRIGGER trg_idempotency_keys_tenant_immutable
BEFORE UPDATE ON idempotency_keys FOR EACH ROW EXECUTE FUNCTION prevent_tenant_reassignment();
CREATE TRIGGER trg_audit_events_tenant_immutable
BEFORE UPDATE ON audit_events FOR EACH ROW EXECUTE FUNCTION prevent_tenant_reassignment();

-- Tenant guard on all tenant-owned writes.
CREATE TRIGGER trg_memberships_tenant_guard
BEFORE INSERT OR UPDATE ON organization_memberships FOR EACH ROW EXECUTE FUNCTION enforce_tenant();
CREATE TRIGGER trg_business_profiles_tenant_guard
BEFORE INSERT OR UPDATE ON business_profiles FOR EACH ROW EXECUTE FUNCTION enforce_tenant();
CREATE TRIGGER trg_integrations_tenant_guard
BEFORE INSERT OR UPDATE ON integrations FOR EACH ROW EXECUTE FUNCTION enforce_tenant();
CREATE TRIGGER trg_leads_tenant_guard
BEFORE INSERT OR UPDATE ON leads FOR EACH ROW EXECUTE FUNCTION enforce_tenant();
CREATE TRIGGER trg_objectives_tenant_guard
BEFORE INSERT OR UPDATE ON objectives FOR EACH ROW EXECUTE FUNCTION enforce_tenant();
CREATE TRIGGER trg_workflows_tenant_guard
BEFORE INSERT OR UPDATE ON workflows FOR EACH ROW EXECUTE FUNCTION enforce_tenant();
CREATE TRIGGER trg_tasks_tenant_guard
BEFORE INSERT OR UPDATE ON tasks FOR EACH ROW EXECUTE FUNCTION enforce_tenant();
CREATE TRIGGER trg_task_dependencies_tenant_guard
BEFORE INSERT OR UPDATE ON task_dependencies FOR EACH ROW EXECUTE FUNCTION enforce_tenant();
CREATE TRIGGER trg_agents_tenant_guard
BEFORE INSERT OR UPDATE ON agents FOR EACH ROW EXECUTE FUNCTION enforce_tenant();
CREATE TRIGGER trg_tools_tenant_guard
BEFORE INSERT OR UPDATE ON tools FOR EACH ROW EXECUTE FUNCTION enforce_tenant();
CREATE TRIGGER trg_agent_permissions_tenant_guard
BEFORE INSERT OR UPDATE ON agent_permissions FOR EACH ROW EXECUTE FUNCTION enforce_tenant();
CREATE TRIGGER trg_agent_runs_tenant_guard
BEFORE INSERT OR UPDATE ON agent_runs FOR EACH ROW EXECUTE FUNCTION enforce_tenant();
CREATE TRIGGER trg_tool_calls_tenant_guard
BEFORE INSERT OR UPDATE ON tool_calls FOR EACH ROW EXECUTE FUNCTION enforce_tenant();
CREATE TRIGGER trg_approvals_tenant_guard
BEFORE INSERT OR UPDATE ON approvals FOR EACH ROW EXECUTE FUNCTION enforce_tenant();
CREATE TRIGGER trg_verifications_tenant_guard
BEFORE INSERT OR UPDATE ON verifications FOR EACH ROW EXECUTE FUNCTION enforce_tenant();
CREATE TRIGGER trg_verification_evidence_tenant_guard
BEFORE INSERT OR UPDATE ON verification_evidence FOR EACH ROW EXECUTE FUNCTION enforce_tenant();
CREATE TRIGGER trg_recovery_attempts_tenant_guard
BEFORE INSERT OR UPDATE ON recovery_attempts FOR EACH ROW EXECUTE FUNCTION enforce_tenant();
CREATE TRIGGER trg_communications_tenant_guard
BEFORE INSERT OR UPDATE ON communications FOR EACH ROW EXECUTE FUNCTION enforce_tenant();
CREATE TRIGGER trg_appointments_tenant_guard
BEFORE INSERT OR UPDATE ON appointments FOR EACH ROW EXECUTE FUNCTION enforce_tenant();
CREATE TRIGGER trg_workflow_outcomes_tenant_guard
BEFORE INSERT OR UPDATE ON workflow_outcomes FOR EACH ROW EXECUTE FUNCTION enforce_tenant();
CREATE TRIGGER trg_idempotency_keys_tenant_guard
BEFORE INSERT OR UPDATE ON idempotency_keys FOR EACH ROW EXECUTE FUNCTION enforce_tenant();
CREATE TRIGGER trg_audit_events_tenant_guard
BEFORE INSERT OR UPDATE ON audit_events FOR EACH ROW EXECUTE FUNCTION enforce_tenant();

CREATE TRIGGER trg_audit_events_no_update
BEFORE UPDATE ON audit_events FOR EACH ROW EXECUTE FUNCTION prevent_audit_mutation();
CREATE TRIGGER trg_audit_events_no_delete
BEFORE DELETE ON audit_events FOR EACH ROW EXECUTE FUNCTION prevent_audit_mutation();

-- Row-level security. Application sessions must set app.organization_id.
ALTER TABLE organization_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_memberships FORCE ROW LEVEL SECURITY;
ALTER TABLE business_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE business_profiles FORCE ROW LEVEL SECURITY;
ALTER TABLE integrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE integrations FORCE ROW LEVEL SECURITY;
ALTER TABLE leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE leads FORCE ROW LEVEL SECURITY;
ALTER TABLE objectives ENABLE ROW LEVEL SECURITY;
ALTER TABLE objectives FORCE ROW LEVEL SECURITY;
ALTER TABLE workflows ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflows FORCE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks FORCE ROW LEVEL SECURITY;
ALTER TABLE task_dependencies ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_dependencies FORCE ROW LEVEL SECURITY;
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE agents FORCE ROW LEVEL SECURITY;
ALTER TABLE tools ENABLE ROW LEVEL SECURITY;
ALTER TABLE tools FORCE ROW LEVEL SECURITY;
ALTER TABLE agent_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_permissions FORCE ROW LEVEL SECURITY;
ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_runs FORCE ROW LEVEL SECURITY;
ALTER TABLE tool_calls ENABLE ROW LEVEL SECURITY;
ALTER TABLE tool_calls FORCE ROW LEVEL SECURITY;
ALTER TABLE approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE approvals FORCE ROW LEVEL SECURITY;
ALTER TABLE verifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE verifications FORCE ROW LEVEL SECURITY;
ALTER TABLE verification_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE verification_evidence FORCE ROW LEVEL SECURITY;
ALTER TABLE recovery_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE recovery_attempts FORCE ROW LEVEL SECURITY;
ALTER TABLE communications ENABLE ROW LEVEL SECURITY;
ALTER TABLE communications FORCE ROW LEVEL SECURITY;
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;
ALTER TABLE appointments FORCE ROW LEVEL SECURITY;
ALTER TABLE workflow_outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_outcomes FORCE ROW LEVEL SECURITY;
ALTER TABLE idempotency_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE idempotency_keys FORCE ROW LEVEL SECURITY;
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events FORCE ROW LEVEL SECURITY;

-- Reusable tenant policy pattern.
CREATE POLICY tenant_org_memberships ON organization_memberships
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());
CREATE POLICY tenant_business_profiles ON business_profiles
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());
CREATE POLICY tenant_integrations ON integrations
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());
CREATE POLICY tenant_leads ON leads
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());
CREATE POLICY tenant_objectives ON objectives
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());
CREATE POLICY tenant_workflows ON workflows
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());
CREATE POLICY tenant_tasks ON tasks
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());
CREATE POLICY tenant_task_dependencies ON task_dependencies
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());
CREATE POLICY tenant_agents ON agents
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());
CREATE POLICY tenant_tools ON tools
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());
CREATE POLICY tenant_agent_permissions ON agent_permissions
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());
CREATE POLICY tenant_agent_runs ON agent_runs
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());
CREATE POLICY tenant_tool_calls ON tool_calls
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());
CREATE POLICY tenant_approvals ON approvals
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());
CREATE POLICY tenant_verifications ON verifications
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());
CREATE POLICY tenant_verification_evidence ON verification_evidence
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());
CREATE POLICY tenant_recovery_attempts ON recovery_attempts
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());
CREATE POLICY tenant_communications ON communications
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());
CREATE POLICY tenant_appointments ON appointments
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());
CREATE POLICY tenant_workflow_outcomes ON workflow_outcomes
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());
CREATE POLICY tenant_idempotency_keys ON idempotency_keys
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());
CREATE POLICY tenant_audit_events ON audit_events
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());

COMMIT;
