# P2-03 — Subscription-free synthetic inventory adapter

**Status:** source-only development demonstration. Not an external provider integration, customer dashboard, paid service or production capability. Phase 01 remains NO-GO (3/9).

## Goal

Progress Phase 02 without paid cloud hosting or external SaaS subscriptions. Build and verify a narrow, **read-only local inventory simulation** that demonstrates the eventual business logic of an approved inventory connector and the separation between simulated and customer data.

The local synthetic fixture is `contracts/domains/v1/fixtures/synthetic_inventory.json`, containing invented stock records for maize, soybean, sorghum and packaging. There are no company credentials, customer identifiers, phone numbers, financial accounts or external URLs. No API call, payment integration, credential or background job is made.

## Developer-only endpoint

`GET /v1/domain-integrations/sandbox/inventory`

This is registered **only for dev_key authentication mode** and is OFF unless `DOMAIN_SANDBOX_MODE=local_synthetic`. The sandbox also verifies that the workspace origin is loopback HTTP, the direct connecting peer is loopback, and the authenticated organization's role is OWNER, ADMIN or OPERATOR. Query parameters are rejected entirely; a caller cannot select a tenant ID, fixture path, connector URL or product scope. A true production environment must additionally enforce trusted network binding: loopback request metadata alone is **not proof of network isolation** when a reverse proxy is in use.

The endpoint returns a deterministic read-only reorder analysis (below-threshold SKUs, suggested restock units, totals, fixture SHA-256 and a non-secret per-organization *demo partition marker*). All responses are labeled `LOCAL_SYNTHETIC_SIMULATION`, `actual_business_data=false`, `simulation_only=true`, `connector_state=unbound`, `execution_available=false`.

The existing `POST /v1/domain-integrations/preview` policy for `business.inventory.stock-preview.v1` **continues to return DENY**; the original capability registry remains DRAFT. No product scope or real read privilege is created by running a simulator.

## Safe local test

Run from a code checkout with dependencies installed:

```bash
PYTHONPATH=apps/api python -m pytest -q tests/test_phase02_synthetic_inventory.py
```

For an isolated development instance, the operator may explicitly set `DOMAIN_SANDBOX_MODE=local_synthetic` with `WORKSPACE_AUTH_MODE=dev_key` and a loopback `WORKSPACE_ORIGIN`. The route still requires existing user authentication. Do not expose the API through a public reverse proxy, forward a browser dev cookie to third parties, or enable this flag on a cloud instance.

## Tested behaviors

- Offline fixture-only data and mathematically correct reorder suggestions
- Repeatable deterministic read-only outputs
- Server-derived organization demo partition; different organizations cannot select one another's ID through query input
- Unauthorized VIEWER and unknown roles denied
- Forged tenant, user, connector URL, scope and custom fixture selection denied
- OIDC/production, wrong environment mode, non-loopback request and origin denied
- Existing inventory capability remains DRAFT/DENY with no connector bound
- No real data access, external network requests, DB writes, credential provisioning or payment required

## Remaining before a legitimate P2-03 customer adapter

- Select an approved real inventory provider and receive **authorized** sandbox credentials, or design an approved tenant-scoped local integration owned by the customer.
- Implement least-privilege, read-only provider scopes; authenticated tenant identity, authorization and source data provenance; bounded response schema/size; timeout/retry and rate limits; privacy minimization; audit receipts; revocation; and cross-tenant negative tests.
- Deploy into approved private staging with protected GitHub release checks, real MFA/private ingress and independent restore; obtain external security acceptance and written customer consent before using actual business data.

This source milestone does **not** close Foundation F04-F09 or constitute a successful external P2-03 integration.
