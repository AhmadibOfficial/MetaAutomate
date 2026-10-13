-- Operational Core v1: durable, tenant-scoped Digital Transformation Assessment
-- Assesses self-reported answers; verifies deterministic report arithmetic only.
-- No AI model, outside integrations, capability activation or external actions.
BEGIN;

CREATE TABLE digital_assessments (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    created_by_user_id uuid NOT NULL,
    business_label text NOT NULL CHECK (char_length(business_label) BETWEEN 3 AND 120),
    objective text NOT NULL CHECK (char_length(objective) BETWEEN 15 AND 300),
    answers jsonb NOT NULL CHECK (jsonb_typeof(answers) = 'array'),
    report jsonb NOT NULL CHECK (jsonb_typeof(report) = 'object'),
    input_sha256 text NOT NULL CHECK (input_sha256 ~ '^[0-9a-f]{64}$'),
    report_sha256 text NOT NULL CHECK (report_sha256 ~ '^[0-9a-f]{64}$'),
    scoring_version text NOT NULL DEFAULT '1.0.0' CHECK (scoring_version = '1.0.0'),
    request_key text NOT NULL CHECK (request_key ~ '^[A-Za-z0-9_.:-]{12,100}$'),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (organization_id, id),
    UNIQUE (organization_id, request_key),
    FOREIGN KEY (organization_id, created_by_user_id)
        REFERENCES organization_memberships(organization_id, user_id) ON DELETE RESTRICT
);
CREATE INDEX idx_digital_assessments_org_created
    ON digital_assessments (organization_id, created_at DESC);

ALTER TABLE digital_assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE digital_assessments FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_digital_assessments ON digital_assessments
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());

CREATE TRIGGER trg_digital_assessments_tenant
BEFORE INSERT ON digital_assessments
FOR EACH ROW EXECUTE FUNCTION enforce_tenant();

-- Assessment reports are immutable receipts: no modification after generation.
CREATE OR REPLACE FUNCTION prevent_assessment_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'Assessment evidence is immutable';
END;
$$;
CREATE TRIGGER trg_digital_assessments_no_update
BEFORE UPDATE ON digital_assessments
FOR EACH ROW EXECUTE FUNCTION prevent_assessment_mutation();
CREATE TRIGGER trg_digital_assessments_no_delete
BEFORE DELETE ON digital_assessments
FOR EACH ROW EXECUTE FUNCTION prevent_assessment_mutation();

REVOKE ALL ON digital_assessments FROM PUBLIC;
GRANT SELECT, INSERT ON digital_assessments TO metaautomate_runtime;
-- Runtime cannot UPDATE/DELETE assessments and cannot alter the evidence schema.
COMMIT;
