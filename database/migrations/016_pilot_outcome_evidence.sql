-- P2-03z — prospective, real-data-capable *aggregate* business evidence ledger.
-- SOURCE ONLY. Migration 016 MUST NOT be run on owner Kali/production or staging
-- until F04-F08, a dedicated pilot consent review and an explicit operator approval.
-- No sensitive customer rows, personal contacts, external connectors or AI agents.
BEGIN;

CREATE TABLE pilot_outcome_periods (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    project_key text NOT NULL CHECK (project_key ~ '^[a-z][a-z0-9_-]{7,63}$'),
    period_kind text NOT NULL CHECK (period_kind IN ('BASELINE','CURRENT')),
    period_start date NOT NULL,
    period_end date NOT NULL,
    currency char(3) NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
    gross_sales_minor bigint NOT NULL CHECK (gross_sales_minor BETWEEN 0 AND 1000000000000),
    variable_cost_minor bigint NOT NULL CHECK (variable_cost_minor BETWEEN 0 AND 1000000000000),
    marketing_spend_minor bigint NOT NULL CHECK (marketing_spend_minor BETWEEN 0 AND 1000000000000),
    processing_fees_minor bigint NOT NULL CHECK (processing_fees_minor BETWEEN 0 AND 1000000000000),
    fulfillment_cost_minor bigint NOT NULL CHECK (fulfillment_cost_minor BETWEEN 0 AND 1000000000000),
    software_cost_minor bigint NOT NULL CHECK (software_cost_minor BETWEEN 0 AND 1000000000000),
    refunds_minor bigint NOT NULL CHECK (refunds_minor BETWEEN 0 AND 1000000000000),
    completed_orders integer NOT NULL CHECK (completed_orders BETWEEN 0 AND 10000000),
    source_kind text NOT NULL CHECK (source_kind IN (
        'BOOKKEEPING_EXPORT','POS_SUMMARY','MANUAL_AGGREGATE')),
    source_sha256 text NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
    consent_sha256 text NOT NULL CHECK (consent_sha256 ~ '^[0-9a-f]{64}$'),
    input_sha256 text NOT NULL CHECK (input_sha256 ~ '^[0-9a-f]{64}$'),
    request_key text NOT NULL CHECK (request_key ~ '^[A-Za-z0-9_.:-]{12,100}$'),
    submitted_by_user_id uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (organization_id,id),
    UNIQUE (organization_id,request_key),
    FOREIGN KEY (organization_id,submitted_by_user_id)
        REFERENCES organization_memberships (organization_id,user_id) ON DELETE RESTRICT,
    CHECK (period_end >= period_start AND period_end < period_start + 367)
);
CREATE INDEX idx_pilot_periods_org_project
    ON pilot_outcome_periods(organization_id,project_key,period_kind,period_start);
ALTER TABLE pilot_outcome_periods ENABLE ROW LEVEL SECURITY;
ALTER TABLE pilot_outcome_periods FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_pilot_periods ON pilot_outcome_periods
    USING (organization_id=app.current_org_id())
    WITH CHECK (organization_id=app.current_org_id());
CREATE TRIGGER trg_pilot_periods_tenant
    BEFORE INSERT ON pilot_outcome_periods
    FOR EACH ROW EXECUTE FUNCTION enforce_tenant();

CREATE TABLE pilot_outcome_reviews (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    period_id uuid NOT NULL,
    reviewer_user_id uuid NOT NULL,
    decision text NOT NULL CHECK (decision IN ('EVIDENCE_CHECKED','REJECTED')),
    reason text NOT NULL CHECK (length(btrim(reason)) BETWEEN 20 AND 600),
    source_sha256_confirmed text NOT NULL CHECK (source_sha256_confirmed ~ '^[0-9a-f]{64}$'),
    reviewer_receipt_sha256 text NOT NULL CHECK (reviewer_receipt_sha256 ~ '^[0-9a-f]{64}$'),
    reviewed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (organization_id,period_id),
    FOREIGN KEY (organization_id,period_id)
        REFERENCES pilot_outcome_periods (organization_id,id) ON DELETE RESTRICT,
    FOREIGN KEY (organization_id,reviewer_user_id)
        REFERENCES organization_memberships (organization_id,user_id) ON DELETE RESTRICT
);
CREATE INDEX idx_pilot_reviews_org ON pilot_outcome_reviews(organization_id,reviewed_at DESC);
ALTER TABLE pilot_outcome_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE pilot_outcome_reviews FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_pilot_reviews ON pilot_outcome_reviews
    USING (organization_id=app.current_org_id())
    WITH CHECK (organization_id=app.current_org_id());
