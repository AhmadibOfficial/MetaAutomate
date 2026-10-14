-- AMBOY M1: MetaAutomate-only, no-model admission ledger.
-- CI uses a disposable DB. Never run this against Kali without separate approval.
BEGIN;

CREATE TABLE amboy_m1_requests (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    actor_user_id uuid NOT NULL,
    product text NOT NULL DEFAULT 'metaautomate' CHECK (product = 'metaautomate'),
    client_request_id uuid NOT NULL,
    conversation_id uuid NOT NULL,
    payload_sha256 text NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    outcome text NOT NULL DEFAULT 'unsupported' CHECK (outcome = 'unsupported'),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (organization_id, actor_user_id, client_request_id),
    UNIQUE (organization_id, id),
    FOREIGN KEY (organization_id, actor_user_id)
        REFERENCES organization_memberships(organization_id, user_id) ON DELETE RESTRICT
);
CREATE INDEX idx_amboy_m1_requests_org_created
    ON amboy_m1_requests(organization_id, created_at DESC);

CREATE TABLE amboy_m1_quotas (
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    actor_user_id uuid NOT NULL,
    product text NOT NULL CHECK (product = 'metaautomate'),
    hour_start timestamptz NOT NULL,
    request_count integer NOT NULL CHECK (request_count BETWEEN 1 AND 10),
    PRIMARY KEY (organization_id, actor_user_id, product, hour_start),
    FOREIGN KEY (organization_id, actor_user_id)
        REFERENCES organization_memberships(organization_id, user_id) ON DELETE RESTRICT
);

ALTER TABLE amboy_m1_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE amboy_m1_requests FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_amboy_m1_requests ON amboy_m1_requests
    USING (organization_id = app.current_org_id()
        AND actor_user_id = NULLIF(current_setting('app.user_id', true), '')::uuid)
    WITH CHECK (organization_id = app.current_org_id()
        AND actor_user_id = NULLIF(current_setting('app.user_id', true), '')::uuid);
ALTER TABLE amboy_m1_quotas ENABLE ROW LEVEL SECURITY;
ALTER TABLE amboy_m1_quotas FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_amboy_m1_quotas ON amboy_m1_quotas
    USING (organization_id = app.current_org_id()
        AND actor_user_id = NULLIF(current_setting('app.user_id', true), '')::uuid)
    WITH CHECK (organization_id = app.current_org_id()
        AND actor_user_id = NULLIF(current_setting('app.user_id', true), '')::uuid);

CREATE FUNCTION prevent_amboy_m1_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'AMBOY M1 evidence is append-only';
END;
$$;
CREATE TRIGGER trg_amboy_m1_requests_no_update BEFORE UPDATE ON amboy_m1_requests
    FOR EACH ROW EXECUTE FUNCTION prevent_amboy_m1_mutation();
CREATE TRIGGER trg_amboy_m1_requests_no_delete BEFORE DELETE ON amboy_m1_requests
    FOR EACH ROW EXECUTE FUNCTION prevent_amboy_m1_mutation();

-- Prevent any runtime caller from resetting quotas, moving an actor's
-- hourly window or shifting counters between organizations.
CREATE FUNCTION enforce_amboy_m1_quota_increment()
RETURNS trigger LANGUAGE plpgsql AS $amboy_quota$
BEGIN
    IF NEW.organization_id IS DISTINCT FROM OLD.organization_id
       OR NEW.actor_user_id IS DISTINCT FROM OLD.actor_user_id
       OR NEW.product IS DISTINCT FROM OLD.product
       OR NEW.hour_start IS DISTINCT FROM OLD.hour_start
       OR NEW.request_count IS DISTINCT FROM OLD.request_count + 1 THEN
        RAISE EXCEPTION 'AMBOY M1 quota may only increment for the same actor and hour';
    END IF;
    RETURN NEW;
END;
$amboy_quota$;
CREATE TRIGGER trg_amboy_m1_quotas_increment
    BEFORE UPDATE ON amboy_m1_quotas
    FOR EACH ROW EXECUTE FUNCTION enforce_amboy_m1_quota_increment();

REVOKE ALL ON FUNCTION prevent_amboy_m1_mutation() FROM PUBLIC;
REVOKE ALL ON FUNCTION enforce_amboy_m1_quota_increment() FROM PUBLIC;
REVOKE ALL ON amboy_m1_requests, amboy_m1_quotas FROM PUBLIC;
REVOKE ALL ON amboy_m1_requests, amboy_m1_quotas FROM metaautomate_runtime;
GRANT SELECT, INSERT ON amboy_m1_requests TO metaautomate_runtime;
GRANT SELECT, INSERT, UPDATE ON amboy_m1_quotas TO metaautomate_runtime;
COMMIT;
