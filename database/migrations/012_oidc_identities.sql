-- OIDC identity extension follows previously installed Operational Assessment migration 011.
-- Never apply this to the owner's development database without separate authorization.
BEGIN;

-- OIDC identities must be provisioned by an administrator after the
-- identity provider and intended organization membership are verified.
-- Identity issuer+subject is globally unique: no arbitrary org selection.
CREATE TABLE oidc_identities (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    issuer text NOT NULL CHECK (issuer LIKE 'https://%' AND length(issuer) <= 512),
    subject_sha256 text NOT NULL CHECK (subject_sha256 ~ '^[0-9a-f]{64}$'),
    status text NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE','REVOKED')),
    created_at timestamptz NOT NULL DEFAULT now(),
    revoked_at timestamptz,
    UNIQUE (issuer, subject_sha256),
    UNIQUE (organization_id,id),
    FOREIGN KEY (organization_id,user_id)
        REFERENCES organization_memberships(organization_id,user_id) ON DELETE RESTRICT
);

ALTER TABLE oidc_identities ENABLE ROW LEVEL SECURITY;
ALTER TABLE oidc_identities FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_oidc_identities ON oidc_identities
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());

REVOKE ALL ON oidc_identities FROM PUBLIC;
REVOKE ALL ON oidc_identities FROM metaautomate_runtime;

-- Preserve all existing local key-based sessions; new OIDC sessions use an
-- identity mapping rather than requiring a legacy API access token.
ALTER TABLE workspace_sessions ALTER COLUMN token_id DROP NOT NULL;
ALTER TABLE workspace_sessions ADD COLUMN oidc_identity_id uuid;
ALTER TABLE workspace_sessions
    ADD CONSTRAINT fk_workspace_sessions_oidc_identity
    FOREIGN KEY (organization_id,oidc_identity_id)
    REFERENCES oidc_identities(organization_id,id) ON DELETE RESTRICT;
ALTER TABLE workspace_sessions
    ADD CONSTRAINT ck_workspace_one_auth_method
    CHECK ((token_id IS NOT NULL) <> (oidc_identity_id IS NOT NULL));
CREATE INDEX idx_workspace_sessions_identity ON workspace_sessions(oidc_identity_id);

CREATE FUNCTION app.create_oidc_workspace_session(
    p_issuer text, p_subject_sha256 text,
    p_session_sha256 text, p_csrf_sha256 text)
RETURNS TABLE(organization_id uuid, user_id uuid, member_role text)
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public, app
AS $$
DECLARE
    v_org uuid;
    v_user uuid;
    v_oidc_id uuid;
    v_role text;
BEGIN
    -- Invalid/missing identity can never inherit an earlier tenant context.
    PERFORM pg_catalog.set_config('app.organization_id', '', true);
    PERFORM pg_catalog.set_config('app.user_id', '', true);
    -- Explicit NULL checks avoid SQL's three-valued OR semantics:
    -- a missing digest must deny, never reach an INSERT with NULL values.
    IF p_issuer IS NULL OR p_issuer NOT LIKE 'https://%'
       OR length(p_issuer) > 512
       OR p_subject_sha256 IS NULL
       OR p_subject_sha256 !~ '^[0-9a-f]{64}$'
       OR p_session_sha256 IS NULL
       OR p_session_sha256 !~ '^[0-9a-f]{64}$'
       OR p_csrf_sha256 IS NULL
       OR p_csrf_sha256 !~ '^[0-9a-f]{64}$' THEN
       RETURN;
    END IF;

    SELECT i.organization_id, i.user_id, i.id
      INTO v_org, v_user, v_oidc_id
      FROM public.oidc_identities i
      JOIN public.organizations o ON o.id=i.organization_id
     WHERE i.issuer=p_issuer AND i.subject_sha256=p_subject_sha256
       AND i.status='ACTIVE' AND i.revoked_at IS NULL AND o.status='ACTIVE';
    IF NOT FOUND THEN RETURN; END IF;

    PERFORM pg_catalog.set_config('app.organization_id', v_org::text, true);
    PERFORM pg_catalog.set_config('app.user_id', v_user::text, true);
    SELECT m.role::text INTO v_role FROM public.organization_memberships m
     WHERE m.organization_id=v_org AND m.user_id=v_user AND m.status='ACTIVE';
    IF NOT FOUND THEN
        -- Denied tenant membership must not leak an authorization context.
        PERFORM pg_catalog.set_config('app.organization_id', '', true);
        PERFORM pg_catalog.set_config('app.user_id', '', true);
        RETURN;
    END IF;

    INSERT INTO public.workspace_sessions (
        organization_id,user_id,oidc_identity_id,session_sha256,csrf_sha256,expires_at
    ) VALUES (
        v_org,v_user,v_oidc_id,p_session_sha256,p_csrf_sha256,
        now()+interval '1 hour'
    );
    RETURN QUERY SELECT v_org,v_user,v_role;
