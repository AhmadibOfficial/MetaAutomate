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


## Stage 01 / F06 — disposable PostgreSQL negative authentication acceptance

The **existing** `scripts/verify_oidc_identity.py` has been enhanced, rather
than creating another identity-test harness. It now checks the **actual
transaction-scoped PostgreSQL** `app.organization_id` and `app.user_id`
settings after authorized session creation/authentication, then after denied
CSRF, unknown sessions, unprovisioned subjects, suspended membership,
revoked session and revoked identity. A new valid authentication following
a denied attempt must reestablish precisely its own organization and user.
The regression specifically exercises a previously successful tenant context
followed by denials **on the same runtime connection/transaction**.

This integration script only runs under the previously established
`GITHUB_ACTIONS=true` gate on the disposable PostgreSQL service created
and migrated by `.github/workflows/ci.yml`. It does **not** create a
database, apply migrations, or connect in an ordinary pytest invocation.
Do not attempt to bypass its CI-only gate or aim DATABASE_URL at a
developer/staging/production instance. Because GitHub Actions runners are
currently billing-blocked, this integration improvement is **source
committed but not independently exercised**. Two read-only source-contract
checks in `tests/test_private_oidc_contract.py` can run on the current Kali
checkout, but do not constitute actual PostgreSQL acceptance.

Safe owner Kali command (source tests ONLY):

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
  tests/test_private_oidc_contract.py \
  tests/test_stage01_f06_oidc_claim_admission.py \
  tests/test_p2_04a_oidc_mfa.py
```

The CI-only integration remains pending a real isolated GitHub runner and
independent reviewer. Real issuer/JWKS/PKCE/nonce/MFA, sealed ingress, F04
branch protection and F07 off-host restore are also unresolved. Foundation
F06 is still BLOCKED; full release **NO-GO**. No migration 012 was
applied to the owner's Kali machine; no browser, customer, subscription,
network/AI/social, deployment, billing or funding work was activated.


## Stage 01 / F06 — two-tenant disposable OIDC isolation

The pre-existing CI-only `scripts/verify_oidc_identity.py` fixture now provisions
**two fictional organizations and separate identities** (OWNER and OPERATOR)
in the same ephemeral PostgreSQL service. It verifies:

- Each OIDC issuer+subject maps to its **own** preprovisioned organization and user.
- Swapping the organizations' CSRF hashes denies access and clears both tenant GUCs.
- Re-authenticating A → B → A on the same connection binds **both** transaction-local tenant settings to the selected principal, with no retained previous tenant.
- Revoking tenant A's identity blocks A without invalidating tenant B's independent session.

Two source-contract tests preserve the negative matrix. The actual PostgreSQL
assertions remain **NOT_RUN** until GitHub Actions or another independently
authorized, genuinely disposable runner becomes available. The source-contract
tests can be executed normally on Kali; do not bypass the CI-only PostgreSQL
guard, apply migration 012 on existing data, change GitHub billing, merge
branches, activate actual OIDC/SSO, deploy, or claim F06 acceptance. Foundation
NO-GO remains binding.


## Stage 01 / F06 — NULL OIDC digest rejection (candidate migration only)

The unapplied `database/migrations/012_oidc_identities.sql` candidate now
explicitly rejects NULL subject, session and CSRF SHA-256 values **before**
attempting an OIDC workspace-session insert. PostgreSQL treats
`NULL !~ pattern` as UNKNOWN rather than TRUE, so a regex-only OR guard
could otherwise fall through and raise a database constraint error. The
intended response is an ordinary no-principal denial with both
transaction-local tenant settings cleared, not an exception or session.

The existing CI-only disposable PostgreSQL identity harness adds three
NULL-digest denial cases, each immediately after successful authentication
in the same transaction, followed by a valid reauthentication. Two
source-contract tests ensure the early SQL guards and harness assertions
remain present. No production migration or runtime setting was changed.

Owner-local **source-only** acceptance command at the exact reviewed PR head:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_private_oidc_contract.py \
  tests/test_stage01_f06_oidc_claim_admission.py \
  tests/test_p2_04a_oidc_mfa.py
```

The new head has **not** been executed against PostgreSQL, Kali pytest or
independent CI. Real OIDC/PKCE/JWKS/MFA, tenant RLS, negative-role browser
testing, private ingress, backup/restore and release approval remain
unverified. F06 is BLOCKED; Foundation remains historically 3/9 verified,
and production/application submission remain NO-GO. Do not bypass the
CI-only database guard, apply migration 012, merge or deploy without
separate explicit approval.


## Stage 01 / F06 — issuer-and-subject collision isolation (synthetic only)

The existing **CI-only**, disposable PostgreSQL identity fixture now adds a
second fictional HTTPS issuer. It deliberately provisions the **same SHA-256
subject digest** under two different issuers to different organizations and
users. The integration assertions require the pair `(issuer, subject_sha256)`
to resolve the correct tenant and member role. They also require:

- A different issuer with an unprovisioned subject to deny admission and
  clear both transaction-local tenant context settings after a prior success.
- The original issuer's session to remain correctly bound after that denial.
- Revoking the first issuer's identity not to revoke a distinct identity from
  the second issuer, even when both share the same subject digest.

Two additional **source-only** regression tests check that the negative
cases remain present. The actual PostgreSQL assertions are **NOT_RUN** until
an authorized ephemeral CI database is available; these tests do **not**
validate actual IdP issuer trust, signature/JWKS, MFA, PKCE, browser sessions
or tenant RLS. The CI-only guard remains in place. Do not set `GITHUB_ACTIONS`
manually, run against the owner's Kali database, apply migration 012, merge,
deploy, spend money, enable subscriptions, or submit the funding application.
Foundation F06 remains BLOCKED and release remains NO-GO.


