BEGIN;

-- Transaction-local tenant context helper. The API should call SET LOCAL before queries.
CREATE OR REPLACE FUNCTION app.set_context(p_organization_id uuid, p_user_id uuid DEFAULT NULL)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    PERFORM set_config('app.organization_id', p_organization_id::text, true);
    IF p_user_id IS NOT NULL THEN
        PERFORM set_config('app.user_id', p_user_id::text, true);
    ELSE
        PERFORM set_config('app.user_id', '', true);
    END IF;
END;
$$;

-- Optimistic locking helper for application-generated UPDATE statements.
-- Example: UPDATE leads SET ... WHERE id = $1 AND organization_id = app.current_org_id() AND lock_version = $2;
CREATE OR REPLACE FUNCTION app.assert_membership(p_organization_id uuid, p_user_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM organization_memberships m
        WHERE m.organization_id = p_organization_id
          AND m.user_id = p_user_id
          AND m.status = 'ACTIVE'
    );
$$;

COMMIT;
