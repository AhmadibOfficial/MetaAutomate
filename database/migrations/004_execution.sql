BEGIN;

CREATE TABLE agents (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    name text NOT NULL,
    agent_type text NOT NULL,
    model_provider text,
    model_name text,
    status agent_status NOT NULL DEFAULT 'ACTIVE',
    instructions_ref text,
    configuration jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    created_by_user_id uuid,
    updated_by_user_id uuid,
    UNIQUE (organization_id, id),
    FOREIGN KEY (organization_id, created_by_user_id)
        REFERENCES organization_memberships(organization_id, user_id)
        ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, updated_by_user_id)
        REFERENCES organization_memberships(organization_id, user_id)
        ON DELETE RESTRICT
);
CREATE INDEX idx_agents_org_status ON agents(organization_id, status);

ALTER TABLE tasks
    ADD CONSTRAINT fk_tasks_assigned_agent
    FOREIGN KEY (organization_id, assigned_agent_id)
    REFERENCES agents(organization_id, id)
    ON DELETE RESTRICT;

CREATE TABLE tools (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    tool_key text NOT NULL,
    name text NOT NULL,
    version text NOT NULL DEFAULT '1.0.0',
    status tool_status NOT NULL DEFAULT 'ACTIVE',
    side_effecting boolean NOT NULL DEFAULT false,
    supports_idempotency boolean NOT NULL DEFAULT true,
    input_schema jsonb,
    output_schema jsonb,
    configuration jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (organization_id, id),
    UNIQUE (organization_id, tool_key, version)
);
CREATE INDEX idx_tools_org_status ON tools(organization_id, status);

CREATE TABLE agent_permissions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    agent_id uuid NOT NULL,
    tool_id uuid NOT NULL,
    action text NOT NULL,
    allowed boolean NOT NULL DEFAULT false,
    requires_approval boolean NOT NULL DEFAULT true,
    constraints_json jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (organization_id, agent_id, tool_id, action),
    UNIQUE (organization_id, id),
    FOREIGN KEY (organization_id, agent_id)
        REFERENCES agents(organization_id, id)
        ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, tool_id)
        REFERENCES tools(organization_id, id)
        ON DELETE RESTRICT
);

CREATE TABLE agent_runs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    workflow_id uuid,
    task_id uuid NOT NULL,
    agent_id uuid NOT NULL,
    status agent_run_status NOT NULL DEFAULT 'QUEUED',
    run_number integer NOT NULL DEFAULT 1,
    idempotency_key text,
    input_hash text,
    input_snapshot jsonb,
    output_summary jsonb,
    error jsonb,
    started_at timestamptz,
    finished_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (organization_id, id),
    FOREIGN KEY (organization_id, workflow_id)
        REFERENCES workflows(organization_id, id)
        ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, task_id)
        REFERENCES tasks(organization_id, id)
        ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, agent_id)
        REFERENCES agents(organization_id, id)
        ON DELETE RESTRICT,
    CHECK (run_number > 0)
);
CREATE UNIQUE INDEX uq_agent_run_idempotency
    ON agent_runs(organization_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;
CREATE INDEX idx_agent_runs_task ON agent_runs(organization_id, task_id);
CREATE INDEX idx_agent_runs_status ON agent_runs(organization_id, status);

CREATE TABLE tool_calls (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    agent_run_id uuid NOT NULL,
    tool_id uuid NOT NULL,
    integration_id uuid,
    action text NOT NULL,
    status tool_call_status NOT NULL DEFAULT 'QUEUED',
    idempotency_key text NOT NULL,
    request_hash text NOT NULL,
    input_redacted jsonb,
    output_redacted jsonb,
    external_request_id text,
    external_resource_id text,
    error_code text,
    error_detail jsonb,
    started_at timestamptz,
    completed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (organization_id, id),
    FOREIGN KEY (organization_id, agent_run_id)
        REFERENCES agent_runs(organization_id, id)
        ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, tool_id)
        REFERENCES tools(organization_id, id)
        ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, integration_id)
        REFERENCES integrations(organization_id, id)
        ON DELETE RESTRICT
);
CREATE UNIQUE INDEX uq_tool_call_idempotency
    ON tool_calls(organization_id, tool_id, idempotency_key);
