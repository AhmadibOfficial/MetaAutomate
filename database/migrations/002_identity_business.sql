BEGIN;

CREATE TABLE organizations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug text NOT NULL UNIQUE,
    name text NOT NULL,
    status organization_status NOT NULL DEFAULT 'ACTIVE',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email citext NOT NULL UNIQUE,
    display_name text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE organization_memberships (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    user_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    role membership_role NOT NULL,
    status membership_status NOT NULL DEFAULT 'ACTIVE',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (organization_id, user_id),
    UNIQUE (organization_id, id)
);
CREATE INDEX idx_memberships_user ON organization_memberships(user_id);
CREATE INDEX idx_memberships_org_status ON organization_memberships(organization_id, status);

CREATE TABLE business_profiles (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    legal_name text,
    trading_name text,
    industry text,
    description text,
    website_url text,
    phone text,
    email citext,
    timezone text NOT NULL DEFAULT 'UTC',
    business_context jsonb NOT NULL DEFAULT '{}'::jsonb,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    created_by_user_id uuid,
    updated_by_user_id uuid,
    lock_version integer NOT NULL DEFAULT 1,
    UNIQUE (organization_id),
    UNIQUE (organization_id, id),
    FOREIGN KEY (organization_id, created_by_user_id)
        REFERENCES organization_memberships(organization_id, user_id)
        ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, updated_by_user_id)
        REFERENCES organization_memberships(organization_id, user_id)
        ON DELETE RESTRICT
);

CREATE TABLE integrations (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    type integration_type NOT NULL,
    provider text NOT NULL,
    status integration_status NOT NULL DEFAULT 'ACTIVE',
    external_account_id text,
    credentials_ref text,
    config jsonb NOT NULL DEFAULT '{}'::jsonb,
    last_health_check_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    created_by_user_id uuid,
    updated_by_user_id uuid,
    UNIQUE (organization_id, id),
    FOREIGN KEY (organization_id, created_by_user_id)
        REFERENCES organization_memberships(organization_id, user_id)
        ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, updated_by_user_id)
        REFERENCES organization_memberships(organization_id, user_id)
        ON DELETE RESTRICT
);
CREATE UNIQUE INDEX uq_integration_external_account
    ON integrations (organization_id, type, provider, external_account_id)
    WHERE external_account_id IS NOT NULL;
CREATE INDEX idx_integrations_org_type
    ON integrations(organization_id, type, status);

COMMIT;
