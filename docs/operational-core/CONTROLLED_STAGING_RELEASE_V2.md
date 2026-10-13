# Operational Core — controlled private staging and release plan

**Reviewed:** 13 October 2026. **Status:** development schema ready; private staging and customer release NOT authorized.

This consolidates older PRs #12 and #13, which predate owner-approved migration 011 and PRs #15/#16. Never reintroduce their older migration script or outdated pre-migration claims.

## Completed with evidence

- PR #11 delivered deterministic assessment code.
- PR #15 merged guarded local backup, disposable restore rehearsal and migration safety.
- The owner confirmed that the existing Kali development PostgreSQL was backed up, restored to a temporary database, upgraded to migration 011, and retained organization/objective/audit counts. The assistant did not access Kali.
- The owner reported successful forced RLS, tenant assessment policy, restricted runtime grants and immutable assessment triggers.
- The owner's local /health and /ready both returned success and API was on 127.0.0.1:8000.
- PR #16 installed a read-only local gate and automated CI evidence; CI validates functional assessment, identity, Chromium browser acceptance and disposable recovery.
- No private cloud deployment, customer authentication, actual financial outcome proof, or autonomous AI actions resulted from these local milestones.

## Gate R0 — source and release controls

Before a merge, review exact PR SHA, current successful CI, change scope and live Render settings. The static-only Render marketing site retains Auto-Deploy and PR Previews Off. Preserve manual owner deployment approval.

**GitHub required-check enforcement is not enabled:** private main remains unprotected. An eligible plan may be required. CI cannot enforce merge restrictions by itself; use an explicit human hold until Release Evidence Gate is required by an active branch protection rule. Never make this repository public to bypass the restriction.

## Gate R1 — local development database

Completed on the owner's Kali after express authorization. Retain protected backup outside the repository; never upload dumps, keys or .env. Production disaster recovery and separate PostgreSQL cluster globals have NOT been validated.

Never replay migration 011. The workspace initialization command rotates existing credentials; it is not a recovery procedure.

## Gate R2 — secure private staging (NO-GO)

Before provisioning staging:

1. Select an explicitly approved commercial-use hosting plan, cost ceiling, region and provider.
2. Provision separate synthetic-record database with restricted runtime identity, RLS, protected off-host backups and recovery proof; no public database port.
3. Use a real authenticated private network/Zero Trust edge. An unlisted public URL is not private.
4. Implement and verify OIDC with PKCE, allowlisted HTTPS callbacks, issuer/audience/nonce checks, administrator MFA, cookie/CSRF/session revocation and tenant authorization.
5. Manage secrets separately, enforce trusted hosts, rate limits, audit/alerts, cost ceilings, monitoring and incident rollback.
6. Run independent two-tenant and role-denial tests in staging. Obtain a new explicit deployment approval.

PR #6 has a migration number collision with installed assessment migration 011 and an earlier Tailscale Personal/VM approach that must not be assumed appropriate for commercial hosting. Rewrite and retest before merging OIDC/cloud code. Do not put local developer-key login on the public internet.

## Gate R3 — production/customer security (NO-GO)

Check OWNER/ADMIN/OPERATOR/VIEWER permissions against actual identity providers; tenant-isolated reporting, no privilege escalation, logout/revocation, rate limits, operational audit and recovery. External customer rollout requires explicit, separate owner approval. CALCULATION_VERIFIED reflects internal arithmetic, not real-world financial improvement.

## Gate R4 — AMBOY milestones

- M0: draft architecture/contracts and distinct MetaAutomate/OneCall identity.
- M1: authenticated tenant/product gateway, quotas, deterministic no-model test requests.
- M2: model gateway with privacy, bounded costs and verified information.
- M3: MetaAutomate read-only objectives assistance.
- M4: OneCall service discovery and proposals only; its own backend confirms a booking.
- M5: separately authorized execution, idempotency and independently verified results.

Do not activate AI actions, simulate ad interactions, invent bookings, change customers, or trigger billing by merging design contracts.

## Stop conditions

Halt when wrong DB/organization, missing backup, failed RLS or tenant isolation, missing MFA/identity checks, unexpected public service, failed CI, unapproved cost, Render setting drift, or unreviewed head SHA. Preserve evidence and obtain separate owner approval for every migration, deployment, credential change or opening customer access.
