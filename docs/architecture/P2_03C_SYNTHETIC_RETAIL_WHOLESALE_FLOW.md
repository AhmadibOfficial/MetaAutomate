# P2-03c — Cross-functional retail + wholesale synthetic workflow

**Status: source-only, zero execution authority.** Phase 01 Foundation remains
**3/9 verified — NO-GO**; Phase 02 operational NO-GO; Phase 03 real execution
NO-GO. This is not a customer pilot, finance integration or production ERP.

## Business problem

Stock visibility, orders, customer follow-ups and financial decisions often
exist in separate systems. The **retail and wholesale** synthetic demonstration
models an integrated, reviewable decision chain without accessing real business
records or claiming a measured return on investment.

## Sequence and invariants

1. **Understand/validate:** Read one fixed, committed
   `SYNTHETIC_DEMO_ONLY` fixture containing two clearly identified sectors.
   Reject unexpected fields, duplicate keys, booleans used as quantities,
   non-finite numbers, real currency symbols, real contact fields, excessive
   input, unknown stock IDs, duplicates and unknown sectors.
2. **Inventory preview:** Check cumulative stock feasibility for all draft
   orders within a sector. Fail the *whole preview* if any proposal oversells.
   Calculate the **projected stock only if later approved**, with thresholds,
   reorder indicators and suggested replenishment quantities. **No stock change.**
3. **Sales preview:** Build deterministic **quotations**, not submitted
   orders or legally issued invoices. Use fixed demonstration prices and whole
   `DEMO_CREDITS` units (not NGN or live money) to avoid floating-point drift.
4. **Customer follow-up preview:** Draft a retail confirmation prompt or
   wholesale payment-terms review; **no contact details, messaging or CRM write**.
5. **Finance preview:** Propose a balanced *illustrative* accounts-receivable
   debit / sales-revenue credit pair. It is **not posted, billed, issued,
   settled, bank reconciled, or evidence of earned revenue**.
6. **Verify:** Every sales draft, follow-up, finance preview and stage trace
   shares one deterministic synthetic order ID. All proposal effects are
   marked unexecuted, with explicit human-review gates and SHA-256
   provenance of the fixed fixture/report.

Each demonstration sector is independently simulated. Orders cannot refer to
another sector's stock; duplicate order IDs across sectors are denied.
No tenant ID is accepted from inputs: this is **not** a multitenant API and
no claim of tenant isolation is made. The reusable design is a contract
example, not a provider integration or an authenticated sandbox endpoint.

## Synthetic cases

| Sector | Example stock | Draft customers | Demonstrates |
|---|---|---|---|
| Retail | Tea packs and carry bags | Two invented customers | A reorder alert after proposed allocations; unsent order confirmations; unposted quotation journals |
| Wholesale | Grain sacks and packaging | Two invented customers | Multiple larger draft allocations; grain replenishment proposal; unissued wholesale quote and payment-terms follow-up |

The data and values are invented. No revenue or cost savings are measured.
Stock is not decremented; there is no purchase order, actual inventory
reservation, CRM contact, tax calculation, cost-of-goods accounting, payment,
real invoice, or customer-facing communication. A balanced hypothetical
journal does **not** imply a compliant accounting integration.

## Local developer use

Uses the Python standard library, a fixed fixture path and no new
subscription. Requires a checkout with Python 3.12 and pytest for tests.

```bash
PYTHONPATH=apps/api python scripts/verify_cross_functional_synthetic.py
PYTHONPATH=apps/api python scripts/verify_cross_functional_synthetic.py --sector retail \
  --report artifacts/validation/retail-workflow-synthetic.json
PYTHONPATH=apps/api python scripts/verify_cross_functional_synthetic.py --sector wholesale
PYTHONPATH=apps/api python -m pytest -q tests/test_cross_functional_synthetic.py
```

Reports contain **only fabricated sample labels and numbers**; treat them as
source validation artifacts, not financial statements or production evidence.
The CLI accepts no arbitrary data-source path, connection details or
customer identity. This module is **not included as a FastAPI route** and
has no network, database, payment, mail or external-provider imports.

## Existing contracts and governance

Cross-functional reasoning relates to draft registry IDs:
`BIZ-011` (inventory & operations), `BIZ-004` (sales outreach & follow-up)
and `BIZ-012` (financial operations), **all still DRAFT / disabled**.
The existing deny-only domain contracts, P2-03a synthetic inventory route and
P2-03b local CSV/JSON preview are not modified, expanded or activated.
The 19-entry engineering Capability Registry and lifecycle event history
remain unchanged; new source files **do not automatically justify a maturity
change**. Any change to the authoritative registry needs a separate
evidence-backed lifecycle proposal and approved source event.

## Adapting beyond retail + wholesale

Future *design-only* mappings can reinterpret the same review stages:
- Transportation: vehicle/capacity availability → trip quotation → rider
  communication proposal → unposted transport billing.
- Logistics: slot/capacity preview → shipment quote → milestone follow-up
  → finance reconciliation proposal.
- Tourism: inventory-like room/tour capacity → reservation quote → guest
  enquiry draft → unissued settlement.
- Education: seat/capacity availability → enrolment quote → guardian/learner
  support → fee statement proposal.
- Healthcare: administrative capacity/stock → appointment/service estimate
  → consent-based communication plan → administrative finance proposal.
  **No patient records, medical advice or clinical operations.**

Each new sector needs its own bounded domain contracts, privacy and regulatory
review, consent model, independent security tests, human approval and pilot
evidence before considering operational connectivity.

## Non-negotiable release hold

Foundation F04–F09 remain blocked (required checks, isolated staging, real
OIDC/MFA and private ingress, independent recovery, acceptance, consented
pilot evidence). No paid subscription, DigitalOcean/Render change, Kali
migration, API activation, product federation, secret, business record or
external customer action is part of P2-03c.
