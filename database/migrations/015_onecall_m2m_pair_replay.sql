-- P2-02c source-only paired OneCall service-proof / identity-assertion admission.
-- Disposable GitHub Actions PostgreSQL only. NO runtime function grants.
BEGIN;

CREATE TABLE onecall_m2m_test_proof_redemptions (
    proof_jti uuid PRIMARY KEY,
    assertion_jti uuid NOT NULL UNIQUE
        REFERENCES onecall_identity_test_redemptions(assertion_jti) ON DELETE RESTRICT,
    service_issuer text NOT NULL CHECK (length(service_issuer) BETWEEN 9 AND 256),
    proof_expires_at timestamptz NOT NULL,
    first_seen_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    purpose text NOT NULL DEFAULT 'm2m_identity_test_only'
        CHECK (purpose = 'm2m_identity_test_only')
);

CREATE TABLE onecall_m2m_test_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    proof_jti uuid NOT NULL,
    assertion_jti uuid NOT NULL,
    outcome text NOT NULL CHECK (outcome IN ('FIRST_USE','REPLAY')),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX idx_onecall_m2m_test_events_proof
    ON onecall_m2m_test_events(proof_jti, created_at DESC);

REVOKE ALL ON onecall_m2m_test_proof_redemptions, onecall_m2m_test_events FROM PUBLIC;
REVOKE ALL ON onecall_m2m_test_proof_redemptions, onecall_m2m_test_events
    FROM metaautomate_runtime;

ALTER TABLE onecall_m2m_test_proof_redemptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE onecall_m2m_test_events ENABLE ROW LEVEL SECURITY;
-- Owner-executed SECURITY DEFINER needs owner-only writes; do not FORCE RLS
-- with no policies, as that would deny the migration-owner function too.
-- Runtime is blocked by missing privileges/policies, and no function grant exists.
-- Deliberately no runtime RLS policies or callable service route.

CREATE TRIGGER trg_onecall_m2m_redemptions_immutable
    BEFORE UPDATE OR DELETE ON onecall_m2m_test_proof_redemptions
    FOR EACH ROW EXECUTE FUNCTION prevent_onecall_identity_evidence_changes();
CREATE TRIGGER trg_onecall_m2m_events_immutable
    BEFORE UPDATE OR DELETE ON onecall_m2m_test_events
    FOR EACH ROW EXECUTE FUNCTION prevent_onecall_identity_evidence_changes();

-- All-or-nothing pair insertion in a PL/pgSQL subtransaction.
-- A concurrent conflict on either JTI rolls the entire attempted pair back;
-- the independent replay audit persists once the subtransaction ends.
-- DANGER: this SQL cannot verify a signature. Do not grant it to the runtime.
CREATE FUNCTION app.consume_onecall_m2m_identity_test_pair(
    p_assertion_jti uuid, p_proof_jti uuid,
    p_identity_issuer text, p_onecall_subject uuid, p_token_version integer,
    p_identity_exp timestamptz, p_service_issuer text, p_proof_exp timestamptz
) RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public
AS $onecall_m2m_consume$
DECLARE
    accepted boolean := FALSE;
    at_time timestamptz := clock_timestamp();
BEGIN
    IF p_assertion_jti IS NULL OR p_proof_jti IS NULL
       OR p_assertion_jti = p_proof_jti
       OR p_onecall_subject IS NULL
       OR p_token_version IS NULL OR p_token_version < 0
       OR p_identity_issuer IS NULL OR length(p_identity_issuer) > 256
       OR p_identity_issuer NOT LIKE 'https://%'
       OR p_service_issuer IS NULL OR length(p_service_issuer) > 256
       OR p_service_issuer NOT LIKE 'https://%'
       OR p_identity_exp IS NULL OR p_identity_exp <= at_time
       OR p_identity_exp > at_time + interval '65 seconds'
       OR p_proof_exp IS NULL OR p_proof_exp <= at_time
       OR p_proof_exp > at_time + interval '35 seconds' THEN
        RETURN FALSE;
    END IF;

    BEGIN
        INSERT INTO public.onecall_identity_test_redemptions
            (assertion_jti, issuer, onecall_subject, token_version, expires_at)
        VALUES (p_assertion_jti, p_identity_issuer, p_onecall_subject,
                p_token_version, p_identity_exp);
        INSERT INTO public.onecall_m2m_test_proof_redemptions
            (proof_jti, assertion_jti, service_issuer, proof_expires_at)
        VALUES (p_proof_jti, p_assertion_jti, p_service_issuer, p_proof_exp);
        accepted := TRUE;
    EXCEPTION WHEN unique_violation THEN
        accepted := FALSE;
    END;

    INSERT INTO public.onecall_m2m_test_events
        (proof_jti, assertion_jti, outcome)
    VALUES (p_proof_jti, p_assertion_jti,
            CASE WHEN accepted THEN 'FIRST_USE' ELSE 'REPLAY' END);
    RETURN accepted;
END;
$onecall_m2m_consume$;

REVOKE ALL ON FUNCTION app.consume_onecall_m2m_identity_test_pair(
    uuid, uuid, text, uuid, integer, timestamptz, text, timestamptz
) FROM PUBLIC;
REVOKE ALL ON FUNCTION app.consume_onecall_m2m_identity_test_pair(
    uuid, uuid, text, uuid, integer, timestamptz, text, timestamptz
) FROM metaautomate_runtime;

COMMIT;
