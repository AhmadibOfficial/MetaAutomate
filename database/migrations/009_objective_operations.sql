BEGIN;

-- Development API credentials: only a SHA-256 digest is retained.
-- Issuance is an out-of-band administrator action, never an unauthenticated API.
CREATE TABLE api_access_tokens (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    token_sha256 text NOT NULL UNIQUE CHECK (token_sha256 ~ '^[0-9a-f]{64}$'),
    label text NOT NULL CHECK (length(trim(label)) BETWEEN 3 AND 120),
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (organization_id, user_id)
        REFERENCES organization_memberships(organization_id, user_id) ON DELETE RESTRICT,
    CHECK (expires_at > created_at)
);
CREATE INDEX idx_api_access_tokens_org_user
    ON api_access_tokens(organization_id, user_id, expires_at);

ALTER TABLE api_access_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_access_tokens FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_api_access_tokens ON api_access_tokens
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());

-- No database password in migration history. A local bootstrap sets LOGIN credentials.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'metaautomate_runtime') THEN
        CREATE ROLE metaautomate_runtime NOLOGIN;
    END IF;
END;
$$;

GRANT USAGE ON SCHEMA public, app TO metaautomate_runtime;
GRANT SELECT ON capability_definitions, capability_dependencies TO metaautomate_runtime;
GRANT SELECT, INSERT ON objectives, workflows, tasks, task_dependencies,
    audit_events TO metaautomate_runtime;
GRANT SELECT, INSERT, UPDATE ON idempotency_keys, approvals TO metaautomate_runtime;
GRANT USAGE ON SEQUENCE audit_events_event_seq_seq TO metaautomate_runtime;

-- Protect the helper that directly sets tenant context; API users authenticate
-- through the token function instead. RLS is defense-in-depth, not an alternative
-- to parameterized SQL and authenticated principal checks.
REVOKE EXECUTE ON FUNCTION app.set_context(uuid, uuid) FROM PUBLIC;

CREATE OR REPLACE FUNCTION app.authenticate_api_token(p_sha256 text)
RETURNS TABLE(organization_id uuid, user_id uuid, member_role text)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public, app
AS $$
DECLARE
    v_org uuid;
    v_user uuid;
    v_role text;
BEGIN
    IF p_sha256 IS NULL OR p_sha256 !~ '^[0-9a-f]{64}$' THEN
        RETURN;
    END IF;

    SELECT t.organization_id, t.user_id INTO v_org, v_user
    FROM public.api_access_tokens t
    WHERE t.token_sha256 = p_sha256
      AND t.revoked_at IS NULL
      AND t.expires_at > now();

    IF NOT FOUND THEN
        RETURN;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM public.organizations o
        WHERE o.id = v_org AND o.status = 'ACTIVE'
    ) THEN
        RETURN;
    END IF;

    -- The transaction-local RLS identity is established only from a valid
    -- opaque bearer token, never a client-supplied organization header.
    PERFORM pg_catalog.set_config('app.organization_id', v_org::text, true);
    PERFORM pg_catalog.set_config('app.user_id', v_user::text, true);

    SELECT m.role::text INTO v_role
    FROM public.organization_memberships m
    WHERE m.organization_id = v_org
      AND m.user_id = v_user
      AND m.status = 'ACTIVE';

    IF NOT FOUND THEN
        PERFORM pg_catalog.set_config('app.organization_id', '', true);
        PERFORM pg_catalog.set_config('app.user_id', '', true);
        RETURN;
    END IF;

    RETURN QUERY SELECT v_org, v_user, v_role;
END;
$$;

REVOKE ALL ON FUNCTION app.authenticate_api_token(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app.authenticate_api_token(text) TO metaautomate_runtime;

COMMIT;
