# P2-03t — Application Tenant Authorization, Durable Audit & Source Data Quality

**Status:** SOURCE-ONLY / DISPOSABLE CI REHEARSAL / OPERATIONAL NO-GO. This PR stacks on draft P2-03s (#81). The new branch must not be merged to `main` separately from its unmerged base.

## Product objective

A MetaAutomate lead/CRM operation should be considered only when *both* authenticated application authorization **and** authenticated database tenant ownership match, the inbound metadata has passed official-message-shaped signature inspection and strict data quality checks, and the operation has an auditable review purpose. Keep all real records and outbound automation disabled.

## Actual engineering changes

1. **Signed application actor/role contract.** `disposable_crm_authorization.py` validates canonical, bounded **Ed25519** test tokens before parsing claims. Pinned verification public key, exact issuer/audience/version and workspace, actor reference, role, short maximum lifetime and reject-on-unknown fields. Roles:
   - `auditor` can read permitted queues and audit integrity.
   - `reviewer` can read and assign fictional human-review tasks but cannot ingest, consent-review or access protected evidence.
   - `tenant_admin` can ingest validated synthetic events, inspect queues/audits, review synthetic consent and access encrypted fictional notes.

   The `AuthorizedMetaCRM` facade applies these checks on **each operation** and independently validates the real PostgreSQL authenticated `session_user` -> protected tenant mapping. A token claiming one workspace cannot operate using another tenant's database login. Arbitrary `app.tenant_id` values have no effect. This is a **working source-only authorization component**, not a deployed login service, identity provider, production user directory, real customer authentication or full staff role-assignment system.

2. **Trusted event inspection and source quality.** Ingest takes raw fictional Meta-shaped bytes, X-Hub-Signature-256 and an **ephemeral test secret**. It revalidates signature through existing P2-03r inspection (not a caller-supplied `signature_check` flag), then verifies digest equality, tenant-binding via trusted provider-account registry, exact event schema/kind/form reference, batch cardinality, synthetic-only IDs, duplicate IDs, PII rejection and absence of false consent/provider-send assertions. Failed results receive deterministic **QUARANTINE** reason codes, with no customer data retained. No external provider origin, event freshness, customer permission or marketing consent is verified, so `production_ready` always remains false.

3. **Durable tenant-specific audit chain.** Disposable SQL extension `database/disposable/p2_03t_meta_audit.sql` installs PostgreSQL triggers for inserts to synthetic accounts/events/consent/evidence/tasks and task updates, in the *same transaction* as protected data changes. Each commit appends a tenant-serialized SHA-256 chain with login identity and minimal non-PII metadata. Runtime roles can SELECT only their own tenant's history and cannot INSERT, UPDATE, DELETE or TRUNCATE it. `disposable_audit_verification.py` checks ordered sequence continuity, hashes, and optional separately retained head digest.

   **Limits:** DB superusers and backup operators are not tamper-proofed; a hash chain with no external immutable anchor cannot by itself detect a privileged attacker rewriting an entire chain. Production requires independent immutable/worm audit storage, authenticated actor identity binding, operational anomaly detection and alerting.

4. **Disposable backup and restore drill.** The CI tests create only fictional data in `meta_stage_ci`, generate a custom-format PostgreSQL archive in memory, restore to separately named `meta_stage_restore_ci`, and verify both tenant RLS boundaries, encrypted sample-evidence decryption and exact previously captured audit-chain heads. The archive is never uploaded. This tests **correctness of the disposable recovery path**, not operational RPO/RTO, encrypted backup lifecycle, real customer disaster recovery or production rollback.

5. **Business continuity value.** Enables trustworthy future source lineage, accountable human review, ability to measure data quality and a recoverable audit foundation for the P2-03s expense/continuity engine. No new profit claim, predictive AI, automated redundancy trigger, operational saving, active 90-day customer pilot or live integration has been established.

## Verification

`.github/workflows/p2-03t-authz-audit.yml` runs (i) pure Ed25519 authorization and source-quality tests, (ii) signed-Meta federation regressions, (iii) PostgreSQL 16 disposable tenant auth/RLS/idempotency/encryption/audit tests and custom-format recovery, and (iv) continuity-model regressions.

Commands:

```
python -m pytest -q tests/test_disposable_crm_auth_quality.py
python -m pytest -q tests/test_disposable_meta_crm_postgres.py
python -m pytest -q tests/test_synthetic_business_resilience.py
```

Database tests execute **only** with `GITHUB_ACTIONS=true`, `META_CRM_STAGING_DISPOSABLE=yes`, `META_CRM_DATABASE_NAME=meta_stage_ci`, plus an explicitly configured disposable PostgreSQL 16 service. Nothing is provisioned in DigitalOcean or Render.

## Before real or authorized customer data

Independent security review, approved private staging topology and cost ceiling; first-party user authentication (OIDC/MFA), trusted signing key lifecycle and rotation; real tenant memberships and role provisioning, short-lived sessions with revocation; verified Meta Page/IG/WABA ownership and approved scopes; signature/replay/freshness checks; durable consent receipts and opt-outs, retention/deletion/subject rights, external immutable audit anchoring, operational encrypted backup and RPO/RTO drills; human inbox access controls; monitoring, quotas and emergency shutdown. Production schema migration and activation require a **separate authorization** after all Phase 01, 02 and 03 gates. Existing Phase 01 remains 3/9 verified.

**No subscriptions, ad spend, hosting changes, real contacts, live messages, public endpoint, production migrations or deployment.**
