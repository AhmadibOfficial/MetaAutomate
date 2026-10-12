BEGIN;

-- Browser sessions contain only irreversible secrets, never raw API keys.
ALTER TABLE api_access_tokens
    ADD CONSTRAINT uq_api_tokens_org_id UNIQUE(organization_id, id);

CREATE TABLE workspace_sessions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    token_id uuid NOT NULL,
    session_sha256 text NOT NULL UNIQUE CHECK (session_sha256 ~ '^[0-9a-f]{64}$'),
    csrf_sha256 text NOT NULL CHECK (csrf_sha256 ~ '^[0-9a-f]{64}$'),
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    FOREIGN KEY (organization_id, user_id)
        REFERENCES organization_memberships(organization_id, user_id) ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, token_id)
        REFERENCES api_access_tokens(organization_id, id) ON DELETE RESTRICT,
    CHECK (expires_at > created_at)
);
CREATE INDEX idx_workspace_sessions_expiry ON workspace_sessions(expires_at);
CREATE INDEX idx_workspace_sessions_token ON workspace_sessions(token_id);

ALTER TABLE workspace_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE workspace_sessions FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_workspace_sessions ON workspace_sessions
    USING (organization_id = app.current_org_id())
    WITH CHECK (organization_id = app.current_org_id());

-- Privilege boundary: only SECURITY DEFINER functions may read or mutate
-- workspace sessions; the runtime application role gets no table privileges.
REVOKE ALL ON workspace_sessions FROM PUBLIC;
REVOKE ALL ON workspace_sessions FROM metaautomate_runtime;

CREATE FUNCTION app.create_workspace_session(
    p_token_sha256 text, p_session_sha256 text, p_csrf_sha256 text)
RETURNS TABLE (organization_id uuid, user_id uuid, member_role text)
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public, app
AS $$
DECLARE
    v_org uuid;
    v_user uuid;
    v_token_id uuid;
    v_expires timestamptz;
    v_role text;
BEGIN
    IF p_token_sha256 !~ '^[0-9a-f]{64}$'
        OR p_session_sha256 !~ '^[0-9a-f]{64}$'
        OR p_csrf_sha256 !~ '^[0-9a-f]{64}$' THEN
        RETURN;
    END IF;

    SELECT t.organization_id, t.user_id, t.id, t.expires_at
      INTO v_org, v_user, v_token_id, v_expires
    FROM public.api_access_tokens t
    JOIN public.organizations o ON o.id = t.organization_id
    WHERE t.token_sha256 = p_token_sha256
      AND t.revoked_at IS NULL AND t.expires_at > now()
      AND o.status = 'ACTIVE';

    IF NOT FOUND THEN RETURN; END IF;

    PERFORM pg_catalog.set_config('app.organization_id', v_org::text, true);
    PERFORM pg_catalog.set_config('app.user_id', v_user::text, true);

    SELECT m.role::text INTO v_role
      FROM public.organization_memberships m
     WHERE m.organization_id = v_org AND m.user_id = v_user
       AND m.status = 'ACTIVE';
    IF NOT FOUND THEN
        PERFORM pg_catalog.set_config('app.organization_id', '', true);
        PERFORM pg_catalog.set_config('app.user_id', '', true);
        RETURN;
    END IF;

    INSERT INTO public.workspace_sessions(
        organization_id, user_id, token_id,
        session_sha256, csrf_sha256, expires_at)
    VALUES (v_org, v_user, v_token_id, p_session_sha256, p_csrf_sha256,
            LEAST(v_expires, now() + interval '8 hours'));
    RETURN QUERY SELECT v_org, v_user, v_role;
END;
$$;

CREATE FUNCTION app.authenticate_workspace_session(
    p_session_sha256 text, p_csrf_sha256 text DEFAULT NULL)
RETURNS TABLE (organization_id uuid, user_id uuid, member_role text)
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public, app
AS $$
DECLARE
    v_org uuid;
    v_user uuid;
    v_role text;
BEGIN
    IF p_session_sha256 IS NULL OR p_session_sha256 !~ '^[0-9a-f]{64}$'
        OR (p_csrf_sha256 IS NOT NULL AND p_csrf_sha256 !~ '^[0-9a-f]{64}$') THEN
        RETURN;
    END IF;

    SELECT s.organization_id, s.user_id INTO v_org, v_user
      FROM public.workspace_sessions s
      JOIN public.api_access_tokens t
        ON t.organization_id = s.organization_id AND t.id = s.token_id
      JOIN public.organizations o ON o.id = s.organization_id
     WHERE s.session_sha256 = p_session_sha256
       AND s.revoked_at IS NULL AND s.expires_at > now()
       AND t.revoked_at IS NULL AND t.expires_at > now()
       AND o.status = 'ACTIVE'
       AND (p_csrf_sha256 IS NULL OR s.csrf_sha256 = p_csrf_sha256);

    IF NOT FOUND THEN RETURN; END IF;
    PERFORM pg_catalog.set_config('app.organization_id', v_org::text, true);
    PERFORM pg_catalog.set_config('app.user_id', v_user::text, true);

    SELECT m.role::text INTO v_role
      FROM public.organization_memberships m
     WHERE m.organization_id = v_org AND m.user_id = v_user
       AND m.status = 'ACTIVE';
    IF NOT FOUND THEN
        PERFORM pg_catalog.set_config('app.organization_id', '', true);
        PERFORM pg_catalog.set_config('app.user_id', '', true);
        RETURN;
    END IF;

    RETURN QUERY SELECT v_org, v_user, v_role;
END;
$$;

CREATE FUNCTION app.revoke_workspace_session(p_session_sha256 text)
RETURNS void
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, public, app
AS $$
BEGIN
    IF p_session_sha256 ~ '^[0-9a-f]{64}$' THEN
        UPDATE public.workspace_sessions
        SET revoked_at = now()
        WHERE session_sha256 = p_session_sha256 AND revoked_at IS NULL;
    END IF;
END;
$$;

REVOKE ALL ON FUNCTION app.create_workspace_session(text,text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION app.authenticate_workspace_session(text,text) FROM PUBLIC;
REVOKE ALL ON FUNCTION app.revoke_workspace_session(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION app.create_workspace_session(text,text,text)
    TO metaautomate_runtime;
GRANT EXECUTE ON FUNCTION app.authenticate_workspace_session(text,text)
    TO metaautomate_runtime;
GRANT EXECUTE ON FUNCTION app.revoke_workspace_session(text)
    TO metaautomate_runtime;

COMMIT;
