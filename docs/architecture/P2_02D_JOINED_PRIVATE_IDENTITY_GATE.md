# P2-02d — Joined identity, service proof and private transport test

**Status:** source-only; NOT a live OneCall-to-MetaAutomate federation. Foundation: **NO-GO, 3/9**.

## What is now covered together

An isolated no-access admission function, `apps/api/app/onecall_joined_identity_test.py`, enforces this sequence:

1. Real Python TLS 1.3 **server-side SSLSocket**, exact operator-pinned OneCall URI SAN, client-auth certificate chain and validity checks, never a copied HTTP header or caller-supplied "verified" boolean.
2. Two **distinct Ed25519** signed OneCall credentials: a short-lived identity assertion and a separately signed backend service proof; the latter cryptographically binds the former's exact bytes and the restricted POST identity-test path.
3. Fresh OneCall identity lookup *interface*, checking the verified subject, current tokenVersion, ACTIVE account, verified email/phone, and failure on revocation/outage.
4. **One atomic dual-JTI redemption interface**, already implemented in source migration 015 and tested in disposable CI against PostgreSQL 16; both assertion and proof JTIs must be consumed once together.
5. Return only `IDENTITY_TEST_ONLY_NO_ACCESS` with no MetaAutomate workspace principal, tenant mapping, booking, payment, autonomous tool or model permission.

The regression test `tests/test_onecall_mtls_handshake.py` verifies this joint sequence over a genuine loopback TLS handshake with fresh temporary ECDSA CA and certificates and freshly generated synthetic Ed25519 service/identity signing keys. Negative scenarios: revoked/blocked account, version mismatch, provider outage, replay, DB callback outage, untrusted/expired/wrong-SAN/no client cert, and disabled peer policy. Browser, Objective Workspace, AMBOY and disposable PostgreSQL recovery CI continue to run.

The independent single-credential signature-verification tests and eight-concurrent-attempt dual-JTI database test remain in the main CI workflow. No live OneCall customer data is used.

## What a passing test DOES NOT prove

- Neither service is deployed on an authorized private staging network. No external IP, route, private CA, production certificate/key, real OneCall service identity, real OIDC/MFA, or account/budget authorization has been established.
- A function argument named `load_authoritative_onecall_identity` is NOT inherently authoritative. Only a separately reviewed, mutually authenticated backend connection to OneCall with documented freshness, issuer and failure behavior may satisfy that role in production.
- A callback named `consume_pair_once` is NOT inherently safe. Only the separately constrained PostgreSQL transaction/role, source migration 015 after approval, zero replay tolerance, audit retention and incident response may satisfy it.
- Evidence remains ephemeral; live certificate revocation, issuer rotation, dedicated secrets management, network policy, independent external security tests and off-site disaster recovery remain unverified.
- OneCall PRs #3 (auth), #4 (identity issuer) and #5 (M2M issuer) are draft and must not be bypassed by trusting client-provided claims or mobile HS256 tokens.

## Required next operational sequence — no invented completion

1. Owner selects an eligible provider, region and monthly cost ceiling, and authorizes a private isolated staging network. No DigitalOcean, Render or any other service provisioning is implicit.
2. Resolve GitHub private `main` status-check enforcement, set up a real identity provider and MFA, and approve managed private certificate authority/service key lifecycle.
3. Review and merge OneCall authentication/source assertions in their correct dependency order, verifying all current backend/principal/tenant assumptions rather than blindly merging drafts.
4. Build real TLS reverse-proxy/service adapters that establish verifiable peer identity from the TLS handshake itself, not forwarded headers, plus a safe test-only route with zero customer data.
5. Establish independently authenticated OneCall revocation lookups, proper tenant/resource ownership model and product scopes. No email matching or client-supplied UUID privileges.
6. Wire signed-proof verification and restricted dual-JTI consumption only behind a non-public, mutually authenticated test-only ingress; audit first-use, replay and all authorization denials with bounded retention.
7. Run real cross-repository adversarial integration tests on private staging; collect off-host recovery, key rotation, certificate expiry/renewal, tenant isolation, outage and roll-back evidence.
8. Obtain independent security acceptance and explicit owner go/no-go approval before any customer access. Migrations 012–015 stay **unapplied on Kali** unless separately approved.

**Code merge is not deployment authorization.** This PR does not modify public services, Cloud/DigitalOcean billing, GitHub plan, passwords, domain/DNS settings, or customer permissions.
