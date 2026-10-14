# P2-02d — Loopback mutual TLS and bound OneCall proof verification

**Status: source-only engineering evidence. There is NO independently approved live private staging environment.** Foundation remains NO-GO at 3/9.

## Prerequisites

- OneCall draft PR #3 is the authentication baseline, draft PR #4 adds the backend-only Ed25519 OneCall identity assertion, and draft PR #5 adds a different Ed25519-signed service proof bound to the exact assertion bytes. These are not deployed or approved as live trust sources.
- MetaAutomate P2-02a and P2-02b add a source-only verifier and disposable JTI replay ledger. MetaAutomate draft PR #26 contains the default-deny peer policy; this P2-02d PR is **stacked on #26**, not independently mergeable to production until the base is reviewed.
- No user or organization mapping is authorized by a signed service assertion or an authenticated TLS connection.

## Implemented and tested now

1. `onecall_mtls_adapter.py` extracts the DER peer certificate directly from an actual connected **server-side** Python `ssl.SSLSocket`, with `CERT_REQUIRED`, a TLS 1.3 handshake and an operator-configured trust store. The X.509 parser independently checks the exact OneCall URI SAN, non-CA leaf certificate, `clientAuth` extended key usage, validity window, and pin against the disabled-by-default P2-02c service policy.
2. `test_onecall_mtls_handshake.py` generates a disposable ECDSA CA and server/client leaf certificates on local pytest temporary storage, then performs actual encrypted handshakes over `127.0.0.1`. Negative cases reject missing client certificates, untrusted issuers, expired certificates, incorrect service URI, disabled operator policy and pin mismatches.
3. `onecall_service_proof.py` independently validates the exact OneCall PR #5 Ed25519 M2M proof format, audience, URI/method binding, 30-second lifetime, separate public-key pin, onecall-only scope and SHA-256 digest of a separately validated, short-lived OneCall identity assertion. Negative tests reject tampering, swapped assertions, wrong signing keys, spoofed tenant/operation claims, unsigned/mobile tokens and expired proofs.
4. Both verifiers remain **disconnected from all HTTP routes** and cannot create a MetaAutomate session, map a OneCall tenant, access records, book services, move money or execute models.
5. CI exercises this cryptography on disposable machines and continues the existing assessment, AMBOY, tenant, Chromium, PostgreSQL recovery and release gates.

## Critical limitations

A passing TLS handshake in GitHub CI is not a private network, real hostname, certificate authority, authorized staging provider, customer consent or production trust. The new adapter verifies actual OpenSSL trust context and X.509 service identity, but does NOT provision a certificate issuer, rotate keys, enforce egress routes, authenticate a real OneCall deployment, verify its current account/session status, grant/restrict service privileges, or establish an independent staging backup.

The M2M proof verifier does not consume the service proof JTI, validate a live OneCall tokenVersion via an authenticated channel, check operator-provisioned issuer keys or independently authenticate the TLS transport. Its returned object is a **cryptographic test receipt, not an authorization grant**. P2-02b's durable JTI ledger has no runtime grant and migrations 012–014 are not applied on Kali.

## GO / NO-GO for the eventual P2-02d live integration

- F04 required GitHub checks enforced and reviewed; F05 approved private staging provider, region and budget; F06 real OIDC/MFA and private ingress; F07 real off-host staging restore; F08 external tenant/security review; F09 customer pilot only later.
- Deploy real mutual TLS with dedicated restricted CA, correct server and OneCall peer leaf certificate identity, certificate lifetime/rotation/revocation, and no client-supplied forwarded-certificate headers. Integrate the TLS adapter only at a thoroughly reviewed private authenticated endpoint; do not accept an arbitrary `VerifiedTlsPeerEvidence` constructor as proof.
- Receive backend-only dedicated OneCall assertion and bound service proof over that channel, verify both distinct Ed25519 signatures/issuers/keys, actual OneCall account/token-version freshness, **both** identity and service proof JTI one-time consumption, persistent denial auditing, quotas and service outage fail-closed behavior.
- Independently verify OneCall resource ownership and OneCall-specific tenant membership; never infer authorization from matching emails, app user IDs or signed proof alone.
- Carry out a real end-to-end security test across separately running OneCall and MetaAutomate staging services with revoked identities, replay, cross-tenant attempts, certificate rotation and network failure.
- Obtain explicit owner security/release approval for hosting, changes, credentials and customer access. Do not deploy on the strength of this PR's CI.

**No DigitalOcean provisioning, Kali migration, Render update, live OneCall connection, OneCall PR merging, or customer access is authorized by this change.**

The CI handshakes use temporary files for short-lived synthetic keys, never any customer or deployed private key. The PR targets `main` to run the full required workflow and supersedes the standalone, synthetic-only peer policy PR #26 if the complete security review accepts the consolidated source.
