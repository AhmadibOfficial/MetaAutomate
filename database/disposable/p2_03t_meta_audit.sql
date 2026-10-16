-- P2-03t: DISPOSABLE CI AUDIT EXTENSION, NOT A PRODUCTION MIGRATION.
-- Apply *after* p2_03s_meta_leads_staging.sql to meta_stage_ci only.
DO $guard$ BEGIN
  IF current_database() <> 'meta_stage_ci'
    OR current_setting('metaautomate.disposable', true) IS DISTINCT FROM 'yes'
  THEN RAISE EXCEPTION 'DISPOSABLE_CI_ONLY'; END IF;
END $guard$;

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;

CREATE TABLE meta_stage.audit_events (
    tenant_id uuid NOT NULL,
    sequence_number bigint NOT NULL CHECK (sequence_number > 0),
    source_login name NOT NULL,
    payload jsonb NOT NULL,
    previous_sha256 text NOT NULL CHECK (previous_sha256 ~ '^[0-9a-f]{64}$'),
    entry_sha256 text NOT NULL CHECK (entry_sha256 ~ '^[0-9a-f]{64}$'),
    recorded_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, sequence_number)
);

ALTER TABLE meta_stage.audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE meta_stage.audit_events FORCE ROW LEVEL SECURITY;
CREATE POLICY audit_reader_tenant ON meta_stage.audit_events
  FOR SELECT USING (tenant_id = meta_stage.session_tenant());

REVOKE ALL ON meta_stage.audit_events FROM PUBLIC;

-- Trigger is owned by the disposable CI database superuser. It holds an
-- advisory lock per tenant for a serialized hash chain, with inserts in the
-- SAME COMMIT as the protected event. Runtime roles get no audit INSERT,
-- UPDATE, DELETE or TRUNCATE privileges.
CREATE FUNCTION meta_stage.append_change_audit() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, meta_stage, public
AS $audit_body$
DECLARE
  tenant uuid;
  next_seq bigint;
  prev_hash text;
  meta jsonb;
  digest_hex text;
BEGIN
  tenant := NEW.tenant_id;
  PERFORM pg_advisory_xact_lock(hashtextextended(tenant::text, 0));
  SELECT sequence_number, entry_sha256
    INTO next_seq, prev_hash
    FROM meta_stage.audit_events
    WHERE tenant_id = tenant
    ORDER BY sequence_number DESC LIMIT 1;
  next_seq := COALESCE(next_seq, 0) + 1;
  prev_hash := COALESCE(prev_hash, repeat('0', 64));
  meta := jsonb_build_object(
    'sequence_number', next_seq,
    'tenant', tenant::text,
    'source_login', session_user::text,
    'table', TG_TABLE_NAME,
    'operation', TG_OP,
    'platform', to_jsonb(NEW)->>'platform',
    'account', to_jsonb(NEW)->>'account_ref',
    'event', to_jsonb(NEW)->>'event_ref',
    'state', COALESCE(to_jsonb(NEW)->>'state',
                      to_jsonb(NEW)->>'reviewed_state'),
    'purpose', to_jsonb(NEW)->>'purpose'
  );
  digest_hex := encode(public.digest(
    convert_to(prev_hash || ':' || meta::text, 'UTF8'), 'sha256'
  ), 'hex');
  INSERT INTO meta_stage.audit_events
    (tenant_id, sequence_number, source_login, payload,
     previous_sha256, entry_sha256)
  VALUES (tenant, next_seq, session_user, meta, prev_hash, digest_hex);
  RETURN NEW;
END
$audit_body$;
REVOKE ALL ON FUNCTION meta_stage.append_change_audit() FROM PUBLIC;

CREATE TRIGGER accounts_audit AFTER INSERT ON meta_stage.accounts
  FOR EACH ROW EXECUTE FUNCTION meta_stage.append_change_audit();
CREATE TRIGGER events_audit AFTER INSERT ON meta_stage.events
  FOR EACH ROW EXECUTE FUNCTION meta_stage.append_change_audit();
CREATE TRIGGER evidence_audit AFTER INSERT ON meta_stage.private_evidence
  FOR EACH ROW EXECUTE FUNCTION meta_stage.append_change_audit();
CREATE TRIGGER consent_audit AFTER INSERT ON meta_stage.consent_reviews
  FOR EACH ROW EXECUTE FUNCTION meta_stage.append_change_audit();
CREATE TRIGGER review_task_audit AFTER INSERT OR UPDATE ON meta_stage.review_tasks
  FOR EACH ROW EXECUTE FUNCTION meta_stage.append_change_audit();

-- No producer or consumer (Graph, Instagram or WhatsApp) is activated.
