# P2-060g — Evidence provenance and stock reconciliation

## Scope

MetaAutomate's campaign workbench now includes a **separate, browser-only,
self-declared inventory reconciliation** capability. It compares two dated
stock snapshots against an explicit movement ledger and distinguishes
arithmetically consistent reports from conflicting, incomplete or
non-comparable evidence.

This is **not** a provider-authenticated accounting system. A SHA-256 digest
does not establish original data provenance. No network integrations,
commercial sales, model inference, social publication, database mutations or
production accounts are enabled.

Parent P2-060f passed owner-local Kali validation at
`a7d3b263d9614c2be9598ee0a879cd7fd64238ca`:
**55 pytest tests in 7.51s** and
`DEVELOPER_LOCAL_TEMPORAL_EVIDENCE_PASS`.
This new P2-060g source is **not yet accepted** at its new HEAD.

## Inputs

1. **Previous dated inventory CSV**: exact ten-column P2-060f inventory
   format, including counted/coverage states and valid stock observation
   and seven-day sales period dates.
2. **Current dated inventory CSV**: same exact schema. Matching SKU means
   the same product only provisionally; a changed product name is treated as\n   not comparable and held for investigation.
3. **Movement CSV**: exact header

```csv
sku,period_start,period_end,received_units,customer_returns_units,adjustment_units,sold_units
CAP-01,2026-10-19,2026-10-25,4,1,-1,3
```

Movement dates must cover exactly the days **after** the previous count
through the current observation. For the example, the previous observation
is 2026-10-18 and the current observation is 2026-10-25.

Received units, customer returns and sold units are nonnegative integers;
adjustments are signed integers. There is no automatically inferred receipt,
sale or correction, and ledger SKUs not present in both snapshots fail closed.
Duplicate SKUs are disallowed (case-insensitive). The existing bounded
CSV limits and injection defense remain; the ledger also has explicit bounds.

The assessment date is an explicitly selected UTC calendar day (defaulting
to the current UTC day) and is included in the export. Current stock
observations more than seven days old or in the future, or stock observation
spans outside 1–90 days, are held as not comparable.

## Calculation

For a sufficiently aligned SKU:

```text
expected_current = previous_stock
                 + received_units
                 + customer_returns_units
                 + adjustment_units
                 - sold_units

difference_units = declared_current_stock - expected_current
```

No assumption of genuine cash sales or inventory ownership is made.
A zero difference only means **the provided integers agree arithmetically**.

Statuses are mutually exclusive:

- `DECLARED_ARITHMETIC_MATCH`: expected stock equals declared current
  count AND the current weekly sales count agrees with ledger sold units
  **only when** the sales window aligns exactly with a seven-day ledger
  window and coverage is self-declared complete. All source values remain
  `USER_SUPPLIED_UNVERIFIED`.
- `STOCK_ARITHMETIC_CONFLICT`: observed stock differs from calculated
  stock (or movements imply negative expected stock). May coexist with
  a sales issue in its issue list.
- `SALES_COUNT_CONFLICT`: same-seven-day-comparable weekly sales disagree
  with ledger sold units, even when stock arithmetic aligns.
- `ARITHMETIC_ONLY_SALES_NOT_COMPARABLE`: stock integers align but
  sales periods/coverage do not. **Not** a verified sales agreement.
- `INPUTS_NOT_COMPARABLE`: stale, future, out-of-order, too-long interval,
  uncertain stock counts or movement-period misalignment. Arithmetic
  is withheld.
- `MISSING_MOVEMENT_LEDGER`: no movement record for an otherwise matching
  SKU; **do not infer zero movements**.
- `NEW_CURRENT_SKU`, `MISSING_CURRENT_SKU`: SKU exists in only one
  snapshot; no assumption that missing equals zero or "sold out".

The result also contains explicit issue text and the declared numbers
used in a computed expected stock value where comparison is valid.

## Report integrity vs. provenance

The browser constructs a deterministic, sorted-by-SKU JSON payload with
fixed field ordering and the chosen UTC assessment date. It computes
SHA-256 over **UTF-8 JSON of the payload, two-space indentation and one
final LF** and exports a wrapper with both payload and digest.

Re-importing the same values and UTC assessment date (even if CSV row
order changes) should reproduce the same payload and fingerprint.
The fingerprint is **not a digital signature, receipt, third-party
timestamp, validated data-source hash or proof that uploaded CSV records
are genuine**. The owner created both the report and fingerprint. The
report includes no fabricated revenue, profit, causal campaign lift or AI
recommendation.

The report and individual CSV inputs can include private inventory and
sales information: DO NOT attach them to public GitHub pull requests or
issues, analytics or a cloud service. The workflow uses no network and
downloads only on a deliberate user click.

## Developer-local acceptance (NOT YET RUN AT P2-060g HEAD)

On an unmodified local checkout of
`feature/p2-060g-snapshot-reconciliation`:

```bash
cd ~/MetaAutomate
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
  tests/test_p2_060_reconciliation.py \
  tests/test_p2_060_temporal_evidence.py \
  tests/test_p2_060_inventory_quality.py \
  tests/test_p2_060_reflow.py \
  tests/test_p2_060_accessibility.py \
  tests/test_p2_060_campaign_workbench.py \
  tests/test_p2_060_browser_harness.py \
  tests/test_p2_060_evidence_review.py

PLAYWRIGHT_BROWSERS_PATH="$HOME/.cache/metautomate-playwright-browsers" \
  "$HOME/.local/share/metautomate-browser-venv/bin/python" \
  scripts/verify_campaign_reconciliation.py

git status --short --branch
```

The current **source-only Python target is 63 tests**, one of which
invokes the 13 new offline Node.js domain test cases; the existing Node
inventory suite runs within its existing pytest entrypoint.

The real Chromium acceptance checks 1440, 390 and 320 CSS px, downloads
the synthetic report privately, recomputes the SHA-256 over the canonical
payload, verifies stock and sales contradictions, missing SKUs, disabling
downloads after edits, zero console errors and zero external browser
requests. Its success marker is **only**
`DEVELOPER_LOCAL_RECONCILIATION_PASS` after actual execution.

**No pass may be inferred from code existing in GitHub.** The browser's
real behavior and exact report fingerprint require running on the owner's
Kali development machine before developer-local acceptance is recorded.

## Production / security boundaries

No change to the existing P2-060b–f source-evidence archives or source
history, social approval and publishing pathways, real user accounts,
database tables, external systems, GitHub Actions configuration, secrets or
cloud services.

Independent CI, AppSec, actual 200% zoom, manual screen reader/visual
review, business-data source authentication, inventory reconciliation
audits and real customer acceptance are pending. Foundation remains
**3/9 verified**, operations and production **NO-GO**, and the new PR
must stay **draft stacked on #128** without merges or deployments.
