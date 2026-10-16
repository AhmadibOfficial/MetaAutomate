-- P2-03r SECURITY BLUEPRINT ONLY. DO NOT APPLY TO ANY DATABASE.
-- Draft PostgreSQL 16 schema for independent review, not a migration or an
-- approved production CRM. Stores only platform event metadata and consent
-- evidence references; no names, phone numbers, emails or message bodies.
-- Live setup requires tenant auth and app roles, KMS, retention, DSR and
-- independent verification. Requires the application to set app.tenant_id
-- only after authenticating the tenant, in a transaction-local context.
BEGIN;

CREATE SCHEMA IF NOT EXISTS meta_leads;

CREATE TABLE meta_leads.accounts (
    tenant_id uuid NOT NULL,
    account_ref text NOT NULL CHECK (length(account_ref) BETWEEN 6 AND 128),
    platform text NOT NULL CHECK (platform IN ('FACEBOOK','INSTAGRAM','WHATSAPP')),
    provider_ownership_verified boolean NOT NULL DEFAULT false,
    access_reviewed_at timestamptz,
    PRIMARY KEY (tenant_id, platform, account_ref)
);

CREATE TABLE meta_leads.events (
    tenant_id uuid NOT NULL,
    platform text NOT NULL CHECK (platform IN ('FACEBOOK','INSTAGRAM','WHATSAPP')),
    account_ref text NOT NULL,
    event_ref text NOT NULL CHECK (length(event_ref) BETWEEN 6 AND 128),
    kind text NOT NULL,
    signed_payload_sha256 text NOT NULL CHECK (signed_payload_sha256 ~ '^[0-9a-f]{64}$'),
    received_at timestamptz NOT NULL DEFAULT now(),
    -- do not persist raw webhook bodies or contact identifiers in this blueprint
    PRIMARY KEY (tenant_id, platform, account_ref, event_ref),
    FOREIGN KEY (tenant_id, platform, account_ref)
        REFERENCES meta_leads.accounts (tenant_id, platform, account_ref)
);

CREATE TABLE meta_leads.consent_reviews (
    review_id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    platform text NOT NULL,
    account_ref text NOT NULL,
    event_ref text NOT NULL,
    purpose text NOT NULL CHECK (purpose IN ('SERVICE','MARKETING')),
    decision text NOT NULL CHECK (decision IN ('UNVERIFIED','GRANTED_EXAMPLE','REVOKED_EXAMPLE')),
    -- evidence refs point to an independently governed future evidence service
    evidence_ref text NOT NULL,
    reviewer_ref text NOT NULL,
    observed_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (tenant_id, platform, account_ref, event_ref)
        REFERENCES meta_leads.events (tenant_id, platform, account_ref, event_ref)
);

CREATE TABLE meta_leads.human_review_tasks (
    task_id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    platform text NOT NULL,
    account_ref text NOT NULL,
    event_ref text NOT NULL,
    state text NOT NULL DEFAULT 'HUMAN_REVIEW_REQUIRED'
        CHECK (state IN ('HUMAN_REVIEW_REQUIRED','ASSIGNED_SYNTHETIC_HUMAN','CLOSED')),
    assigned_agent_ref text,
    external_execution_enabled boolean NOT NULL DEFAULT false
        CHECK (external_execution_enabled = false),
    FOREIGN KEY (tenant_id, platform, account_ref, event_ref)
        REFERENCES meta_leads.events (tenant_id, platform, account_ref, event_ref),
    UNIQUE (tenant_id, platform, account_ref, event_ref)
);

-- Tenant isolation must apply even to table owners. Privileges are not granted
-- here; an independently provisioned non-BYPASSRLS runtime role is required.
ALTER TABLE meta_leads.accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE meta_leads.accounts FORCE ROW LEVEL SECURITY;
ALTER TABLE meta_leads.events ENABLE ROW LEVEL SECURITY;
ALTER TABLE meta_leads.events FORCE ROW LEVEL SECURITY;
ALTER TABLE meta_leads.consent_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE meta_leads.consent_reviews FORCE ROW LEVEL SECURITY;
ALTER TABLE meta_leads.human_review_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE meta_leads.human_review_tasks FORCE ROW LEVEL SECURITY;

CREATE POLICY accounts_tenant ON meta_leads.accounts
    USING (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);
CREATE POLICY events_tenant ON meta_leads.events
    USING (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);
CREATE POLICY consent_tenant ON meta_leads.consent_reviews
    USING (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);
CREATE POLICY tasks_tenant ON meta_leads.human_review_tasks
    USING (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
    WITH CHECK (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);

REVOKE ALL ON SCHEMA meta_leads FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA meta_leads FROM PUBLIC;
-- No GRANT to public, no auto provision, no migration authorization.
COMMIT;
