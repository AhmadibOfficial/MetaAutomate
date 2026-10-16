# P3-04 — Business Analytics and Intelligent Insights (offline synthetic source)

**MetaAutomate development continues without subscriptions.** This milestone builds a deterministic analytics foundation for future business improvements. It does **not** read financial accounts, handle live customer records, authorize financial actions, claim verified ROI, or generate income guarantees. **Phase 01: 3/9 NO-GO; Phase 02 operational: NO-GO; Phase 03 real execution: BLOCKED.**

## What we implemented

- `apps/api/app/phase03_business_analytics.py`: bounded integer-based analytics on invented `DemoBusinessPeriod` fixtures only; tenant UUID, fixed DEMO currency/source, strict calendar label, 1–12 unique periods, integer minor units, max counts and cost bounds; rejects partial or semantically inconsistent sales funnels.
- Deterministic metrics: `leads`, `qualified_leads`, `paid_orders`, `refunded_orders`, `retained_orders`, `gross_sales_minor`, `refund_value_minor`, `net_sales_minor`, `variable_cost_minor`, `marketing_cost_minor`, `fixed_cost_minor`, `hypothetical_net_minor`, lead-to-order basis points, refund basis points and hypothetical margin basis points.
- Transparent finance arithmetic: `net_sales = gross_sales - full refunds`; `variable_cost = paid_orders * per_paid_order_cost` (including refunded orders); `hypothetical_net = net_sales - variable_cost - marketing - fixed`. All units are **DEMO-UNIT**, not Nigerian naira or verified sales.
- Missing denominator is `null` plus a quality code, **not zero, fabricated percentages or observed business success**. Every report retains `business_value_measured=false` and `decision=DENY`.
- Rules-based synthetic insight codes flag negative hypothetical margin, refunds 10% or greater, stock below retained orders, and lead-to-order below 5%; *no language model, web inference, recommendations to trade or operational automation.*
- `simulate_demo_increment` models a highly optimistic **counterfactual** based on the final synthetic period with extra paid/retained orders and stated marketing cost; ignores returns, incremental overhead, real demand, seasonality and market prices. **Not a forecast, ROI, income claim or verified financial advice.**
- `contracts/intelligent/v1/business_analytics.json` and `tests/test_phase03_business_analytics.py`: machine-readable source scope and edge-case security tests, including invalid calendars, unexpected tenant source, malformed funnels, overflow, undefined denominators, integer type confusion, double-period aggregation and CLI execution denial.

## Developer commands

The following are free, local-only and use hard-coded invented test inputs:

```bash
python scripts/phase03_offline_cli.py business-demo
python scripts/phase03_offline_cli.py scenario-demo
python scripts/phase03_offline_cli.py scenario-demo --extra-orders 5 --extra-marketing-minor 10000
```

The demonstration fixture contains two invented time periods. Positive simulated values describe **arithmetic only**, never observed revenue or business profitability. The CLI has no option to import actual records, set a real provider endpoint, send messages, accept payment instructions or execute a transaction.

## Quality and security gates for future scale

Before handling authorized customer data, MetaAutomate needs a separate approved tenant-scoped ingestion contract, explicit data rights and privacy disclosures, provider identity and read-only permission validation, secure retention, aggregation access controls, cross-tenant adversarial tests, audit provenance, currency/cost semantics verified by business owners, and monitoring of missingness and uncertainty. Financial metrics need reconciliation to independently sourced records, not generated examples.

**Source branch dependencies:** P3-04 is based on unmerged draft PR #46 (P3-03), itself containing PRs #44 and #45. This P3-04 candidate targets `main` to trigger the existing GitHub PR CI; this does not merge any of those parents or grant independent approval. Exact-head GitHub CI and owner Kali acceptance are separate evidence.

## Follow-on milestone

**P3-05 — Developer Experience and Tooling:** consistent CLI argument standards, OpenAPI-like source capability contract generator and offline typed SDK examples with strict no-provider-connect conditions. Later P3-06 execution requires independent review, protected branches, actual service identities, customer permission, proven durable replay prevention, readback, rollout and explicit release authority.

**NO-GO for live effects.** No cloud purchase, migration, production deployment, customer import, provider read/write, live payment, real finance or AI-assisted autonomous action is authorized by source tests.