## Stage 01 / F06 — tenant- and user-bound session revocation (candidate only)

The existing migration 010 `app.revoke_workspace_session` accepts an opaque
session digest but did not constrain its update by the authenticated
transaction principal. The **unapplied** migration 012 now replaces that
function without changing its SQL signature: it requires nonempty
`app.organization_id` and `app.user_id` transaction settings and updates
only the session whose digest, organization **and user** all match. This
preserves the normal authenticated browser logout flow, while denying
cross-tenant, cross-user or unauthenticated runtime revocation by digest
alone.

The existing CI-only ephemeral PostgreSQL identity harness now attempts to
revoke tenant B's session from tenant A's authenticated context and again
from a new connection with no identity context. Both must leave B's
session usable; the original legitimate revocation assertion remains.
Two offline source-contract tests cover the function guard and negative
harness cases.

**Security scope:** transaction-local settings are meaningful only when
established through the existing trusted authentication flow; they are
not a defense against arbitrary SQL execution or an independently verified
identity proof. The SQL function is a migration candidate, not a change
applied to any owner database. The actual negative tests are **NOT_RUN**
until independently authorized disposable PostgreSQL CI is available.
GitHub Actions account billing remains blocked. Live OIDC issuer/JWKS,
MFA/PKCE, cross-tenant RLS, browser tests and independent review are
unverified. F06 BLOCKED, Foundation 3/9 historically verified, production
and QDB submission NO-GO. Do not spoof CI flags, apply migration 012,
merge, deploy, enable billing or spend funds without separate approval.


## Stage 01 / F06 — SQL candidate integrity regression

Source review detected a **malformed migration 012** in the prior draft:
the replacement session-revoker function had a truncated dollar-quoted
body and a premature `COMMIT`/grant inserted inside the digest predicate.
This would make the candidate migration invalid if applied. The candidate
text has been repaired **without executing it**: all three PL/pgSQL bodies
use balanced `AS $$ ... $$;` delimiters, the session digest guard is intact,
and exactly one `COMMIT` terminates the migration after the function grant.

A source-only regression in `tests/test_private_oidc_contract.py` checks
the three delimiters, the single terminal transaction boundary, the grant
placement and the revoker's tenant/user/digest predicates. These are
**static text checks, not SQL parsing or a PostgreSQL execution result**.
Next acceptance still requires independently authorized disposable
PostgreSQL syntax/application, revocation and RLS testing. Never run the
migration against the owner's existing database or bypass the CI-only
integration guard. F06 remains BLOCKED; production and QDB submission NO-GO.


## Stage 01 / F06 — CI database target interlock (2026-10-27)

The disposable OIDC integration harness now calls
`scripts/oidc_ci_database_guard.py` **before any PostgreSQL connection**.
The standard-library-only guard requires the expected GitHub-hosted
`push`/`pull_request` job context, repository, numeric run ID, and separate
admin/runtime PostgreSQL URLs targeting the existing CI fixture at
`localhost:5432/metaautomate`. It rejects remote hosts, arbitrary databases,
wrong roles, socket-style DSNs, query-parameter overrides and missing passwords.
The exact fixture host, database and roles are taken from
`.github/workflows/ci.yml`; no service or migration was changed.

Two offline Python regression tests exercise accepted synthetic CI inputs and
negative environment/DSN cases **without connecting to any database**. They
can be run alongside the existing F06 source-contract tests from a clean,
trusted checkout:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_private_oidc_contract.py \
  tests/test_stage01_f06_oidc_claim_admission.py \
  tests/test_p2_04a_oidc_mfa.py
```

**Limit:** CI environment variables and a loopback DSN do not cryptographically
prove that PostgreSQL is disposable. A malicious or misconfigured runner could
still mimic them, and a local process could occupy that port. The CI-only
interlock is defense-in-depth against accidental non-CI or remote execution,
not authorization to set CI variables manually or to run this script on Kali.
Actual isolated PostgreSQL acceptance, independent security review, real
IdP/MFA/PKCE/JWKS, F04–F09 and release approvals remain pending.
GitHub Actions billing is still blocked. No production database was touched;
Foundation remains historically 3/9 verified and **NO-GO**.


## Stage 01 / F06 — Exact disposable CI DSN matching (2026-10-27)

The OIDC PostgreSQL integration interlock now accepts **only the two literal
admin/runtime connection URLs configured in `.github/workflows/ci.yml`**,
including their deliberately throwaway CI-only passwords. It no longer accepts
an arbitrary nonempty password or alternate localhost spelling. This narrows
accidental targeting of a developer-local database that happens to share the
same host, port, database name and role. Exact comparison also rejects
ambiguous percent-encoding, whitespace and URL parser normalization.

Six additional negative fixture cases cover alternate credentials, IP
spelling and embedded control characters. The guard does not open a database
connection, and the test cases are source-only. These CI fixture credentials
are intentionally non-production and must never be reused for any developer,
staging or production database. If the CI fixture changes, update the guard
and tests together under review.

This remains **defense-in-depth**, not proof of an isolated runner or database:
a malicious environment can spoof GitHub variables and mimic the literal
connection URL. No PostgreSQL migration or actual integration run occurred.
F06 remains BLOCKED, Foundation 3/9 historically verified, and production,
customer operations and QDB submission remain NO-GO.
