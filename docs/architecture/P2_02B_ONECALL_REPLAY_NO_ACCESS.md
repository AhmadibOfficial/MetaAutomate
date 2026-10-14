# P2-02b — OneCall identity handoff: offline replay, revocation and mapping NO-GO

**Status:** source-only; NOT a live OneCall-to-AMBOY integration. P2-02a offline signature verifier is already merged.

## Two linked but independent source changes

- **OneCall stacked draft PR #4**, based on its still-draft authentication PR #3: backend-only Ed25519 assertion issuer with independent key, 60-second lifetime, audience `metaautomate-amboy-identity-test`, and freshly checked active/verified user and token version. There is no HTTP endpoint or NestJS DI registration.
- **This MetaAutomate PR**: source-only identity test gate requiring a cryptographically verified assertion, authoritative OneCall account/revocation callback, and one-time atomic replay callback. It does not create a MetaAutomate workspace principal, organization membership, cookie, AI permission or service route.

## Durable one-time replay proof

Migration `014_onecall_identity_test_replay.sql` adds:
- A unique `assertion_jti` ledger, with product `onecall`, purpose `identity_test_only`, token version and expiry.
- Append-only `FIRST_USE` and `REPLAY` audit events (metadata only, never mobile JWTs or raw messages).
- `app.consume_onecall_identity_test_jti` to atomically insert-on-conflict and record the outcome for the first consumer and concurrent replays.
- A separate *pending-only* `onecall_tenant_mapping_reviews` table with no active/bound state and **no runtime grants**. No OneCall customer receives a MetaAutomate tenant mapping from this source.
- No grants on the JTI function to the runtime role. The database design is intentionally unusable as a live customer authorization mechanism until independent review authorizes new grants and network controls.

GitHub CI applies migration 014 to **disposable** PostgreSQL and verifies eight simultaneous attempts at the same JTI admit exactly one first use and audit seven replays. The test also verifies immutable event evidence, no direct runtime SELECT and no runtime EXECUTE on the consumption function.

## Revocation is required separately from JWS verification

The Python `evaluate_identity_test_no_access` requires a caller-supplied *current OneCall account lookup* and a durable *consume-once callback*, checks subject, token version, account active/verified status, and refuses missing/revoked/stale identities before JTI consumption. This is an isolated unit-tested interface, NOT a trusted network attestation: the real OneCall backend must provide an authenticated, fresh, audited revocation protocol before the module can be connected.

An untrusted client cannot supply a tenant, product scope, organization or revocation approval and obtain permissions: **there is no live API route** and the returned receipt is explicitly `IDENTITY_TEST_ONLY_NO_ACCESS`.

## Mandatory P2-02c integration gates

1. Complete OneCall's separate authentication PR #3 review and baseline verification. Its `develop` branch lacks the new auth module.
2. Approve an authenticated private machine-to-machine channel and a dedicated restricted internal issuer route, never exposed to mobile clients, with issuance audits/rate limits and key rotation.
3. Add independently verified OneCall account-status, session/token-version revocation and signing-key lifecycle to the MetaAutomate consumer. A plain caller-provided current-account callback is insufficient.
4. Bind no OneCall tenant until OneCall's authoritative resource ownership/tenant model and administrator-approved product mapping policy can be verified. Matching email, a client-supplied UUID or successful JWS verification do not constitute tenant authorization.
5. Establish independently tested product/tenant scopes, quotas, denial audits, service outage fail-closed handling and JTI retention/expiry cleanup.
6. Approve isolated private staging, OIDC/MFA, secrets, off-host restore, owner release gate and end-to-end negative security tests before any real customer usage.
7. Keep bookings, payments, wallet operations, advertisements, AI/model calls and all autonomous execution OFF until separately approved.

## Release constraints

- Phase 01 remains **3/9 verified, NO-GO**; GitHub private main branch status checks remain unenforced.
- Migrations 012–014 **must not** be applied to the Kali development database without a separately approved backup and change request.
- Do not deploy OneCall, MetaAutomate, DigitalOcean or Render; do not change credentials or DNS; do not enable customer sessions.
- **Merge into main means source evidence and tests only, not authorization to integrate identities.**
