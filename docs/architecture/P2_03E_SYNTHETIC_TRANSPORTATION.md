# P2-03e — Transportation bounded synthetic workflow

**Source-only, local fabricated-data experiment. NO-GO for all operations.**

This follows the merged seven-sector [Cross-Sector v1 contract](P2_03D_CROSS_SECTOR_WORKFLOW_CONTRACT.md) without revising its existing transportation profile. The contract remains **DESIGN_MAPPING_ONLY**. This isolated simulator provides new experimental code/test evidence, but does **not** automatically approve a contract v2 maturity change or grant permissions.

## Scope: fictional trip capacity → quote → customer update → finance → verify

The fixed repository fixture `contracts/domains/v1/fixtures/synthetic_transportation.json` contains two invented route labels and three invented parties. It has **no real destinations, schedules, operator identity, drivers, vehicle identifiers, phone numbers, contact details, addresses, location/GPS traces, passengers, banking details or transaction history**.

1. **Availability preview:** Validates bounded fictional seat capacity, existing fictional holds and cumulative draft requests. Overbooking rejects the entire fixture. Projected availability never reserves seats.
2. **Quotation draft:** Computes integer `DEMO_CREDITS` estimates without quoting an actual fare, issuing a ticket, scheduling trips or committing inventory.
3. **Customer follow-up draft:** Produces an unsent prompt to review the estimate and capacity; no contacts are held or messaged.
4. **Finance preview:** An unposted **illustrative** receivable debit and estimated transport credit pair, not earned revenue, an invoice, tax advice, accounting acceptance or a settled payment.
5. **Verification:** Deterministic draft IDs, five cross-sector stages, synthetic fixture checksum, output checksum, no side effects and explicit human-review requirement.

The code verifies both trips **before** honoring an optional demo trip filter, so filtering cannot conceal an invalid second trip. A failure anywhere produces no partial proposal. No route optimization, real dispatch or transport safety certification is claimed.

## Sample synthetic scenario

| Trip | Total fictional capacity | Existing fictional holds | Draft requested seats | Projected free if approved |
|---|---:|---:|---:|---:|
| DEMO-TRIP-A1 / Synthetic Route Alpha | 12 | 2 | 7 | 3 |
| DEMO-TRIP-B2 / Synthetic Route Beta | 8 | 1 | 2 | 5 |

Three unissued estimates total **15,900 DEMO_CREDITS**, which has no real-world financial value or claimed revenue. Exactly three customer updates remain unsent; three unposted finance illustrations stay in memory. No real-world resource is held or consumed.

## Offline source verification

Requires Python 3.12; `pytest` for tests. No new subscription or service:

```bash
python scripts/verify_synthetic_transportation.py \
  --report artifacts/validation/transportation-synthetic-demo.json
python scripts/verify_synthetic_transportation.py --trip DEMO-TRIP-A1
PYTHONPATH=apps/api python -m pytest -q tests/test_synthetic_transportation.py
```

The CLI accepts no file selection, customer ID, webhook, target domain or connector parameters. Reports contain only invented demo data and are CI artifacts—not evidence of real pilot acceptance.

## Security, scope and governance

The parser rejects extra keys, duplicate JSON keys, unknown trip references, repeated IDs, booleans as units, nonfinite or noninteger figures, overbooking, oversize fixtures, real route labels and customer details. The source includes no API router, network/SQL/email/payment dependencies, persistent storage or runtime connector. This is not a tenant-scoped service; no tenant isolation or production authentication claims are made.

Transport safety, provider identity, real trip scheduling, vehicle/fleet authorization, real-time location privacy, passenger consent, protected audit receipts, refund handling and independent acceptance remain unresolved. Any future sector prototype must use its own **approved v2 contract/lifecycle evidence**, strictly synthetic fixtures, negative authorization tests and an explicit owner review before access to anything real.

The existing 33 DRAFT capabilities, 19-entry engineering registry and lifecycle history remain unchanged. Foundation is **3/9 verified** with F04–F09 blocked, Phase 02 operational NO-GO, Phase 03 live-execution NO-GO. No migrations, Render/DigitalOcean deployments, model inference, external providers, transactions or subscriptions were enabled.
