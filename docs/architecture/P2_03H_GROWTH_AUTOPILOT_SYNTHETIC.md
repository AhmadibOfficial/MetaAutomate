# P2-03h — MetaAutomate Growth Autopilot, synthetic source prototype

**STATUS: SOURCE-ONLY / NO-GO.** This is a reusable *workflow proposal generator* based on fictional business events. It is neither a functioning Selar/Metricool integration nor an authorized multi-tenant platform.

## Commercial product hypothesis

**Outcome promise:** "Connect your business goals to an easy, measurable sales and customer-retention workflow." NOT "guaranteed income", "AI automatically makes money" or "automatic customer acquisition". A subscription should be defensible with monthly time saved, repeat purchase/learner retention, and **incremental contribution after fees** against a baseline, not just impressions or AI content volume.

**First two research examples** (real business names only in documentation): Meta Automate Academy (learning enrolment and alumni pathways) and Ahmad-IB Bespoke Tailoring (garment enquiries, aftercare and accessory upsells). The module itself uses entirely fictional `academy_demo` and `bespoke_demo` records, invented product names/amounts and `DEMO_CREDITS`.

## One goal, three onboarding screens

1. **Business profile:** choose retail/fashion or course/training, specify the business outcome (new paid orders, re-enrolments or contribution after spend), and review the data/consent policy.
2. **Connect or import (future):** choose an approved commerce/social provider, explicit minimum permission scope and contact consent rules. Before F04–F09 release gates, show *DISCONNECTED / DEMO ONLY* and use a synthetic fixture. No actual credentials, customer data or platform billing may be requested.
3. **Activate (future, separately gated):** preview rules, review each content/re-engagement action, see forecast/baseline definitions, set quiet hours, rate limits, opt-outs and spend ceilings. Autopilot must never bypass human review for payments, customer-facing messages, identity, stock mutation or marketing publication until explicit permission and live authorization are established.

**Client's homepage (design only):** This month's goal → approved/suppressed automation proposals → real completed orders (only after consented certified connector) → contribution after variable costs and advertising → trend versus a comparable baseline → human-review queue → what to try next. Never label modeled contribution as actual net profit. Show source and confidence of every figure.

## Automation recipes (source engine is bounded and deterministic)

| Trigger | Academy action | Tailoring action | Safety |
|---|---|---|---|
| Fictional opt-in lead | Draft sample lesson invitation | Draft fit/quality guide | Only if explicitly consented; **never sent** |
| Checkout abandonment | Rely on native merchant recovery | Same | **Suppressed**: Selar already handles reminders; no duplicate automation |
| Completed fictional order | Draft course onboarding | Draft garment aftercare | Review required, not sent; order validated |
| Fictional learning completion | Draft related training offer | Not valid | Requires synthetic opt-in and matching order |
| Fictional garment delivery | Not valid | Draft a related style offer | Requires synthetic opt-in and matching order |

The simulator recognizes `SYNTHETIC_OPTED_IN` or `NOT_RECORDED` only in fictional test events. That classification **is not a verified real-world consent record**. An event without opt-in is suppressed. No one is contacted.

The parser rejects duplicate event/order/product IDs, cross-workspace fictional journeys/products, unknown or mismatched purchases, excessive data, negative/float/bool monetary values, non-finite JSON numbers, unexpected personal/contact fields, and real-world currencies. Workspace separation here is mere in-memory validation; **tenant isolation, protected consent and secure provider authorization remain unverified.**

## Why use existing Selar capabilities, not rebuild them?

Selar documents native abandoned-transaction emails (including 15-minute and 1-day reminders): https://help.selar.com/portal/en/kb/articles/abandoned-transaction-17-6-2024 . It also describes native purchase tagging and integrations with Mailchimp (https://help.selar.com/portal/en/kb/articles/guide-to-connecting-your-selar-store-to-mailchimp-setting-up-automation-tags) and MailerLite (https://help.selar.com/portal/en/kb/articles/simple-guide-to-connecting-your-selar-store-to-mailerlite-setting-up-automation-tags). These require provider configuration and may require a linked bank account; **no connection is claimed or attempted here**.

A future consented MetaAutomate tenant would use approved native provider integrations where appropriate, ingest only authorized aggregate data/approved events, and avoid duplicating reminders. Direct Metricool API integration is restricted to eligible plans; manually reviewed posts remain a viable bridge. Never ask tenants to share Selar passwords or scrape private order pages.

## Revenue and subscription business model — HYPOTHESIS ONLY

Propose plan experiments, not activated billing:

| Plan | Example monthly test price (NGN; not a quoted offer) | Proposed value |
|---|---:|---|
| Explore | Free, fixed demo only | Understand business goals and preview recommended rules |
| Starter | ₦9,900 | One workspace, recommended recipes and assisted performance scorecards |
| Growth | ₦29,900 | More workflows and approvals, cohort/product analysis, richer measurement |
| Team | ₦79,900 | Multiple permissioned team workspaces, governance and custom integrations after security approval |

**No actual subscription, charge, entitlement or connector is enabled by this source PR.** These prices require real customer willingness-to-pay interviews, cost-of-service forecasts and provider licensing verification. Avoid bundling paid connectors invisibly. Track gross margin for MetaAutomate itself (fees less compute, communications, payment, hosting and support), onboarding effort and monthly retention, not only subscription receipts.

**Business break-even:** if *hypothetically* one garment yields ₦9,000 contribution after variable costs, a ₦9,900 monthly SaaS fee requires at least **two genuinely incremental** such sales, before advertising and further overhead. At ₦6,000 contribution per training enrolment, the same plan also needs two incremental enrolments. These are illustrations, not forecasts or evidence of causation.

## Evidence and scientific pilot

The fixed invented scenarios exercise exactly two workspaces, separate product pools and three-channel logic: marketing opt-in, native-provider suppression and drafted follow-ups. Metrics track **fictional completed orders, revenue, variable costs, contribution, marketing spend, modeled contribution after marketing spend, goal gap and fictional repeat orders**. All event-to-revenue causal attribution is explicitly zero/unproven. Do not infer a conversion rate without a reliable visit-to-order denominator or report full net profit without fixed cost information.

Future authorized pilot success criteria: customer setup time, number of *approved and delivered* legitimate workflows, opt-out compliance, true incrementality via matched controls when possible, repeat order/learner retention, contribution after all incremental costs, cost per conversion, support effort, consent/complaint rate and trial-to-paid subscription retention. Only promote source evidence after an independent lifecycle proposal.

## Developer proof (standard library; no subscriptions)

```bash
python scripts/verify_synthetic_growth_autopilot.py \
  --report artifacts/validation/p2-03h-growth-autopilot-synthetic.json
python -m pytest -q tests/test_synthetic_growth_autopilot.py
```

**Hard boundary:** no live commerce integration, customer records, payment processor, messaging, social publishing, provider API, data warehouse, subscription enforcement, database changes, active API route, infrastructure provisioning, real tenant authorization, or automatic operations. The 19-entry capability registry, accepted LCE-0001, 33 disabled catalog IDs, and seven-sector contract remain unchanged. Foundation **3/9 verified**, F04–F09 blocked; Phases 02–03 live execution **NO-GO**. This draft PR is for source review only.
