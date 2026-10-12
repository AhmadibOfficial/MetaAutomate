BEGIN;

CREATE TABLE leads (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    public_ref text,
    full_name text,
    email citext,
    phone text,
    source_type text,
    source_external_id text,
    canonical_contact_key text,
    status lead_status NOT NULL DEFAULT 'NEW',
    qualification_status qualification_status NOT NULL DEFAULT 'PENDING',
    qualification_score numeric(5,2),
    qualification_reason text,
    duplicate_of_lead_id uuid,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    created_by_user_id uuid,
    updated_by_user_id uuid,
    lock_version integer NOT NULL DEFAULT 1,
    UNIQUE (organization_id, id),
    FOREIGN KEY (organization_id, duplicate_of_lead_id)
        REFERENCES leads(organization_id, id)
        ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, created_by_user_id)
        REFERENCES organization_memberships(organization_id, user_id)
        ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, updated_by_user_id)
        REFERENCES organization_memberships(organization_id, user_id)
        ON DELETE RESTRICT,
    CHECK (qualification_score IS NULL OR (qualification_score >= 0 AND qualification_score <= 100))
);
CREATE INDEX idx_leads_org_status ON leads(organization_id, status);
CREATE INDEX idx_leads_org_qualification ON leads(organization_id, qualification_status);
CREATE INDEX idx_leads_org_contact ON leads(organization_id, canonical_contact_key);
CREATE UNIQUE INDEX uq_lead_source_external
    ON leads(organization_id, source_type, source_external_id)
    WHERE source_external_id IS NOT NULL;

CREATE TABLE objectives (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    public_ref text,
    title text NOT NULL,
    description text,
    status objective_status NOT NULL DEFAULT 'DRAFT',
    execution_mode execution_mode NOT NULL DEFAULT 'ASSIST',
    initiated_by_user_id uuid,
    input_context jsonb NOT NULL DEFAULT '{}'::jsonb,
    desired_outcome jsonb NOT NULL DEFAULT '{}'::jsonb,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    lock_version integer NOT NULL DEFAULT 1,
    UNIQUE (organization_id, id),
    FOREIGN KEY (organization_id, initiated_by_user_id)
        REFERENCES organization_memberships(organization_id, user_id)
        ON DELETE RESTRICT
);
CREATE INDEX idx_objectives_org_status ON objectives(organization_id, status);

CREATE TABLE workflows (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    objective_id uuid NOT NULL,
    public_ref text,
    workflow_type text NOT NULL,
    definition_version integer NOT NULL DEFAULT 1,
    state workflow_state NOT NULL DEFAULT 'DRAFT',
    execution_mode execution_mode NOT NULL,
    started_at timestamptz,
    completed_at timestamptz,
    context jsonb NOT NULL DEFAULT '{}'::jsonb,
    result jsonb NOT NULL DEFAULT '{}'::jsonb,
    error jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    lock_version integer NOT NULL DEFAULT 1,
    UNIQUE (organization_id, id),
    FOREIGN KEY (organization_id, objective_id)
        REFERENCES objectives(organization_id, id)
        ON DELETE RESTRICT,
    CHECK (definition_version > 0),
    CHECK ((completed_at IS NULL) OR (completed_at >= COALESCE(started_at, created_at)))
);
CREATE INDEX idx_workflows_org_state ON workflows(organization_id, state);
CREATE INDEX idx_workflows_org_objective ON workflows(organization_id, objective_id);

CREATE TABLE tasks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    workflow_id uuid NOT NULL,
    parent_task_id uuid,
    capability_key text,
    task_type text NOT NULL,
    name text NOT NULL,
    sequence_no integer,
    state task_state NOT NULL DEFAULT 'PENDING',
    assigned_agent_id uuid,
    input jsonb NOT NULL DEFAULT '{}'::jsonb,
    output jsonb NOT NULL DEFAULT '{}'::jsonb,
    error jsonb,
    started_at timestamptz,
    completed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    lock_version integer NOT NULL DEFAULT 1,
    UNIQUE (organization_id, id),
    FOREIGN KEY (organization_id, workflow_id)
        REFERENCES workflows(organization_id, id)
        ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, parent_task_id)
        REFERENCES tasks(organization_id, id)
        ON DELETE RESTRICT,
    CHECK (sequence_no IS NULL OR sequence_no >= 0)
);
CREATE INDEX idx_tasks_workflow_state ON tasks(organization_id, workflow_id, state);
CREATE INDEX idx_tasks_agent ON tasks(organization_id, assigned_agent_id, state);

CREATE TABLE task_dependencies (
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    task_id uuid NOT NULL,
    depends_on_task_id uuid NOT NULL,
    dependency_type text NOT NULL DEFAULT 'REQUIRES',
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (organization_id, task_id, depends_on_task_id),
    FOREIGN KEY (organization_id, task_id)
        REFERENCES tasks(organization_id, id)
        ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, depends_on_task_id)
        REFERENCES tasks(organization_id, id)
        ON DELETE RESTRICT,
    CHECK (task_id <> depends_on_task_id)
);

COMMIT;
