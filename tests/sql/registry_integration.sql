-- Run AFTER 001..008 migrations AND CSV seed against an isolated development database.
-- Nothing is permanently inserted: the outer transaction rolls back all fixtures.
\set ON_ERROR_STOP on
BEGIN;

DO $$
BEGIN
  IF (SELECT count(*) FROM capability_definitions) <> 33 THEN
    RAISE EXCEPTION 'Expected 33 seeded capability definitions';
  END IF;
  IF (SELECT count(*) FROM capability_versions WHERE version = '0.1.0' AND contract IS NULL) <> 33 THEN
    RAISE EXCEPTION 'Expected 33 non-executable draft versions';
  END IF;
  IF EXISTS (SELECT 1 FROM capability_definitions WHERE is_enabled OR lifecycle_status <> 'DRAFT') THEN
    RAISE EXCEPTION 'Draft capabilities were accidentally activated';
  END IF;
  RAISE NOTICE 'PASSED: 33 draft entries and version placeholders';
END;
$$;

INSERT INTO organizations(id, slug, name)
VALUES
('11111111-1111-4111-8111-111111111111', 'registry-org-a', 'Registry Organization A'),
('22222222-2222-4222-8222-222222222222', 'registry-org-b', 'Registry Organization B');

SET LOCAL app.organization_id = '11111111-1111-4111-8111-111111111111';
INSERT INTO organization_capabilities(organization_id, capability_id)
VALUES ('11111111-1111-4111-8111-111111111111', 'CORE-001');
INSERT INTO capability_executions
(organization_id, capability_id, version, idempotency_key, request_hash)
VALUES
('11111111-1111-4111-8111-111111111111', 'CORE-001', '0.1.0', 'test-a', 'hash-a');

SET LOCAL app.organization_id = '22222222-2222-4222-8222-222222222222';
INSERT INTO organization_capabilities(organization_id, capability_id)
VALUES ('22222222-2222-4222-8222-222222222222', 'CORE-002');
INSERT INTO capability_executions
(organization_id, capability_id, version, idempotency_key, request_hash)
VALUES
('22222222-2222-4222-8222-222222222222', 'CORE-002', '0.1.0', 'test-b', 'hash-b');

CREATE ROLE registry_validation_reader NOLOGIN;
GRANT USAGE ON SCHEMA public, app TO registry_validation_reader;
GRANT SELECT ON organization_capabilities, capability_executions TO registry_validation_reader;
SET ROLE registry_validation_reader;

SET LOCAL app.organization_id = '11111111-1111-4111-8111-111111111111';
DO $$
BEGIN
  IF (SELECT count(*) FROM organization_capabilities) <> 1
     OR (SELECT count(*) FROM capability_executions) <> 1
     OR NOT EXISTS (SELECT 1 FROM organization_capabilities WHERE capability_id='CORE-001')
  THEN RAISE EXCEPTION 'FAILED: org A registry RLS'; END IF;
  RAISE NOTICE 'PASSED: org A registry RLS';
END;
$$;
SET LOCAL app.organization_id = '22222222-2222-4222-8222-222222222222';
DO $$
BEGIN
  IF (SELECT count(*) FROM organization_capabilities) <> 1
     OR (SELECT count(*) FROM capability_executions) <> 1
     OR NOT EXISTS (SELECT 1 FROM organization_capabilities WHERE capability_id='CORE-002')
  THEN RAISE EXCEPTION 'FAILED: org B registry RLS'; END IF;
  RAISE NOTICE 'PASSED: org B registry RLS';
END;
$$;
RESET ROLE;
ROLLBACK;
