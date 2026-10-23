# P2-061 — Secure Business Data Workspace

STATUS: SOURCE-ONLY, AUTHENTICATED LOCAL REHEARSAL. OPERATIONAL NO-GO.
This branch builds on P2-060 (draft PR #119); its parent must pass review first.

## Scope

A bounded, real AES-256-GCM encrypted SQLite inventory lab, with a
loopback-only FastAPI adapter using the EXISTING PostgreSQL-authenticated
workspace identity and session/CSRF controls.

- Inventory CSV: exact header sku,name,stock,weekly_sales,unit_price_kobo
- Limit: 64 KiB, 200 rows per file, 25 active documents per tenant.
- Stock and sales: integer 0–1000000. Price: positive integer kobo.
- Product names and SKUs reject basic control/formula/HTML injection.
- Explicit data-owner declaration on import. This is a SELF CLAIM, not proof.
- Tenant and user UUIDs come exclusively from app.authn verified principal.
- OWNER/ADMIN can import and delete; OPERATOR can read; VIEWER denied.
- Tenant-derived AESGCM encryption keys via HKDF from a 32-byte external secret.
- Per-document random 12-byte nonces, tenant and document-bound AAD.
- Reads, imports, deletes and purges carry local tenant HMAC chain evidence.
- Retention 1–30 days. Expired records cannot be read. An authorized manual
  purge is needed for physical removal, no automatic retention scheduler.
- Delete is limited to the active SQLite row; backups/snapshots are not erased.
- The existing private Objective Workspace now includes a locally gated
  Inventory vault screen. The navigation remains hidden by default and becomes
  available only if the server advertises the development-only flag. The screen
  supports authenticated CSV import, document listing, on-demand decrypt/view,
  explicit deletion and expired-record purge, local HMAC verification, and
  immediate clearing of decrypted on-screen previews on navigation/logout.
  This interface is served by the private API app, NOT the public apps/site page.
- Independent source/consent verification, KMS, key rotation, and PostgreSQL
  forced RLS remain future acceptance gates.

The workbench does not include a live public app, customer accounts, media
inference, social publication, analytics connectors or real production storage.
It does not change any existing Postgres schema or Render service.

## Local operator requirements

Only an explicitly approved, separate local development workspace is supported.
Do not copy customer personal data, secrets or confidential vendor information
into this test service. Prefer fabricated inventory fixtures.

The API is disabled unless every condition is satisfied:

    MAT_DATA_LAB_ENABLED=1
    MAT_DATA_LAB_ACK=LOCAL_REHEARSAL_ONLY
    WORKSPACE_AUTH_MODE=dev_key
    WORKSPACE_ORIGIN=http://127.0.0.1:8000
    MAT_DATA_LAB_SQLITE=/absolute/path/outside/repo/inventory.sqlite3
    MAT_DATA_LAB_KEY_B64=<base64 of 32 strong random bytes>

The path's parent must exist, not be a symlink. The new DB is mode 0600.
Never store the key in Git, terminal history, shared screenshots or log files.
Losing a non-persisted ephemeral key makes data unrecoverable: proper external
key custody, encrypted backups and rotation are required before actual service.

Requests require the existing authenticated MetaAutomate workspace bearer
token OR session cookies with trusted Origin and X-CSRF-Token for mutations.
The adapter checks remote loopback address and exact local Host.
Caller-supplied tenant headers are always rejected.

## Endpoints

- POST /v1/data-lab/inventory?retention_days=7: UTF-8 CSV, Content-Type
  text/csv, X-Inventory-Data-Claim with exact value
  OWNER_AUTHORIZED_INVENTORY_NO_PERSONAL_DATA.
- GET /v1/data-lab/inventory: list unexpired document metadata for tenant.
- GET /v1/data-lab/inventory/{UUID}: decrypt same-tenant inventory, audit read.
- DELETE /v1/data-lab/inventory/{UUID}: delete active record and append tombstone.
- POST /v1/data-lab/inventory/purge-expired: authorized per-tenant manual purge.
- GET /v1/data-lab/audit: verify local HMAC chain, NOT external anchoring.

The existing API authentication is NOT reproduced by the unit tests; those
tests use typed fictional principals to test authorization/tenant mechanics.

## Tests

    python3 -m pytest -q tests/test_p2_061_secure_data_lab.py tests/test_p2_061_data_api_admission.py tests/test_p2_061_private_vault_ui.py
    python3 -m compileall -q apps/api/app/secure_inventory_lab.py apps/api/app/secure_data_lab_api.py

The tests cover different tenant IDs, denied read/delete, ciphertext
tampering and substitution, invalid root keys, audit manipulation, wrong roles,
expired/inaccessible records, explicit purge, bounded quotas, injection-prone
CSV input, missing authorization claim, disabled-by-default API, nonloopback
clients, forged tenant headers, and OIDC/private-production mode denial.

These local results do not count as a security audit, independently
authenticated business-data source, verified customer consent or accepted
production onboarding.

## Remaining release gates

Real customer deployment requires real OIDC/MFA and tenant membership review,
PostgreSQL 16 forced RLS and independent two-tenant acceptance, managed key
storage/versioned rotation and restore rehearsals, consent/data rights,
background retention enforcement, external immutable audit head anchoring,
private network topology and independent penetration testing.

P2-060, P2-061 and the platform's 3/9 foundation status remain operational
NO-GO. No subscriptions, live integrations, automated AI, production database
migration, merge, cloud build or deployment have been performed here.


## P2-061 local validation while hosted GitHub Actions is billing-blocked

The owner's check-run annotation on 2026-10-23 explicitly says:

    The job was not started because recent account payments have failed
    or your spending limit needs to be increased.

This indicates the GitHub Actions job did not begin. It does not establish
that the code or tests failed, and it MUST NOT be converted into a green
GitHub status in source code or by a substitute workflow. The unrelated
Ubuntu runner-image migration announcement is only a notice, not proof
that Ubuntu 26 caused the failure.

A read-only developer-owned local validation runner is available:

    cd ~/MetaAutomate
    git status --short --branch
    python3 scripts/verify_p2_061_offline.py

Optional evidence output to a **new path outside the repository**:

    python3 scripts/verify_p2_061_offline.py \
      --report "$HOME/p2-061-source-evidence.json"

Do not overwrite existing evidence or include private customer records.
The command will refuse dirty worktrees and missing required files, compile
Python source entirely in memory, run isolated pytest and Node tests and
JavaScript syntax checks, compare git status before/after, and output a JSON
report with commit fingerprint. Source tests run with browser/infrastructure
activation flags set to OFF. It never installs packages, creates cloud
resources, merges PRs, deploys, changes billing, or touches databases outside
test-created disposable fixtures.

A passing report is explicitly marked LOCAL_TESTS_PASS with
github_ci_verified=false, merge_approved=false and deployment_approved=false.
Real authenticated browser/API integration and independent hosted CI must
still run after repository billing/runners are restored. Protect the recorded
evidence path; it is local source test evidence, not an external attestation.

The development queue is:
1. Resolve P2-060's independent browser/CI acceptance.
2. Complete P2-061's local encrypted-lab source/API/browser acceptance.
3. Have the GitHub account owner repair Actions billing/spending-limit
   configuration; do not create a workaround to fake checks.
4. Obtain independent reviewer approval, then separately authorize any
   merge or private staging deployment.
5. Only after source gates, design production RLS/KMS/retention revisions
   as a distinct milestone, keeping customer data disabled.

No nightly validation timer or GitHub Actions runner has been installed on
the owner's Kali machine by this repository change.
