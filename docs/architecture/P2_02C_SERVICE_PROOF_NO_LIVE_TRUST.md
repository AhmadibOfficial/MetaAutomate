# P2-02c — Independent backend-to-backend proof contract (NO LIVE TRUST)

**Status:** Offline, source-only M2M cryptographic verification. No customer traffic, HTTP route, networking, IAM principal, OneCall tenancy or AMBOY permission is enabled.

This work is paired with OneCall's source-only service-proof signing branch stacked on its draft issuer PR #4 and auth PR #3.

## Two independent credentials and keys

1. **OneCall identity assertion** (P2-02b): short-lived Ed25519 JWS scoped to the signed-in OneCall UUID for `amboy:identity-test`; subject status and token version checked by the authoritative OneCall issuer.
2. **OneCall service proof** (this stage): different Ed25519 signing key with ID prefix `oc-m2m-`, dedicated `typ=onecall-amboy-service-proof+jwt`, `aud=metaautomate-amboy-m2m-test`, `sub=onecall-backend`, `scope=amboy:service-identity-test`, method `POST`, path `/internal/amboy/identity-test`, unique UUIDv4 JTI, maximum 30 seconds, and `ath` equal to unpadded base64url(SHA-256(exact ASCII assertion token)). No email, tenant, booking, credit, customer role or authority flags in the proof.

MetaAutomate's `onecall_m2m_proof.py` validates the proof's own signature with an **out-of-band pinned service public key**. It refuses any overlap with the pinned identity public keys, unsigned and HS256 tokens, attacker-supplied `jwk/jku`, wrong method/operation/audience/scope, overly long lifetimes, and proof/assertion byte mismatches.

Passing proof signature checks only indicates that a private key signed a specific identity-test request. It does **not** prove a private network peer, authenticated machine, consent, fresh OneCall account status, or organization membership.

## Atomic test-only pair redemption

Migration 015 creates an append-only proof-ID redemption table and a replay audit table. The owner-only `app.consume_onecall_m2m_identity_test_pair` function inserts the proof JTI and assertion JTI in a single PL/pgSQL subtransaction. Unique conflicts on either ID roll back both inserts, while a replay event is recorded. GitHub's disposable PostgreSQL tests use eight simultaneous calls and prove exactly one first use and seven replays; runtime roles have no SELECT/EXECUTE grant.

**Do not expose this SQL function to a client or service**: PostgreSQL cannot verify either JWS signature and the function deliberately has no runtime grant. Source review/CI is not an approved authentication mechanism.

## Remaining live integration blockers

- Approve private staging host/network, enforce default-deny ingress and mTLS or equivalent authenticated service identity, and pin separate issuer and service public keys (including rotation, revocation, and compromise procedures).
- OneCall auth PR #3, identity issuer PR #4, and service proof branch must be jointly security reviewed before a backend-only transport/issuance endpoint is considered. No Flutter access to signing keys.
- Independently authenticate the service peer; verify both cryptographic tokens and their binding, real OneCall account/session revocation, and one-time pairing in the **same** trusted transaction with audit, quotas and bounded retention.
- Define an authoritative OneCall organization/resource model and explicit product mapping; neither matching email nor claimed client tenant IDs authorizes anything. Pending-only mappings stay denied.
- Prove fail-closed behavior on expired/compromised keys, cross-tenant attempts, service outage, replay, wrong endpoint, server clock skew and concurrency, plus real end-to-end staging restore and security acceptance.
- No OneCall bookings, payments, MetaAutomate workspaces, model calls, agent actions or customer access.

## Release boundaries

All source migrations 012–015 are CI-only and **not approved on Kali**. Foundation remains 3/9 with outstanding branch protection, cloud staging, live OIDC/MFA, backup restore, security acceptance and real pilot. Render Auto-Deploy/Previews remain off. Neither merge nor test success is operational release authorization.
