# P2-04a — Authenticated Business Value Demonstration Admission

**16 October 2026. Source engineering only; real staff/private staging remains NOT LIVE.**

## What changed
The private pilot outcome API now requires a second, cryptographically verifiable admission control beyond the previously existing OIDC mode, explicit pilot flag and HTTPS acceptance-record URL. The operator mounts an externally prepared JSON receipt. Two **distinct independent Ed25519 signer keys** attest to a single tenant, exact deployment Git commit, real HTTPS IdP issuer, private staging origin, F04–F08 evidence references and bounded expiry of at most 24 hours.

Validation is repeated for **every API request**, not just at startup. Missing, revoked, changed, expired, forged, cross-tenant or cross-commit admission blocks the pilot endpoint. No private signing key is ever committed to the repo. This extra check is deliberately fail closed.

**Cryptographic signatures only authenticate the signed claims.** They do not prove real GitHub branch protection, genuine source records, staff MFA, a live network perimeter, an off-host restore or customer consent. Independent witness review of the underlying artifacts is still mandatory.

## Current real-world blockers
- **F04:** GitHub main remains unprotected, with private-repo rulesets returning HTTP 403 and an upgrade requirement. No eligible plan was purchased and the private repo must not be made public.
- **F05:** No approved isolated private staging with operator, region, security design, cost ceiling and independently inspected perimeter.
- **F06:** No independently witnessed actual staff OIDC/MFA and revocation on the deployed environment.
- **F07:** No separately witnessed off-host encrypted backup and restore.
- **F08:** No complete live security, agent egress, audit and rollback acceptance.
- **F09:** No verified consented business pilot and measured real outcome.

Phase 01 remains 3/9 verified. Phase 02 and Phase 03 are operational NO-GO.

## Signed admission contract

The implementation is in apps/api/app/p2_04a_pilot_admission.py.

The signed JSON document contains exactly:
1. schema_version 1, purpose PRIVATE_STAGING_AGGREGATE_MEASUREMENT, repository AhmadibOfficial/MetaAutomate, and environment PRIVATE_STAGING.
2. Commit SHA (40 lowercase hex), canonical tenant UUID, exact HTTPS workspace_origin and oidc_issuer, consent_scope AGGREGATE_ONLY and external_execution false.
3. issued_at and expires_at UTC timestamps, no longer than 24 hours apart.
4. Exactly F04, F05, F06, F07, F08 evidence objects, each containing artifact_sha256, witness_url (independently inspected HTTPS reference) and the corresponding witness_kind: FAILED_MERGE_DENIAL, PRIVATE_PERIMETER_INSPECTION, LIVE_IDP_MFA_REVOCATION, OFFHOST_RESTORE_WITNESS and LIVE_SECURITY_ACCEPTANCE.
5. Two signatures, OWNER followed by INDEPENDENT_REVIEWER, separately generated, signed over canonical sorted-key ASCII JSON of all the document fields **except signatures**.

Private-staging configuration (all deliberately absent by default):
- WORKSPACE_AUTH_MODE=oidc, MAT_PILOT_OUTCOMES_ENABLED=1, WORKSPACE_COOKIE_SECURE=1.
- MAT_PILOT_ACCEPTANCE_RECORD: independently witnessed immutable HTTPS evidence reference, not a user-provided arbitrary link.
- MAT_PILOT_ADMISSION_FILE: absolute path of securely mounted non-symlink signed JSON, outside Git.
- MAT_PILOT_OWNER_VERIFY_KEY and MAT_PILOT_REVIEWER_VERIFY_KEY: distinct pinned base64url Ed25519 public keys; corresponding **private** keys must remain with the two independent signers, never the API.
- MAT_DEPLOY_COMMIT_SHA and MAT_PILOT_TENANT_ID: separately approved exact deployment and sole authorized pilot organization.
- WORKSPACE_ORIGIN, OIDC_ISSUER, APP_DATABASE_URL and existing private OIDC settings: approved HTTPS ingress, real staff identity provider and restricted runtime DB user.

A configuration administrator who can replace BOTH public keys or the whole private runtime could circumvent source-level trust. Production therefore requires independently protected deployment configuration, approvals, key custody and witnessed evidence, not only this code.

## End-to-end acceptance (AFTER F04–F08 live proof)

1. An independent reviewer inspects GitHub required-check enforcement and a deliberately failed, refused-to-merge negative-control PR.
2. An owner approves a genuinely private staging host, region, provider, ingress, spending ceiling and security controls.
3. With a real approved IdP, an enrolled employee authenticates using MFA as OPERATOR, submits an explicitly consented BASELINE aggregate and then equal-duration nonoverlapping CURRENT aggregates. Test expired/revoked/MFA-missing/wrong-tenant sessions and CSRF.
4. An independently authenticated *different* OWNER or ADMIN inspects source records and consents, then signs each independent immutable human review. Negative cases must demonstrate denied self-review, forged receipt hashes, duplicate keys and tenant crossing.
5. The business owner and independent reviewer witness the before/after cost and contribution computations, without claiming net profit, AI-generated income, causal business impact or real ROI. The accounting source itself needs independent authentication.
6. Independently verify staff revocation, API audit, worker egress denial, removal/expiry of the signed admission, monitoring, rollback and encrypted off-host recovery. This does not alone complete F09; actual real customer outcomes still need a separate consented pilot evaluation.

## Verification and permissions

Tests in tests/test_p2_04a_pilot_admission.py use throwaway in-memory signer keys and fictional witness references. They are strictly CI assertions, not operational evidence. Existing P2-03z PostgreSQL CI continues validating immutable tenant-scoped financial receipts.

- No new hosting, subscriptions, customer migrations, real model calls, messages or permanent databases were activated.
- Merge of source and publication of the existing apps/site static Render service do not authorize an API deployment or waive F04–F09.
- A real live demonstration cannot be performed until eligible GitHub branch protection and an explicitly approved private staging environment exist.