END;
$$;

-- Replace the session verifier without changing its public contract.
CREATE OR REPLACE FUNCTION app.authenticate_workspace_session(
    p_session_sha256 text, p_csrf_sha256 text DEFAULT NULL)
RETURNS TABLE(organization_id uuid, user_id uuid, member_role text)
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public, app
AS $$
DECLARE
    v_org uuid;
    v_user uuid;
    v_role text;
BEGIN
    -- Invalid/expired sessions can never inherit an earlier tenant context.
    PERFORM pg_catalog.set_config('app.organization_id', '', true);
    PERFORM pg_catalog.set_config('app.user_id', '', true);
    IF p_session_sha256 IS NULL OR p_session_sha256 !~ '^[0-9a-f]{64}$'
       OR (p_csrf_sha256 IS NOT NULL AND p_csrf_sha256 !~ '^[0-9a-f]{64}$') THEN
        RETURN;
    END IF;

    SELECT s.organization_id,s.user_id INTO v_org,v_user
      FROM public.workspace_sessions s
      JOIN public.organizations o ON o.id=s.organization_id
      LEFT JOIN public.api_access_tokens t
             ON t.organization_id=s.organization_id AND t.id=s.token_id
      LEFT JOIN public.oidc_identities i
             ON i.organization_id=s.organization_id AND i.id=s.oidc_identity_id
     WHERE s.session_sha256=p_session_sha256
       AND s.revoked_at IS NULL AND s.expires_at>now()
       AND o.status='ACTIVE'
       AND (p_csrf_sha256 IS NULL OR s.csrf_sha256=p_csrf_sha256)
       AND (
            (s.token_id IS NOT NULL
             AND t.revoked_at IS NULL AND t.expires_at>now())
            OR
            (s.oidc_identity_id IS NOT NULL AND i.status='ACTIVE'
             AND i.revoked_at IS NULL AND i.user_id=s.user_id)
       );

    IF NOT FOUND THEN RETURN; END IF;
    PERFORM pg_catalog.set_config('app.organization_id',v_org::text,true);
    PERFORM pg_catalog.set_config('app.user_id',v_user::text,true);

    SELECT m.role::text INTO v_role FROM public.organization_memberships m
     WHERE m.organization_id=v_org AND m.user_id=v_user AND m.status='ACTIVE';
    IF NOT FOUND THEN
        -- A revoked membership must not leave the session tenant GUC set.
        PERFORM pg_catalog.set_config('app.organization_id', '', true);
        PERFORM pg_catalog.set_config('app.user_id', '', true);
        RETURN;
    END IF;
    RETURN QUERY SELECT v_org,v_user,v_role;
END;
$$;

-- Stage 01 F06: narrow the legacy session revoker to the authenticated
-- transaction principal. A runtime caller must not revoke another user's
-- or another tenant's session by presenting its opaque session digest.
-- This changes the candidate migration only; it is not applied here.
CREATE OR REPLACE FUNCTION app.revoke_workspace_session(p_session_sha256 text)
RETURNS void
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public, app
AS $$
DECLARE
    v_org text;
    v_user text;
BEGIN
    v_org := pg_catalog.current_setting('app.organization_id', true);
    v_user := pg_catalog.current_setting('app.user_id', true);
    IF p_session_sha256 IS NULL OR p_session_sha256 !~ '^[0-9a-f]{64}$'
       OR v_org IS NULL OR v_org = ''
       OR v_user IS NULL OR v_user = '' THEN
        RETURN;
    END IF;

    UPDATE public.workspace_sessions
       SET revoked_at = now()
     WHERE session_sha256 = p_session_sha256
       AND organization_id = v_org::uuid
       AND user_id = v_user::uuid
       AND revoked_at IS NULL;
END;
$$;

REVOKE ALL ON FUNCTION app.create_oidc_workspace_session(text,text,text,text)
    FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app.create_oidc_workspace_session(text,text,text,text)
    TO metaautomate_runtime;

COMMIT;
