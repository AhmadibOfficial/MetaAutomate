BEGIN;

CREATE TABLE communications (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    lead_id uuid NOT NULL,
    workflow_id uuid,
    task_id uuid,
    integration_id uuid,
    direction communication_direction NOT NULL,
    channel communication_channel NOT NULL,
    sender text,
    recipient text,
    subject text,
    body text,
    status communication_status NOT NULL DEFAULT 'QUEUED',
    idempotency_key text NOT NULL,
    content_hash text,
    external_message_id text,
    provider_metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    sent_at timestamptz,
    delivered_at timestamptz,
    read_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (organization_id, id),
    FOREIGN KEY (organization_id, lead_id)
        REFERENCES leads(organization_id, id)
        ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, workflow_id)
        REFERENCES workflows(organization_id, id)
        ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, task_id)
        REFERENCES tasks(organization_id, id)
        ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, integration_id)
        REFERENCES integrations(organization_id, id)
        ON DELETE RESTRICT
);
CREATE UNIQUE INDEX uq_communication_idempotency
    ON communications(organization_id, integration_id, idempotency_key);
CREATE UNIQUE INDEX uq_external_message
    ON communications(integration_id, external_message_id)
    WHERE external_message_id IS NOT NULL;
CREATE INDEX idx_communications_lead
    ON communications(organization_id, lead_id, created_at);

CREATE TABLE appointments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    lead_id uuid NOT NULL,
    workflow_id uuid,
    task_id uuid,
    integration_id uuid,
    external_event_id text,
    status appointment_status NOT NULL DEFAULT 'TENTATIVE',
    title text NOT NULL,
    start_at timestamptz NOT NULL,
    end_at timestamptz NOT NULL,
    time_zone text NOT NULL,
    attendee_email citext,
    attendee_phone text,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (organization_id, id),
    FOREIGN KEY (organization_id, lead_id)
        REFERENCES leads(organization_id, id)
        ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, workflow_id)
        REFERENCES workflows(organization_id, id)
        ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, task_id)
        REFERENCES tasks(organization_id, id)
        ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, integration_id)
        REFERENCES integrations(organization_id, id)
        ON DELETE RESTRICT,
    CHECK (end_at > start_at)
);
CREATE UNIQUE INDEX uq_appointment_external_event
    ON appointments(integration_id, external_event_id)
    WHERE external_event_id IS NOT NULL;
CREATE INDEX idx_appointments_lead ON appointments(organization_id, lead_id, start_at);
CREATE INDEX idx_appointments_status ON appointments(organization_id, status, start_at);

CREATE TABLE workflow_outcomes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    workflow_id uuid NOT NULL,
    outcome_type text NOT NULL,
    status text NOT NULL DEFAULT 'DRAFT',
    baseline_value numeric,
    target_value numeric,
    realized_value numeric,
    currency char(3),
    metrics jsonb NOT NULL DEFAULT '{}'::jsonb,
    measured_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (organization_id, id),
    FOREIGN KEY (organization_id, workflow_id)
        REFERENCES workflows(organization_id, id)
        ON DELETE RESTRICT,
    CHECK (currency IS NULL OR currency ~ '^[A-Z]{3}$')
);
CREATE INDEX idx_workflow_outcomes_workflow
    ON workflow_outcomes(organization_id, workflow_id);

CREATE TABLE idempotency_keys (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    scope text NOT NULL,
    idempotency_key text NOT NULL,
    request_hash text NOT NULL,
    status idempotency_status NOT NULL DEFAULT 'IN_PROGRESS',
    response_code integer,
    response_body jsonb,
    resource_type text,
    resource_id uuid,
    locked_at timestamptz,
    completed_at timestamptz,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (organization_id, scope, idempotency_key),
    CHECK (expires_at > created_at),
    CHECK (completed_at IS NULL OR completed_at >= created_at)
);
CREATE INDEX idx_idempotency_expiry ON idempotency_keys(expires_at);
CREATE INDEX idx_idempotency_resource
    ON idempotency_keys(organization_id, resource_type, resource_id);

CREATE TABLE audit_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    event_seq bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
    occurred_at timestamptz NOT NULL DEFAULT now(),
    actor_type audit_actor_type NOT NULL,
    actor_user_id uuid,
    actor_agent_id uuid,
    action text NOT NULL,
    entity_type text NOT NULL,
    entity_id uuid,
    request_id uuid,
    correlation_id uuid,
    idempotency_key text,
    before_data jsonb,
    after_data jsonb,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    ip_address inet,
    user_agent text,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (organization_id, id),
    FOREIGN KEY (organization_id, actor_user_id)
        REFERENCES organization_memberships(organization_id, user_id)
        ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, actor_agent_id)
        REFERENCES agents(organization_id, id)
        ON DELETE RESTRICT,
    CHECK (
        (actor_type = 'USER' AND actor_user_id IS NOT NULL AND actor_agent_id IS NULL)
        OR (actor_type = 'AGENT' AND actor_agent_id IS NOT NULL AND actor_user_id IS NULL)
        OR (actor_type IN ('SYSTEM','EXTERNAL') AND actor_user_id IS NULL AND actor_agent_id IS NULL)
    )
);
CREATE INDEX idx_audit_org_time
    ON audit_events(organization_id, occurred_at DESC);
CREATE INDEX idx_audit_entity
    ON audit_events(organization_id, entity_type, entity_id, occurred_at DESC);
CREATE INDEX idx_audit_correlation
    ON audit_events(organization_id, correlation_id);
CREATE INDEX idx_audit_idempotency
    ON audit_events(organization_id, idempotency_key);

COMMIT;
