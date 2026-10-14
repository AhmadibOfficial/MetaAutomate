# Phase 02 — Platform Expansion

**Status:** Source development started, **not production ready**. Phase 01 Foundation remains NO-GO (3/9 release gates verified). These tracks can advance in parallel, but Phase 02 source work does not waive GitHub protection, staging, identity, recovery, security, or pilot gates.

## Scope

MetaAutomate's next platform layer turns a single development Objective Workspace into a framework for distinct business domains and independently authorized connectors.

A domain operation contract names the business capability, version, effect type, required product scope, risk classification and whether a separate action approval is required. None of those fields grants access by itself.

### First integration contracts (all source-only DRAFT)

| Contract | Registry capability | Intended eventual value | Current boundary |
|---|---|---|---|
| `business.lead-intake.validate.v1` | BIZ-002 | Validate lead intake before CRM entry | No lead data accepted or saved |
| `business.crm.sync-proposal.v1` | BIZ-006 | Prepare a CRM sync proposal | No CRM configured and no write |
| `business.inventory.stock-preview.v1` | BIZ-011 | Review authenticated inventory data | No inventory system connected |
| `business.finance.reconciliation-proposal.v1` | BIZ-012 | Prepare evidence-based bookkeeping reconciliation | No financial record read or mutated |

Versioned machine contract: `contracts/domains/v1/operations.json`. Runtime contract registry lives in `apps/api/app/domain_integrations.py`; a source parity test prevents it from drifting from the exported contract file. Existing capability definitions remain DRAFT and disabled.

## First API milestone — authenticated contract discovery and deny-only policy preview

- `GET /v1/domain-integrations/contracts`: authenticated organizational members can discover the four **draft** integration declarations; VIEWER may browse.
- `POST /v1/domain-integrations/preview`: authenticated OWNER/ADMIN/OPERATOR can request a read-only admission decision for one operation ID and optional correlation UUID. All requests currently return `decision=DENY` with specific outstanding prerequisites and `executed=false`.
- The client cannot supply organization, actor, product, role, scopes, approval token, connector address or business records. Server-side session auth and CSRF remain in force. No external API, database write, job queue, AI model or connector is used.
- No new migration; existing migrations 012–013 remain unapplied to the owner's Kali database.

**The preview is a policy explanation, not an execution plan or a way to grant scopes.** Binding an integration will require a separate reviewed adapter, scope mapping, least-privilege identity, tenant isolation, rate limits, approval mechanism, idempotency, audit receipts and live security acceptance. No operation may become executable merely by editing a manifest flag.

## Engineering sequence

1. **P2-01 — Domain contract foundation** (this PR): documented versioned contracts, authenticated discovery, deny-only policy previews, negative tests, CI acceptance.
2. **P2-02 — Independent product and tenant identity**: P2-02a source-only OneCall pilot-auth review and offline dedicated asymmetric assertion signature verifier is implemented; it is NOT connected to AMBOY. P2-02b still requires actual OneCall backend assertion issuance, private service identity, atomic JTI replay prevention, fresh account revocation, product-scoped authorization, tenant mapping and denial auditing. Never join MetaAutomate and OneCall users by matching email.
3. **P2-03 — Read-only pilot adapter**: choose ONE target domain and one authorized provider, obtain approved sandbox credentials and private staging, verify isolation and provenance with synthetic records.
4. **P2-04 — Durable integration delivery**: job state, signed webhooks, bounded retry/backoff, rate limits, deduplication, compensating actions, observability and safe incident recovery.
5. **P2-05 — Controlled write proposals**: scoped authorization for a specific effect, human approval, preflight, idempotency, authoritative provider receipt and independent verification.
6. **P2-06 — Commercial pilots and resilience**: controlled customer onboarding after Phase 01 operational gates, support workflows, tenant security assessment, evidence-based value measurement and service cost limits.

**No external action, customer access or commercial rollout is authorized in P2-01.** This document does not mean Phase 01 can be marked complete.

## Validation and release boundaries

- CI runs automated schema/contract parity, policy rejection, unauthorized-session denial, CSRF-compatible dependency integration and full existing Operational Core/AMBOY/Chromium/recovery tests.
- Readiness artifacts continue to report Foundation **NO-GO** until the six live gates have independently verified evidence.
- Public Render marketing remains a static service with Auto-Deploy and PR Previews off. A website source revision does not deploy or activate platform functionality.
- PR merge is a source engineering change only. No migrations 012–013 on Kali, customer data, provider accounts, hosting costs, secrets, financial postings, bookings, ads or model inference.
