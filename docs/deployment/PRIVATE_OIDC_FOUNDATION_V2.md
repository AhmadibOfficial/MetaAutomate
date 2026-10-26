# Private OIDC Identity Foundation v2 (PR #6 replacement)

**Status:** Compatibility candidate only. No Kali migration 012, cloud provisioning, SSO provider, production rollout or customer access is authorized.

This candidate replaces outdated PR #6. The previous branch used migration number 011 for OIDC while the existing Operational Core already uses migration 011 for immutable assessments. The corrected schema extension is 012_oidc_identities.sql, after migrations 001–011. **Do not apply 012 to the owner's working Kali database without an explicit separately approved backup, restore drill and change window.** The existing guarded upgrade script currently handles migrations through 011 only.

## Implemented as isolated source code

- Retains local development-key login and all existing objective/assessment interfaces when WORKSPACE_AUTH_MODE is dev_key (default development image only).
- In the opt-in OIDC runtime mode: require HTTPS issuer, origin and exact callback; secure cookies; sufficiently long state secret; restricted APP_DATABASE_URL; and no privileged DATABASE_URL. On missing config, start fails.
- OIDC identity maps a verified issuer+subject digest to a preprovisioned organization membership. Runtime cannot list the identity directory. Dev access-key login and dev bearer authentication are disabled.
- Browser login offers organization SSO only when the server reports OIDC mode. The identity provider callback creates a revocable, time-bounded database session. Existing assessment interface is preserved.
- The separate production Dockerfile defaults to OIDC-only and runs as an unprivileged user. It does not provision cloud resources, databases, DNS or network ingress.
- CI tests run against disposable PostgreSQL records to verify tenant mapping, revocation, restricted grants, CSRF and fail-closed configuration. These tests are NOT an externally verified OIDC issuer/JWKS/PKCE end-to-end proof.

## Remaining blockers before a private-cloud release

1. Select and explicitly approve a commercial-use hosting provider, pricing ceiling and region. Do not assume Tailscale Personal Free is suitable for business production.
2. Choose/configure a real OIDC provider, issuer, client, owner identity and MFA policy; verify the full authorization-code + PKCE + nonce + JWKS/token signature process against the actual provider.
3. Configure a genuinely private authenticated ingress, HTTPS, hardened reverse proxy and no public database port.
4. Use a separate staging database, encrypted protected backup, audited role provisioning and successful independent restore. Do not copy owner development data.
5. Test live SSO, cross-tenant denials, logout/expiry, refresh/session revocation, CSRF, abuse/rate limits, logs, monitoring, recovery and rollback. The old branch's Tailscale-specific automatic launcher is intentionally NOT copied.
6. Review PR head SHA and CI; acquire fresh, explicit approvals before applying migration 012 or deploying the application. Opening this PR does not authorize any runtime change.

The release evidence gate remains the source-merge signal, not a promise of production security.


## Stage 01 / F06 — OIDC identity-claim shape hardening (draft only)

The existing Authlib authorization-code callback previously coerced the
verified issuer and subject to strings. Unexpected `sub` types could
therefore become implicit string account identifiers; non-ASCII subjects
would fail later in the ASCII-only SHA-256 identity digest. The callback
now **denies before database session creation** when the purported
provider-verified claims are not a mapping, `iss` is not the configured
issuer as an exact string, or `sub` is not a printable 1–255-byte ASCII
string. The ID-token presence check also rejects nonstring placeholders.
Valid claim shapes proceed through the **existing** recent signed-MFA
policy; neither the MFA check nor the membership SQL is bypassed.

This is a narrow defense-in-depth fix. The synthetic tests use a fake
`authorize_access_token` response and deliberately **do not** establish
a signed JWT, real IdP, authentic MFA, correct Authlib state/nonce/PKCE,
tenant isolation, live SSO, browser acceptance or deployment readiness.

From a reviewed clean exact-commit checkout:
```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
  tests/test_stage01_f06_oidc_claim_admission.py \
  tests/test_p2_04a_oidc_mfa.py \
  tests/test_private_oidc_contract.py
```

Additional operator-owned acceptance remains mandatory: genuine IdP OIDC
code+PKCE+nonce signature/JWKS, MFA, tenant mapping, session revocation
and negative-role E2E; actual recovery and independent security review.
F06 remains BLOCKED; the full nine-control operational release is NO-GO.
No live provider, app secrets, external network, subscription/billing,
migrations, merges or deployments were activated by this source change.


## Stage 01 / F06 — transaction-scoped tenant isolation (source hardening)

The **unapplied** `012_oidc_identities.sql` candidate contains two
`SECURITY DEFINER` OIDC session functions. A failed authentication or a
revoked membership must never leave an organization/user GUC set inside
a transaction that could execute a subsequent statement.

Both `app.create_oidc_workspace_session` and
`app.authenticate_workspace_session` now clear
`app.organization_id` and `app.user_id` **before evaluating** the
provided identity/session token, and clear both again on denied active
membership. This retains the successful tenant-setting behavior for an
authorized principal; failure still returns no principal. The patch
does **not** apply migration 012, grant access or enable the OIDC service.

Two source-contract regressions were added to
`tests/test_private_oidc_contract.py`. Run in a clean checkout bound
to the PR HEAD:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
  tests/test_private_oidc_contract.py \
  tests/test_stage01_f06_oidc_claim_admission.py \
  tests/test_p2_04a_oidc_mfa.py
```

**Not a runtime proof.** These tests inspect the SQL source and synthetic
callback; independent PostgreSQL transactional checks, a real IdP
issuer/JWKS/PKCE/nonce/MFA integration, forced RLS checks, revoked
identity/session tests, complete cross-tenant denial, private browser
acceptance, backup/restore, human review and security sign-off remain
mandatory. F06 is BLOCKED; production NO-GO remains binding.
