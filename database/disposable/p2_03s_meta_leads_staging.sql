-- P2-03s: DISPOSABLE CI POSTGRESQL REHEARSAL ONLY.
-- Never apply to Kali, production, a shared database, or real customer data.
-- Uses session_user -> sealed database login mapping; does NOT trust app.tenant_id.
DO $guard$ BEGIN
  IF current_database() <> 'meta_stage_ci'
     OR current_setting('metaautomate.disposable', true) IS DISTINCT FROM 'yes'
  THEN RAISE EXCEPTION 'DISPOSABLE_CI_ONLY'; END IF;
END $guard$;

CREATE SCHEMA meta_stage;
REVOKE ALL ON SCHEMA meta_stage FROM PUBLIC;

CREATE TABLE meta_stage.login_tenants (
  login_role name PRIMARY KEY,
  tenant_id uuid NOT NULL UNIQUE
);
REVOKE ALL ON meta_stage.login_tenants FROM PUBLIC;

CREATE FUNCTION meta_stage.session_tenant() RETURNS uuid
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = pg_catalog, meta_stage AS $$
  SELECT tenant_id FROM meta_stage.login_tenants
    WHERE login_role = session_user
$$;
REVOKE ALL ON FUNCTION meta_stage.session_tenant() FROM PUBLIC;

CREATE TABLE meta_stage.accounts (
 tenant_id uuid NOT NULL,
 platform text NOT NULL CHECK (platform IN ('FACEBOOK','INSTAGRAM','WHATSAPP')),
 account_ref text NOT NULL CHECK (account_ref ~ '^SIM-[A-Z0-9-]{3,48}$'),
 provider_verified boolean NOT NULL DEFAULT false CHECK (provider_verified = false),
 PRIMARY KEY (tenant_id, platform, account_ref)
);

CREATE TABLE meta_stage.events (
 tenant_id uuid NOT NULL,
 platform text NOT NULL,
 account_ref text NOT NULL,
 event_ref text NOT NULL CHECK (event_ref ~ '^SIM-[A-Z0-9-]{3,48}$'),
 payload_sha256 text NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
 event_kind text NOT NULL,
 inserted_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY (tenant_id, platform, account_ref, event_ref),
 FOREIGN KEY (tenant_id, platform, account_ref)
  REFERENCES meta_stage.accounts(tenant_id, platform, account_ref)
);

CREATE TABLE meta_stage.private_evidence (
 tenant_id uuid NOT NULL,
 platform text NOT NULL,
 account_ref text NOT NULL,
 event_ref text NOT NULL,
 nonce bytea NOT NULL CHECK (octet_length(nonce) = 12),
 ciphertext bytea NOT NULL CHECK (octet_length(ciphertext) >= 16
                                      AND octet_length(ciphertext) <= 8192),
 key_version integer NOT NULL DEFAULT 1 CHECK (key_version = 1),
 PRIMARY KEY (tenant_id, platform, account_ref, event_ref),
 FOREIGN KEY (tenant_id, platform, account_ref, event_ref)
  REFERENCES meta_stage.events(tenant_id, platform, account_ref, event_ref)
);

CREATE TABLE meta_stage.consent_reviews (
 tenant_id uuid NOT NULL,
 platform text NOT NULL,
 account_ref text NOT NULL,
 event_ref text NOT NULL,
 evidence_ref text NOT NULL CHECK (evidence_ref ~ '^SIM-[A-Z0-9-]{3,48}$'),
 purpose text NOT NULL CHECK (purpose IN ('SERVICE', 'MARKETING')),
 reviewed_state text NOT NULL CHECK (reviewed_state IN ('UNVERIFIED','DOCUMENTED_EXAMPLE','REVOKED_EXAMPLE')),
 actor_ref text NOT NULL CHECK (actor_ref ~ '^SIM-AGENT-[A-Z0-9-]{2,40}$'),
 reviewed_at timestamptz NOT NULL DEFAULT now(),
 FOREIGN KEY (tenant_id, platform, account_ref, event_ref)
  REFERENCES meta_stage.events(tenant_id, platform, account_ref, event_ref),
 PRIMARY KEY (tenant_id, platform, account_ref, event_ref, evidence_ref)
);

CREATE TABLE meta_stage.review_tasks (
 tenant_id uuid NOT NULL,
 platform text NOT NULL,
 account_ref text NOT NULL,
 event_ref text NOT NULL,
 state text NOT NULL DEFAULT 'HUMAN_REVIEW_REQUIRED'
    CHECK (state IN ('HUMAN_REVIEW_REQUIRED','ASSIGNED_SYNTHETIC_HUMAN','CLOSED')),
 agent_ref text CHECK (agent_ref IS NULL OR agent_ref ~ '^SIM-AGENT-[A-Z0-9-]{2,40}$'),
 outbound_enabled boolean NOT NULL DEFAULT false CHECK (outbound_enabled = false),
 PRIMARY KEY (tenant_id, platform, account_ref, event_ref),
 FOREIGN KEY (tenant_id, platform, account_ref, event_ref)
  REFERENCES meta_stage.events(tenant_id, platform, account_ref, event_ref)
);

-- Transaction-serialized append-only revocation guard. A caller with direct
-- INSERT privilege cannot bypass it by skipping the Python review client.
CREATE FUNCTION meta_stage.guard_consent_revocation() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, meta_stage AS $
BEGIN
  PERFORM pg_advisory_xact_lock(hashtextextended(
    NEW.tenant_id::text || '|' || NEW.platform || '|' || NEW.account_ref
    || '|' || NEW.event_ref || '|' || NEW.purpose, 0));
  IF NEW.reviewed_state = 'DOCUMENTED_EXAMPLE' AND EXISTS (
    SELECT 1 FROM meta_stage.consent_reviews
    WHERE tenant_id = NEW.tenant_id AND platform = NEW.platform
      AND account_ref = NEW.account_ref AND event_ref = NEW.event_ref
      AND purpose = NEW.purpose AND reviewed_state = 'REVOKED_EXAMPLE'
  ) THEN
    RAISE EXCEPTION 'CONSENT_REVOKED_REVIEW_REQUIRED';
  END IF;
  RETURN NEW;
END $;
REVOKE ALL ON FUNCTION meta_stage.guard_consent_revocation() FROM PUBLIC;
CREATE TRIGGER consent_revocation_guard
  BEFORE INSERT ON meta_stage.consent_reviews
  FOR EACH ROW EXECUTE FUNCTION meta_stage.guard_consent_revocation();

-- The seal is DB login identity: a caller cannot choose another tenant by
-- issuing SET app.tenant_id. Runtime roles cannot SELECT login_tenants.
DO $rls$
DECLARE name text;
BEGIN
 FOREACH name IN ARRAY ARRAY['accounts','events','private_evidence','consent_reviews','review_tasks'] LOOP
   EXECUTE format('ALTER TABLE meta_stage.%I ENABLE ROW LEVEL SECURITY', name);
   EXECUTE format('ALTER TABLE meta_stage.%I FORCE ROW LEVEL SECURITY', name);
   EXECUTE format(
     'CREATE POLICY tenant_only ON meta_stage.%I USING (tenant_id = meta_stage.session_tenant()) WITH CHECK (tenant_id = meta_stage.session_tenant())',
     name
   );
 END LOOP;
END $rls$;

-- CI harness must provision non-BYPASSRLS restricted LOGIN roles and
-- explicitly GRANT minimal permissions; there is no live role bootstrap here.
REVOKE ALL ON ALL TABLES IN SCHEMA meta_stage FROM PUBLIC;
