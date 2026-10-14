-- P2-02b: offline-only OneCall assertion replay research with auditable no-trust boundary.
-- Applied to disposable CI PostgreSQL, never owner Kali without separate approval.
-- No API route, client permission, OneCall tenant relationship or live trust is established.
BEGIN;

CREATE TABLE onecall_identity_test_redemptions (
    assertion_jti uuid PRIMARY KEY,
    issuer text NOT NULL CHECK (length(issuer) BETWEEN 9 AND 256),
    onecall_subject uuid NOT NULL,
    token_version integer NOT NULL CHECK (token_version >= 0),
    expires_at timestamptz NOT NULL,
    first_seen_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    product text NOT NULL DEFAULT 'onecall' CHECK (product = 'onecall'),
    purpose text NOT NULL DEFAULT 'identity_test_only' CHECK (purpose = 'identity_test_only')
);

CREATE TABLE onecall_identity_test_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    assertion_jti uuid NOT NULL,
    issuer text NOT NULL,
    onecall_subject uuid NOT NULL,
    outcome text NOT NULL CHECK (outcome IN ('FIRST_USE','REPLAY')),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX idx_onecall_identity_test_events_jti
    ON onecall_identity_test_events(assertion_jti, created_at DESC);

-- Pending review records are NOT tenant bindings. They are deliberately unable
-- to grant a product or MetaAutomate organization session, even if populated.
CREATE TABLE onecall_tenant_mapping_reviews (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    onecall_subject uuid NOT NULL,
    proposed_meta_org_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    evidence_sha256 text NOT NULL CHECK (evidence_sha256 ~ '^[0-9a-f]{64}$'),
    review_state text NOT NULL DEFAULT 'PENDING' CHECK (review_state = 'PENDING'),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX idx_onecall_tenant_mapping_review_subject
    ON onecall_tenant_mapping_reviews(onecall_subject, created_at DESC);

-- No runtime role can read or write identity/tenant review internals.
REVOKE ALL ON onecall_identity_test_redemptions,
    onecall_identity_test_events, onecall_tenant_mapping_reviews FROM PUBLIC;
REVOKE ALL ON onecall_identity_test_redemptions,
    onecall_identity_test_events, onecall_tenant_mapping_reviews
    FROM metaautomate_runtime;

ALTER TABLE onecall_identity_test_redemptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE onecall_identity_test_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE onecall_tenant_mapping_reviews ENABLE ROW LEVEL SECURITY;
-- No runtime policies; all direct runtime access is denied. Owner-controlled
-- function below executes with migration-owner rights only. No runtime grant.

CREATE FUNCTION prevent_onecall_identity_evidence_changes()
RETURNS trigger LANGUAGE plpgsql AS $onecall_immutable$
BEGIN
    RAISE EXCEPTION 'OneCall identity evidence is append-only';
END;
$onecall_immutable$;
CREATE TRIGGER trg_onecall_jti_no_update
  BEFORE UPDATE OR DELETE ON onecall_identity_test_redemptions
  FOR EACH ROW EXECUTE FUNCTION prevent_onecall_identity_evidence_changes();
CREATE TRIGGER trg_onecall_events_no_update
  BEFORE UPDATE OR DELETE ON onecall_identity_test_events
  FOR EACH ROW EXECUTE FUNCTION prevent_onecall_identity_evidence_changes();
CREATE TRIGGER trg_onecall_mapping_no_change
  BEFORE UPDATE OR DELETE ON onecall_tenant_mapping_reviews
  FOR EACH ROW EXECUTE FUNCTION prevent_onecall_identity_evidence_changes();

-- Atomic, durable FIRST_USE vs REPLAY receipt. Only the migration owner can
-- invoke this now; do NOT grant to the app runtime before live identity review.
-- Signature, issuer freshness and account revocation MUST be verified outside
-- SQL before any future caller is authorized to invoke this function.
CREATE FUNCTION app.consume_onecall_identity_test_jti(
    p_jti uuid, p_issuer text, p_subject uuid, p_token_version integer,
    p_expires_at timestamptz
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public
AS $onecall_consume$
DECLARE
    accepted boolean;
    at_time timestamptz := clock_timestamp();
BEGIN
    IF p_jti IS NULL OR p_subject IS NULL
       OR p_issuer IS NULL OR length(p_issuer) < 9 OR length(p_issuer) > 256
       OR p_issuer NOT LIKE 'https://%'
       OR p_token_version IS NULL OR p_token_version < 0
       OR p_expires_at IS NULL OR p_expires_at <= at_time
       OR p_expires_at > at_time + interval '65 seconds' THEN
        RETURN FALSE;
    END IF;

    INSERT INTO public.onecall_identity_test_redemptions
       (assertion_jti, issuer, onecall_subject, token_version, expires_at)
    VALUES (p_jti, p_issuer, p_subject, p_token_version, p_expires_at)
    ON CONFLICT (assertion_jti) DO NOTHING;
    accepted := FOUND;

    INSERT INTO public.onecall_identity_test_events
       (assertion_jti, issuer, onecall_subject, outcome)
    VALUES (p_jti, p_issuer, p_subject,
            CASE WHEN accepted THEN 'FIRST_USE' ELSE 'REPLAY' END);
    RETURN accepted;
END;
$onecall_consume$;

REVOKE ALL ON FUNCTION app.consume_onecall_identity_test_jti(
    uuid, text, uuid, integer, timestamptz
) FROM PUBLIC;
REVOKE ALL ON FUNCTION app.consume_onecall_identity_test_jti(
    uuid, text, uuid, integer, timestamptz
) FROM metaautomate_runtime;
REVOKE ALL ON FUNCTION prevent_onecall_identity_evidence_changes()
    FROM PUBLIC;

COMMIT;
