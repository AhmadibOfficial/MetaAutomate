BEGIN;

-- Capability metadata is platform-global. It is NEVER tenant-specific.
-- CSV-only draft entries have no complete validated execution contract.
CREATE TABLE capability_definitions (
    capability_id text PRIMARY KEY CHECK (capability_id ~ '^[A-Z]+-[0-9]{3}$'),
    name text NOT NULL CHECK (length(trim(name)) >= 3),
    domain text NOT NULL CHECK (domain IN ('CORE','BIZ','PER','CRE','SPEC')),
    release text NOT NULL CHECK (release IN ('R1','R2','R3','R4')),
    priority text NOT NULL CHECK (priority IN ('P0','P1','P2')),
    lifecycle_status text NOT NULL DEFAULT 'DRAFT'
        CHECK (lifecycle_status IN ('DRAFT','REVIEW','ACTIVE','DEPRECATED','RETIRED')),
    is_enabled boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    CHECK (NOT is_enabled OR lifecycle_status = 'ACTIVE')
);
CREATE INDEX idx_capability_definitions_domain_release
    ON capability_definitions (domain, release, lifecycle_status);

CREATE TABLE capability_versions (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    capability_id text NOT NULL REFERENCES capability_definitions(capability_id) ON DELETE RESTRICT,
    version text NOT NULL CHECK (version ~ '^[0-9]+\.[0-9]+\.[0-9]+$'),
    version_state text NOT NULL DEFAULT 'DRAFT'
        CHECK (version_state IN ('DRAFT','REVIEW','ACTIVE','DEPRECATED','RETIRED')),
    contract jsonb,
    is_current boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    published_at timestamptz,
    UNIQUE (capability_id, version),
    CHECK (contract IS NULL OR jsonb_typeof(contract) = 'object'),
    CHECK (NOT is_current OR (contract IS NOT NULL AND version_state = 'ACTIVE'))
);
CREATE UNIQUE INDEX uq_capability_current_version
    ON capability_versions (capability_id) WHERE is_current;

CREATE TABLE capability_dependencies (
    capability_id text NOT NULL REFERENCES capability_definitions(capability_id) ON DELETE RESTRICT,
    depends_on_capability_id text NOT NULL REFERENCES capability_definitions(capability_id) ON DELETE RESTRICT,
    min_version text CHECK (min_version IS NULL OR min_version ~ '^[0-9]+\.[0-9]+\.[0-9]+$'),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (capability_id, depends_on_capability_id),
    CHECK (capability_id <> depends_on_capability_id)
);

CREATE TABLE capability_permissions (
    capability_id text NOT NULL REFERENCES capability_definitions(capability_id) ON DELETE RESTRICT,
    permission_key text NOT NULL CHECK (length(trim(permission_key)) > 0),
    requires_approval boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (capability_id, permission_key)
);

-- Tenant-specific activation is disabled by default and is not managed by the read-only API.
CREATE TABLE organization_capabilities (
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    capability_id text NOT NULL REFERENCES capability_definitions(capability_id) ON DELETE RESTRICT,
    enabled boolean NOT NULL DEFAULT false,
    pinned_version text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (organization_id, capability_id),
    FOREIGN KEY (capability_id, pinned_version)
        REFERENCES capability_versions(capability_id, version) ON DELETE RESTRICT
);

-- Execution ledger only: v1 API does not enqueue or execute capability actions.
-- Sensitive request/response contents must be redacted by the application before insertion.
CREATE TABLE capability_executions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    capability_id text NOT NULL,
    version text NOT NULL,
    workflow_id uuid,
    task_id uuid,
    status text NOT NULL DEFAULT 'QUEUED'
        CHECK (status IN ('QUEUED','RUNNING','SUCCEEDED','FAILED','REJECTED','CANCELLED')),
    idempotency_key text NOT NULL,
    request_hash text NOT NULL,
    input_redacted jsonb NOT NULL DEFAULT '{}'::jsonb,
    output_redacted jsonb NOT NULL DEFAULT '{}'::jsonb,
    approval_id uuid,
    verification_id uuid,
    started_at timestamptz,
    finished_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (organization_id, id),
    FOREIGN KEY (capability_id, version)
        REFERENCES capability_versions(capability_id, version) ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, workflow_id)
        REFERENCES workflows(organization_id, id) ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, task_id)
        REFERENCES tasks(organization_id, id) ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, approval_id)
        REFERENCES approvals(organization_id, id) ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, verification_id)
        REFERENCES verifications(organization_id, id) ON DELETE RESTRICT,
    UNIQUE (organization_id, capability_id, idempotency_key),
    CHECK (finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at)
);
CREATE INDEX idx_capability_executions_tenant_status
    ON capability_executions (organization_id, status, created_at DESC);
CREATE INDEX idx_capability_executions_tenant_cap
    ON capability_executions (organization_id, capability_id, created_at DESC);

-- Reuse the audited tenant enforcement helpers installed by migration 006.
CREATE TRIGGER trg_capability_definitions_updated
BEFORE UPDATE ON capability_definitions FOR EACH ROW EXECUTE FUNCTION set_updated_at_only();
CREATE TRIGGER trg_org_capabilities_updated
BEFORE UPDATE ON organization_capabilities FOR EACH ROW EXECUTE FUNCTION set_updated_at_only();
CREATE TRIGGER trg_capability_executions_updated
BEFORE UPDATE ON capability_executions FOR EACH ROW EXECUTE FUNCTION set_updated_at_only();

CREATE TRIGGER trg_org_capabilities_tenant_guard
BEFORE INSERT OR UPDATE ON organization_capabilities FOR EACH ROW EXECUTE FUNCTION enforce_tenant();
CREATE TRIGGER trg_org_capabilities_tenant_immutable
BEFORE UPDATE ON organization_capabilities FOR EACH ROW EXECUTE FUNCTION prevent_tenant_reassignment();
CREATE TRIGGER trg_capability_executions_tenant_guard
BEFORE INSERT OR UPDATE ON capability_executions FOR EACH ROW EXECUTE FUNCTION enforce_tenant();
CREATE TRIGGER trg_capability_executions_tenant_immutable
BEFORE UPDATE ON capability_executions FOR EACH ROW EXECUTE FUNCTION prevent_tenant_reassignment();

ALTER TABLE organization_capabilities ENABLE ROW LEVEL SECURITY;
ALTER TABLE organization_capabilities FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_organization_capabilities ON organization_capabilities
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());

ALTER TABLE capability_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE capability_executions FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_capability_executions ON capability_executions
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());

COMMIT;
