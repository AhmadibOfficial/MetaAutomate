# P2-02 — OneCall → MetaAutomate / AMBOY independent identity

**Date:** 14 October 2026. **Status:** source-only offline identity verification; **NO live trust**.

## Verified OneCall repository facts

The public `AhmadibOfficial/OneCall` repository has **two different implementation baselines**:

- `develop` (commit `f4ca1b0af79e0fd5896ee76820f3f755998fe096`): starter NestJS `AppModule` with no `AuthModule`, a root hello-world controller and no production login enforcement.
- Open **draft PR #3** `feat/staging-release-preparation-20261013` (head `8f12ead24e0616b1649ce47191ae7a393f4039cf`): substantive NestJS authentication. `AuthModule` signs **HS256 mobile JWTs** with issuer `onecall`, audience `onecall-mobile`, 15 minute access expiry. `JwtStrategy` verifies issuer/audience/algorithm and looks up an active user, checking `tokenVersion`. Refresh tokens use database-backed sessions; additional tests cover registration, lockout, refresh rotation and sensitive-field disclosure. CI's Kaduna pilot verification is green on the PR head.
- PR #3 is **not merged to develop**; its CI success does not prove OneCall is deployed or that its complete auth flow is operational with live users.
- A OneCall customer has an independent OneCall UUID and not automatically a MetaAutomate identity or organization. The presence of identical email addresses proves no product membership, user relationship or authorization.
- The OneCall mobile HS256 secret and bearer token are **strictly unsuitable** for federated AMBOY identity, because they were issued for the mobile application and not for MetaAutomate. NEVER copy or share JWT_SECRET.

## This PR implements (P2-02a)

- A source-only `app.onecall_assertion.validate_onecall_assertion_signature_only` verifier for a **different, future** backend-issued assertion. Requires an out-of-band approved public Ed25519 key, fixed asymmetric EdDSA algorithm, dedicated `typ`, exact `aud`, approved HTTPS `iss`, `onecall` product, explicit `amboy:identity-test` scope, server-side OneCall UUID subject, UUID replay ID, and max 60-second lifetime.
- Rejects mobile HS256 and unsigned tokens; any unrecognized header including `jku` or `jwk`; extra authority, roles or email-based principal claims; unknown `kid`; excessive lifetime; signature forgery; wrong audience/issuer; and malformed JSON.
- All cryptographic unit-test signing keys are created in memory and are not stored in GitHub.
- `contracts/identity/onecall-amboy/v1/assertion.json` publishes the verification contract. No routes, middleware, JWT issuer, network calls, database migrations or external side effects are introduced.

**Important distinction:** A signature-valid claim object is NOT a MetaAutomate principal. Offline signature validation alone proves neither an active OneCall session nor freshness of `tokenVersion`. This module must NOT be attached to a live route or used to grant access until the external conditions below are satisfied.

## Trust architecture before any real connection (P2-02b)

1. OneCall backend checks its own customer authentication, account status and revocation state using its authoritative database. It MUST refuse issuance for blocked/revoked/unverified users according to product policy.
2. OneCall backend (not Flutter) mints a short-lived **asymmetrically signed service-specific assertion**, with a separate issuer and audience `metaautomate-amboy-identity-test`. Signing keys never enter MetaAutomate; public verifying keys are pinned and rotated under explicit operator review.
3. Only a restricted, authenticated private service channel may deliver the assertion to MetaAutomate. This route is not implemented yet.
4. MetaAutomate verifies signature, issuer, audience, expiry, unique `jti`, product/scope and subject claims, then atomically redeems `jti` once in durable, tenant-isolated storage; rejects replay. The offline verifier in this PR **does not provide replay protection**, so it remains unconnected.
5. On each permitted operation, verify the OneCall account/session revocation or a safe bounded revalidation mechanism; assign a distinct OneCall **product principal**. Do not mint MetaAutomate workspace cookies for a OneCall identity.
6. OneCall subject-to-tenant mapping and business authorization must be established by backend rules, not supplied client tenant IDs, matching email, or AI-generated output.
7. Enforce independent quotas and denial audits with no raw request contents or secrets, and maintain a separate lifecycle for OneCall identity keys.
8. Begin with `amboy:identity-test` only. Deny OneCall service listings, bookings, payments, wallets, advertisements, model inference and external actions until separate authorized milestones.

## Threat-model minimums

Fail-closed tests must cover swapped issuer, HS256 confusion, unknown or attacker-provided JWK/JWKS URL, wrong audience, stale `exp`, `nbf` in the future, replayed `jti`, compromised key rotation, revoked account, cross-tenant/user claims, forged consent, product-scope escalation and OneCall backend outage.

Attestations must NEVER be treated as authorization or customer data proof without an independently verified issuer, fresh user/session context and a separate business policy.

## Parallel Foundation boundaries

Foundation remains NO-GO: main required-check protection, live private staging, real OIDC/MFA, independent recovery and end-to-end pilot evidence are not complete. MetaAutomate migrations 012/013 remain unapplied to Kali. Neither OneCall PR #3 nor this P2-02a work authorizes cloud deployment, secret exchange, customer access or model/tool execution.

Next acceptance is a reviewed OneCall **backend-issued dedicated assertion contract and negative tests** on a OneCall branch, then a separate private, audited test handshake. There is no default trust link between repositories.