CREATE UNIQUE INDEX uq_tool_external_request
    ON tool_calls(integration_id, external_request_id)
    WHERE external_request_id IS NOT NULL;
CREATE INDEX idx_tool_calls_run ON tool_calls(organization_id, agent_run_id);
CREATE INDEX idx_tool_calls_status ON tool_calls(organization_id, status);

CREATE TABLE approvals (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    workflow_id uuid,
    task_id uuid,
    agent_run_id uuid,
    action_type text NOT NULL,
    requested_action jsonb NOT NULL,
    status approval_status NOT NULL DEFAULT 'PENDING',
    requested_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz,
    decided_by_user_id uuid,
    decided_at timestamptz,
    decision_reason text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (organization_id, id),
    FOREIGN KEY (organization_id, workflow_id)
        REFERENCES workflows(organization_id, id)
        ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, task_id)
        REFERENCES tasks(organization_id, id)
        ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, agent_run_id)
        REFERENCES agent_runs(organization_id, id)
        ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, decided_by_user_id)
        REFERENCES organization_memberships(organization_id, user_id)
        ON DELETE RESTRICT,
    CHECK (expires_at IS NULL OR expires_at > requested_at),
    CHECK ((status = 'PENDING' AND decided_at IS NULL AND decided_by_user_id IS NULL)
        OR (status <> 'PENDING'))
);
CREATE INDEX idx_approvals_pending
    ON approvals(organization_id, status)
    WHERE status = 'PENDING';

CREATE TABLE verifications (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    workflow_id uuid,
    task_id uuid,
    tool_call_id uuid,
    verification_type text NOT NULL,
    status verification_status NOT NULL DEFAULT 'PENDING',
    expected_state jsonb NOT NULL DEFAULT '{}'::jsonb,
    observed_state jsonb NOT NULL DEFAULT '{}'::jsonb,
    evidence_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
    verified_at timestamptz,
    verified_by_user_id uuid,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (organization_id, id),
    FOREIGN KEY (organization_id, workflow_id)
        REFERENCES workflows(organization_id, id)
        ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, task_id)
        REFERENCES tasks(organization_id, id)
        ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, tool_call_id)
        REFERENCES tool_calls(organization_id, id)
        ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, verified_by_user_id)
        REFERENCES organization_memberships(organization_id, user_id)
        ON DELETE RESTRICT
);

CREATE TABLE verification_evidence (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    verification_id uuid NOT NULL,
    evidence_type text NOT NULL,
    source_type text NOT NULL,
    description text,
    reference text,
    content_hash text,
    captured_at timestamptz NOT NULL DEFAULT now(),
    verification_status verification_status NOT NULL DEFAULT 'PENDING',
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (organization_id, id),
    FOREIGN KEY (organization_id, verification_id)
        REFERENCES verifications(organization_id, id)
        ON DELETE RESTRICT
);
CREATE INDEX idx_verification_evidence ON verification_evidence(organization_id, verification_id);

CREATE TABLE recovery_attempts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    workflow_id uuid,
    task_id uuid,
    attempt_number integer NOT NULL,
    failure_reason jsonb NOT NULL,
    recovery_strategy text NOT NULL,
    status recovery_status NOT NULL DEFAULT 'STARTED',
    result jsonb,
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (organization_id, workflow_id, task_id, attempt_number),
    UNIQUE (organization_id, id),
    FOREIGN KEY (organization_id, workflow_id)
        REFERENCES workflows(organization_id, id)
        ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, task_id)
        REFERENCES tasks(organization_id, id)
        ON DELETE RESTRICT,
    CHECK (attempt_number > 0),
    CHECK (finished_at IS NULL OR finished_at >= started_at)
);

COMMIT;
