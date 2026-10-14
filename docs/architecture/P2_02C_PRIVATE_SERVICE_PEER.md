# P2-02c — Private service peer policy (source-only candidate)

**Status: SOURCE-ONLY, NO LIVE TRUST.** Phase 01 still NO-GO (3/9). Neither OneCall nor MetaAutomate has an approved private ingress, live MFA or deployed verified service-to-service transport.

## Workstream status
- OneCall [PR #3](https://github.com/AhmadibOfficial/OneCall/pull/3) is still an open draft auth baseline.
- OneCall [PR #4](https://github.com/AhmadibOfficial/OneCall/pull/4) is an open draft backend Ed25519 assertion issuer, stacked on PR #3; full CI passed.
- MetaAutomate P2-02a verifier and P2-02b JTI/denial source were merged. The JTI redemption has no grant to runtime and migrations 012–014 have not been approved on Kali.

## What P2-02c tests

The pure `onecall_peer_policy.py` contract describes a future authenticated service-channel boundary: a verified mutual-TLS client certificate, an exact service identity URI, trusted certificate-chain validation, an operator-pinned certificate SHA-256, handshake freshness, evidence from the trusted TLS adapter, and disabled-by-default admission. Successful evaluation returns only `PEER_VERIFIED_IDENTITY_TEST_ONLY`, explicitly **without** organization membership, booking rights, payments, tools, or model execution.

The negative suite covers missing approval, stale handshakes, wrong service identity, certificate substitution, missing mutual TLS, unverified chain and forwarded-header impersonation. The test uses **synthetic evidence**, not a live certificate chain or cloud service.

**Critical:** `VerifiedTlsPeerEvidence` is only a Python data structure. It can be constructed by an untrusted caller and must NEVER be populated from JSON, a forwarded certificate header, bearer JWT, or client-controlled metadata. The `verified_chain` field is NOT itself a cryptographic verification. This function MUST remain disconnected from live routes until a separately audited TLS-terminating adapter establishes full certificate-chain validation and signed/protected evidence over a trusted local IPC connection or an equivalent non-spoofable transport. A hash pin alone is not a PKI chain validation. This PR contains no such adapter.

## Future end-to-end handshake and release gates
1. Approve and provision a private OneCall-to-MetaAutomate network path with an authenticated server and client peer, rotated service certificates, chain/revocation checks, mutual TLS, and correct certificate-identity extraction.
2. Ensure the OneCall issuer can only run after JWT guard, CURRENT authoritative account lookup, service consent, abuse limits and a separately controlled key; do not expose mobile JWTs or private keys.
3. Verify dedicated Ed25519 assertion against pinned review-approved public keys and exact OneCall issuer and AMBOY audience; do not accept mobile HS256, `jku`, or client-declared tenant IDs.
4. Verify independently fresh OneCall session/version/account status over the protected service channel, consume JTI atomically once, and audit first-use/replay/denial with retention.
5. Create an independent, approved OneCall product-tenant and resource-ownership map after security review; no email-match membership.
6. Run cross-product, replay, rotated-key, forged-header, expired-certificate, proxy misconfiguration and revocation tests on approved staging.
7. Keep Foundation NO-GO and the customer connection OFF until cloud host, cost, real OIDC/MFA, private ingress, recovery and pilot gates are independently verified.

No migrations, cloud deployments, live trust grants, Render/DigitalOcean changes, OneCall source merge or customer access are authorized by a green CI result.
