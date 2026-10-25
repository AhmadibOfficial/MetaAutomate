# P2-060e — Inventory-input quality and explainable campaign decisions

## Scope and product outcome

Prior P2-060 browser, keyboard, saved-evidence and responsive-reflow
acceptance passed **on the repository owner's Kali machine**. This milestone
addresses a material ambiguity: in the legacy five-column CSV, a
`weekly_sales=0` numeric value does **not** prove that zero sales occurred
during a complete measurement window.

The new opt-in import records whether the owner says stock was counted and
whether the weekly sales record is complete. **A declaration is not an
independently verified inventory fact.** MetaAutomate uses deterministic,
reviewable rules; no neural model, authenticated ERP integration, demand
forecasting or revenue/publishing claim is made here.

## Data contract

Legacy exact header (still works):

```csv
sku,name,stock,weekly_sales,unit_price_kobo
CAP-01,Branded Cap,18,0,850000
```

Quality-aware exact header (optional):

```csv
sku,name,stock,weekly_sales,unit_price_kobo,stock_count_status,sales_coverage_status
CAP-01,Branded Cap,18,0,850000,unknown,unknown
FAB-02,Classic Kaftan,24,3,3500000,counted,complete
SHOE-03,Low Stock Shoes,1,5,1400000,unknown,partial
```

Allowed literal statuses:
- `stock_count_status`: `counted`, `unknown`
- `sales_coverage_status`: `complete`, `partial`, `unknown`

These statuses are provided by the user, not attested by a connected data
provider. Fields cannot be silently reordered or partially supplied.
Malformed fields, extra columns and unsafe values fail closed. Existing
limits of 400 records / 128 KB, integer kobo prices, and text/CSV injection
safeguards remain.

## Business decision semantics

- An enhanced row classified as a promotion candidate is **held** when
  either stock is not `counted` or weekly sales coverage is not
  `complete`. Holds have explicit human-readable reasons and cannot be
  bypassed through `makeCampaign()` even if invoked directly.
- A row declaring `counted,complete` may become a rule-based campaign
  draft candidate, but its quantities and statuses are still entirely
  **user-supplied and unverified**. They do not establish actual demand.
- Low-stock and sold-out items are never promoted, regardless of the new
  statuses.
- Legacy five-column rows retain the previous provisional rule-based
  workflow, but display `LEGACY_UNATTESTED` warnings. Existing test fixture
  acceptance, prior user exports and published draft claims are not
  retroactively described as verified.
- Summary counts distinguish promotion candidates, held candidates and
  legacy rows. The original per-item stock/prioritization rules remain.

## New explicit, local decision-trace export

After import, a user may download an `INVENTORY_DECISION_TRACE` JSON
containing each supplied row, the underlying stock signal, the final
allow/hold decision, input-quality issues and the declaration basis. It
is marked `USER_SUPPLIED_UNVERIFIED` and includes explicit
`inventoryIndependentlyVerified:false`,
`financialPerformanceVerified:false`, and `publishPerformed:false`
safeguards. It contains business inventory data, so do **not** upload it
to public GitHub issues, PRs, logs or cloud evidence buckets. Download
only occurs upon a deliberate local click.

When a campaign's evidence JSON is exported, it also includes optional
`inputQuality` metadata; the existing schema 1 fields are not removed.
Each new CSV import resets the transient audit, and preparing a different
campaign retains only the current import event before starting a new
draft history. Old approvals/reviews are not attributed to later drafts.
The prior 12 archived P2-060b artifacts retain their historical hashes.

## Kali acceptance (new branch only)

```bash
cd ~/MetaAutomate
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
  tests/test_p2_060_inventory_quality.py \
  tests/test_p2_060_reflow.py \
  tests/test_p2_060_accessibility.py \
  tests/test_p2_060_campaign_workbench.py \
  tests/test_p2_060_browser_harness.py \
  tests/test_p2_060_evidence_review.py

PLAYWRIGHT_BROWSERS_PATH="$HOME/.cache/metautomate-playwright-browsers" \
  "$HOME/.local/share/metautomate-browser-venv/bin/python" \
  scripts/verify_campaign_inventory_quality.py

git status --short --branch
```

Expect **only on an actual successful Chromium run**:
`DEVELOPER_LOCAL_INVENTORY_QUALITY_PASS`. Browser test uses three
viewports (1440/390/320), fabricated stock, locally downloaded trace
read back by Playwright and eliminated on browser context teardown.
No outside-origin requests are authorized. If a test fails, preserve the
failure rather than loosening quality rules to manufacture a PASS.

## Limits and release hold

- No proof that stock was counted or sales records are truly complete.
- No time-window provenance, last-stock-take timestamp, demand model,
  sale attribution, profitability analysis or verified marketing ROI.
- No actual 200% browser zoom certification, manual screen-reader,
  visual contrast/overlap, independent AppSec, independent CI or client data.
- No production account authorization, AI media generation, social
  publication, cloud deploy, migration, branch merge or QDB submission.

P2-060e remains a **draft stacked on #126** (and preceding drafts).
Foundation **3/9 verified** and production **NO-GO** are unchanged.