CREATE TRIGGER trg_pilot_reviews_tenant
    BEFORE INSERT ON pilot_outcome_reviews
    FOR EACH ROW EXECUTE FUNCTION enforce_tenant();

-- The database itself rejects self-review, hash substitution, forged reviewers
-- and a reviewer who is no longer an active OWNER/ADMIN member.
CREATE FUNCTION app.validate_pilot_evidence_review()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,public,app
AS $
DECLARE
  submitted_by uuid;
  expected_source text;
  role_in_org text;
BEGIN
  -- SECURITY DEFINER reads member status without granting runtime direct
  -- access to the membership table. Tenant and actor must match before reads.
  IF NEW.organization_id IS DISTINCT FROM app.current_org_id() THEN
    RAISE EXCEPTION 'review organization must equal authenticated tenant';
  END IF;
  IF NEW.reviewer_user_id IS DISTINCT FROM app.current_user_id() THEN
    RAISE EXCEPTION 'review identity is not the authenticated actor';
  END IF;
  SELECT p.submitted_by_user_id,p.source_sha256
    INTO submitted_by,expected_source
    FROM public.pilot_outcome_periods p
   WHERE p.organization_id=NEW.organization_id AND p.id=NEW.period_id;
  IF NOT FOUND OR submitted_by=NEW.reviewer_user_id THEN
    RAISE EXCEPTION 'independent reviewer required';
  END IF;
  IF expected_source IS DISTINCT FROM NEW.source_sha256_confirmed THEN
    RAISE EXCEPTION 'review evidence source hash mismatch';
  END IF;
  SELECT m.role::text INTO role_in_org
  FROM public.organization_memberships m
  WHERE m.organization_id=NEW.organization_id
    AND m.user_id=NEW.reviewer_user_id AND m.status='ACTIVE';
  IF role_in_org IS NULL OR role_in_org NOT IN ('OWNER','ADMIN') THEN
    RAISE EXCEPTION 'active owner or administrator reviewer required';
  END IF;
  RETURN NEW;
END
$$;
CREATE TRIGGER trg_pilot_review_checks
    BEFORE INSERT ON pilot_outcome_reviews
    FOR EACH ROW EXECUTE FUNCTION app.validate_pilot_evidence_review();

-- Immutable receipt trail: corrections require a new distinct request and
-- independent review; existing evidence and decisions cannot be rewritten.
CREATE FUNCTION app.prevent_pilot_evidence_change()
RETURNS trigger LANGUAGE plpgsql
AS $$ BEGIN RAISE EXCEPTION 'pilot evidence is append-only'; END $$;
CREATE TRIGGER trg_pilot_period_immutable
    BEFORE UPDATE OR DELETE ON pilot_outcome_periods
    FOR EACH ROW EXECUTE FUNCTION app.prevent_pilot_evidence_change();
CREATE TRIGGER trg_pilot_review_immutable
    BEFORE UPDATE OR DELETE ON pilot_outcome_reviews
    FOR EACH ROW EXECUTE FUNCTION app.prevent_pilot_evidence_change();

REVOKE ALL ON pilot_outcome_periods,pilot_outcome_reviews FROM PUBLIC;
GRANT SELECT,INSERT ON pilot_outcome_periods,pilot_outcome_reviews TO metaautomate_runtime;
-- Do not grant UPDATE, DELETE, TRUNCATE or schema ownership to runtime.

COMMIT;
