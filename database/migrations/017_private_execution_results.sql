-- P2-052: real private task results, 7-day access expiry, tenant RLS.
-- SOURCE ONLY: DO NOT APPLY until signed private staging authorization,
-- restricted database connection, encrypted storage and operator data deletion
-- controls are verified. Migration 012-016 dependencies are not waived.
BEGIN;

CREATE TABLE private_execution_results (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    actor_user_id uuid NOT NULL,
    request_key text NOT NULL CHECK (request_key ~ '^[A-Za-z0-9_.:-]{12,100}$'),
    task_type text NOT NULL CHECK (task_type IN (
        'INVENTORY_REORDER_CSV','ORIGINAL_BRANDED_SVG','LOCAL_MODEL_TEXT'
    )),
    input_sha256 text NOT NULL CHECK (input_sha256 ~ '^[0-9a-f]{64}$'),
    artifact_sha256 text NOT NULL CHECK (artifact_sha256 ~ '^[0-9a-f]{64}$'),
    artifact_mime text NOT NULL CHECK (artifact_mime IN (
        'text/csv; charset=utf-8','image/svg+xml','text/plain; charset=utf-8'
    )),
    artifact_filename text NOT NULL CHECK (
        artifact_filename IN (
            'inventory-reorder.csv','original-brand-graphic.svg',
            'model-generated-text.txt'
        )
    ),
    artifact_bytes integer NOT NULL CHECK (
        artifact_bytes BETWEEN 1 AND 130000
    ),
    artifact bytea NOT NULL,
    result_metadata jsonb NOT NULL CHECK (jsonb_typeof(result_metadata)='object'),
    status text NOT NULL DEFAULT 'COMPLETED' CHECK (status='COMPLETED'),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    expires_at timestamptz NOT NULL,
    UNIQUE (organization_id,id),
    UNIQUE (organization_id,actor_user_id,request_key),
    FOREIGN KEY (organization_id,actor_user_id)
      REFERENCES organization_memberships(organization_id,user_id)
      ON DELETE RESTRICT,
    CHECK (octet_length(artifact)=artifact_bytes),
    CHECK (expires_at > created_at),
    CHECK (expires_at <= created_at + interval '8 days')
);

CREATE INDEX idx_private_execution_actor
ON private_execution_results (organization_id, actor_user_id, created_at DESC);

CREATE INDEX idx_private_execution_expiry
ON private_execution_results (expires_at);

ALTER TABLE private_execution_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE private_execution_results FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_private_execution_results
ON private_execution_results
USING (organization_id=app.current_org_id()
       AND actor_user_id=app.current_user_id())
WITH CHECK (organization_id=app.current_org_id()
            AND actor_user_id=app.current_user_id());

CREATE TRIGGER trg_private_execution_tenant
BEFORE INSERT ON private_execution_results
FOR EACH ROW EXECUTE FUNCTION enforce_tenant();

-- Runtime may not mutate completed artifacts. Only a separately authorized
-- privileged maintenance identity may perform expired-row deletion.
REVOKE ALL ON private_execution_results FROM PUBLIC;
GRANT SELECT, INSERT ON private_execution_results TO metaautomate_runtime;
COMMIT;
