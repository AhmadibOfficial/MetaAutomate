# P2-03s — Disposable Secure CRM and Business Resilience Intelligence

**Delivery class:** testable private-staging *rehearsal* on disposable GitHub Actions PostgreSQL 16 only. **Not an independently authorized live private staging environment; not production ready.**

Merged dependency: PR #80 (Meta signed-event review). This work is a new draft increment, independent of any live deployment authorization.

## Tested engineering objective

1. **Authenticated tenant sessions** — disposable PostgreSQL LOGIN roles with separate randomly generated CI passwords, NOINHERIT and NOBYPASSRLS; deny all public schema grants. Protected tenant mappings are stored in an unexposed table. RLS uses the authenticated SQL `session_user` identity via a SECURITY DEFINER lookup with pinned search path. A client-written `app.tenant_id` setting cannot change tenant identity. SQL login is actual CI authentication, but is not Meta account authentication or application RBAC.
2. **Durable idempotency** — a PostgreSQL unique tenant/platform/account/event key and restricted INSERT; replayed identical signed synthetic events create zero new records after a new SQL session, while a duplicate ID with changed digest is rejected.
3. **Encrypted example evidence** — AES-256-GCM, OS-generated 96-bit nonce, HKDF-SHA256 per-tenant key derivation from ephemeral 256-bit CI master; associated data binds tenant, provider account and event ID. No plaintext retained in database. The master key exists only within the disposable test process. Real encrypted customer data, key rotation, KMS, deletion and backup safeguards are NOT implemented.
4. **Consent evidence and revocation** — append-only illustrative purpose-linked reviews, an SQL transaction-serialized revocation guard, no UPDATE grants on consent history. A simulated consent flag never validates real Meta or customer permissions.
5. **Human review** — bounded synthetic agent task state in PostgreSQL, with permanently disallowed outbound execution flag. No authenticated staff inbox or customer messaging exists.
6. **No unauthorized migrations** — SQL at `database/disposable/p2_03s_meta_leads_staging.sql` checks that the target is exactly `meta_stage_ci` and requires a test-only session marker. It is **not** under production migration files and MUST NOT be applied on Kali, DigitalOcean, Render or business databases.

### CI commands

GitHub workflow `.github/workflows/p2-03s-disposable-crm-resilience.yml` launches an ephemeral PostgreSQL service, provisions test-only role secrets and exercises:
- `python -m pytest -q -rs tests/test_disposable_meta_crm_postgres.py`
- `python -m pytest -q tests/test_synthetic_business_resilience.py`
- `python -m pytest -q tests/test_meta_webhook_signature.py tests/test_synthetic_meta_lead_federation.py`

Actual live private staging with independent access, network isolation, approved costs, response/backup recovery testing and external security review remains an explicit dependency, not an accomplishment of this CI.

## Business Continuity and Revenue Expenditure Intelligence

This increment expands the existing twelve-module Business Value and Decision Intelligence suite with an offline `synthetic_business_resilience.py` analyzer.

- **Continuity reviews:** supplier delay, system outage and cost leakage reviewed using transparent 1–5 **ordinal** likelihood/impact scores. Their product is only a review priority, **not a probability or insurance-style expected loss**. Recovery actions are owner-controlled descriptions, not live failover.
- **Unit economics:** gross sales, six identified expense categories, modeled contribution, identified-cost-to-sales ratio and budget gap. CAC, LTV, EBITDA, net profit and actual savings remain unknown without verified business ledgers, allocation rules and complete cost coverage.
- **Scenario stress tests:** an unchanged baseline, 25% assumed demand shock, 20% assumed identified-cost increase and a combined scenario. These are sensitivity arithmetic, **not predictive modeling or earnings claims**.
- **90-day pilot:** days 1–30 baseline validation, days 31–60 supervised cost/continuity improvements, days 61–90 outcome verification with comparison periods and competing causes. All are prospective; no customer benefit has been measured.
- **Data governance:** input size limits, exact allowlisted schemas, no PII, duplicate rejection, deterministic results and verifiable SHA-256 fixture identifiers.
- **Operating cost discipline:** prioritize possible idle seats, unreconciled costs and supply risks for review, without asserting those costs are actually recoverable.

## Next required release gates

1. Independent approval and provisioning of a real **private** staging network, its risk and cost ceiling, credential vault, monitoring and deletion controls.
2. App-layer tenant authentication / RBAC, authorized Meta business-account ownership, verified permissions and approved token handling.
3. Source-of-truth webhook ingress with TLS, replay limits, backed-up idempotency, provider-origin mapping, secure failures and user-deletion rights.
4. Actual consent evidence (who, when, what purpose, what notice, provenance and revocation), legally reviewed data retention and customer privacy.
5. Independently reviewed DB-role provisioning, encrypted production key lifecycle, data-subject rights, tested restore and staff inbox authentication.
6. Human-authorized and policy-compliant follow-ups only; separate approval for any live connection or ad spend.

**Release:** Foundation Phase 01 3/9 verified; operational Phases 02 and 03 NO-GO. No migration to Kali, no Meta business connection, no paid subscription, no cloud provisioning, no production activation.

## Technical references

- PostgreSQL 16 row-level security: https://www.postgresql.org/docs/16/ddl-rowsecurity.html
- NIST SP 800-34 Rev. 1 business continuity and recovery: https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-34r1.pdf
