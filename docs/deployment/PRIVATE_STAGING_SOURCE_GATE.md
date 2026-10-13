# MetaAutomate Private Staging — source readiness gate (v1)

Status: **SOURCE CANDIDATE ONLY**. No staging VM, database, HTTPS edge, SSO provider or account has been provisioned. This document and the code do not authorize a deployment or local migration.

## What the template establishes

The unactivated Compose template at deploy/staging/compose.yaml is explicitly separate from the Kali development Compose project and uses a different project name, PostgreSQL DB and named volume. PostgreSQL has no published ports and runs only on an internal DB network. The production-mode API has a read-only root filesystem, a nonroot user, dropped capabilities and a loopback-only host port. It requires OIDC-only mode, secure cookies, a restricted database URL and external secret inputs.

Both services belong to an opt-in Compose profile. A normal Compose invocation without that profile does not launch staging. This is accidental-start protection, not an authorization system.

The API has an outbound-capable network solely because real OIDC verification requires issuer and token exchange; this is not a deployed authenticated inbound edge. There is **no public ingress** or routing configuration in this PR.

## Automated source gate

On a reviewed checkout, with PyYAML available:

    python3 scripts/verify_private_staging_contract.py

The script statically rejects unsafe ports, unexpected services, dev-key authentication, embedded passwords, privilege expansion, local database reuse, extra bind mounts and missing manual-profile controls. It writes a machine-readable JSON report under the ignored .buildlog directory and never executes Docker, reads .env or contacts the network.

GitHub Actions runs the static gate plus negative tests and uploads its JSON evidence as a separate artifact. Its result is fed into the existing Release Evidence Gate through the functional CI prerequisite.

**SOURCE_PASS means the manifest satisfies reviewed source constraints only.** It does not mean that a private staging environment exists or that it is safe for production.

## Owner approval needed BEFORE deployment

1. Choose a commercially permitted provider and region; approve a monthly cost ceiling and resource limits.
2. Verify an actual private ingress: authenticated proxy/Zero Trust or private network, TLS, hostname ownership and no exposed database.
3. Select a real OIDC identity provider and client; enable MFA for privileged members, PKCE, issuer/audience/nonce/JWKS checks and constrained callback URLs. Prove actual provider behavior in a controlled test.
4. Prepare staging-only admin and runtime credentials, secret storage, immutable artifacts, restricted Docker access and no copy of the local development database.
5. Create a fresh isolated staging database with migrations 001–012, provision a separate restricted runtime role and OIDC tenant identities through an independently reviewed administrative path. The main Kali database has only migrations through 011; migration 012 is **not** approved for that database.
6. Verify encrypted off-host backups, independent full restore, observability, rate limits, audit logs, rollback and two-tenant negative tests using synthetic records.
7. Confirm release approval, exact reviewed git commit, private access list and a time-bounded change window. Keep Render's public marketing site and legacy service unchanged, with Auto-Deploy and PR Previews Off.

The current source template cannot satisfy all seven gates without external decisions and a separate provisioning workflow. **Do not run the profile on a production host yet.**

## AMBOY M1 follows staging acceptance

Build a separately authenticated product-and-tenant gateway: identity verified server-side for MetaAutomate and OneCall, least-privilege scopes, quotas per product and tenant, idempotency, request correlation, denial audits, and no-model deterministic responses. AMBOY must not share OneCall bookings or MetaAutomate records across products, accept client-provided tenant authority, execute actions, or initiate artificial ad events. Live AI inference and authorized actions remain later milestones.

## Explicit release boundary

A merged staging template is **not** a license to apply migration 012, provision a VM, install an IdP, pay for hosting, change DNS, enable a cloud API, open customer access or activate AMBOY. Each requires separate authorization and live-environment evidence.
