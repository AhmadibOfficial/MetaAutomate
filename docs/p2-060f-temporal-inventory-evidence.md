# P2-060f — Dated inventory snapshots and seven-day sales-period validation

## Goal

P2-060e passed owner-local Kali verification: **48 Python tests passed**
and Playwright full Chromium reported **DEVELOPER_LOCAL_INVENTORY_QUALITY_PASS**
at exact commit `7cae50436af1af5af14a982c16d34eb9d34439d4`.

P2-060f improves the **interpretability and recency** of user-supplied
inventory without claiming real provider integrations, audited data,
AI-driven predictions, sales attribution or independently verified outcomes.
It adds an optional stricter third CSV schema while retaining BOTH existing
five- and seven-column formats unchanged.

## Three exact import formats

**Legacy, 5 columns:** `sku,name,stock,weekly_sales,unit_price_kobo`.
Accepted with `LEGACY_UNATTESTED` warnings. No dates inferred.

**Quality, 7 columns:** adds `stock_count_status,sales_coverage_status`.
Accepted with `SELF_DECLARED` warnings and no dates inferred.
`counted,complete` retains provisional candidate eligibility, and incomplete
count/coverage is held as in P2-060e.

**Dated, 10 columns:** adds `stock_observed_on,sales_period_start,sales_period_end`
to the exact 7-column header. Date format is exactly **YYYY-MM-DD**, UTC
calendar dates. Values must be real dates within 2000–2099. Order cannot
change, partial columns cannot silently parse, duplicate SKU and CSV injection
defenses remain.

Example **synthetic** dated inventory:

```csv
sku,name,stock,weekly_sales,unit_price_kobo,stock_count_status,sales_coverage_status,stock_observed_on,sales_period_start,sales_period_end
CAP-01,Branded Cap,18,0,850000,counted,complete,2026-10-25,2026-10-19,2026-10-25
FAB-02,Classic Kaftan,24,3,3500000,unknown,partial,2026-10-25,2026-10-19,2026-10-25
```

These are date **declarations**, not cryptographic signatures, source-system
receipts, GPS or authenticated timestamps. Even a fully populated row is
`USER_SUPPLIED_UNVERIFIED`.

## Decisions

Dated, otherwise promotable items are held if any:
- Stock or weekly-sales completeness declarations are insufficient.
- Stock observation date is in the future or **more than seven calendar
  days before the UTC assessment date**.
- Sales period does not contain **exactly seven inclusive calendar days**
  (end - start must be six days).
- Sales period ends in the future or **more than seven days ago**.
- Data is passed directly to the engine with incomplete dated properties:
  it cannot bypass the hold by avoiding CSV parsing.

The original conservative exclusion of sold-out/low-stock products remains.
No model estimates customer demand, profit, campaign lift, or future sales.
Decisions are **rules**, not trained AI inference. All date checks are in UTC,
so date boundaries may differ from Nigerian/local business day boundaries.

`analyze(records, referenceDate)` allows a deterministic explicit UTC
assessment date for reproducible unit tests and backtesting; UI uses the
current UTC day. The engine independently rechecks current freshness when a
campaign draft is created, so stale items are not permitted merely because a
caller passed a historical date to a prior analysis. The same gate also holds directly submitted dated fields when either quality-status declaration is missing.

## Evidence and user interface

- The UI displays the UTC reference date and the counts of dated/undated rows.
- The owner-downloaded inventory decision trace retains the same schema 1
  shape and classification, and now additionally includes as-of UTC date,
  dates per row, observed age information and the specific reasons for
  holding a stale or inconsistent candidate.
- Campaign evidence adds optional inputQuality dates and as-of information.
  Historical P2-060b artifacts are not modified, rewritten or reclassified.
- The example CSV is generated locally with the browser's current UTC date
  and an inclusive last-seven-day synthetic weekly-sales window.

**Privacy:** This export includes product inventory and business figures.
It must stay private and is generated only by explicit local download.
Never attach customer/product data to public GitHub issue or PR evidence.

## Exact-head Kali tests (not yet executed on this new branch)

```bash
cd ~/MetaAutomate
git status --short --branch
git fetch origin
git switch --track origin/feature/p2-060f-temporal-inventory-evidence

PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
  tests/test_p2_060_temporal_evidence.py \
  tests/test_p2_060_inventory_quality.py \
  tests/test_p2_060_reflow.py \
  tests/test_p2_060_accessibility.py \
  tests/test_p2_060_campaign_workbench.py \
  tests/test_p2_060_browser_harness.py \
  tests/test_p2_060_evidence_review.py

PLAYWRIGHT_BROWSERS_PATH="$HOME/.cache/metautomate-playwright-browsers" \
  "$HOME/.local/share/metautomate-browser-venv/bin/python" \
  scripts/verify_campaign_temporal_evidence.py

git status --short --branch
```

Expected pytest cases: **55**, including a nested Node decision suite which
now contains nine additional date-related cases. The real Chromium gate
checks 1440/390/320 CSS px, held and permitted dated items, the decision
trace, campaign evidence and unchanged legacy fallback. It prints
`DEVELOPER_LOCAL_TEMPORAL_EVIDENCE_PASS` only after a real successful run.
No run is claimed from code inspection alone.

## Independent gates and operational hold

The dated data is NOT independently authenticated. Temporal completeness
does not prove genuine sales, accurate stock or causal marketing results.
Human visual and native 200% browser zoom testing, screen-reader evaluation,
independent CI (GitHub Actions billing blocked), AppSec, security/provenance
review and real-customer validation remain pending.

P2-060f must stay a **draft stacked on #127** and earlier drafts.
Foundation **3/9 verified**, Phase 02/03 and production **NO-GO**.
No merge, external publishing, live inference, database migration, cloud
deployment, customer operations, paid resources or QDB submission.

## Preserve analysis when editing campaign settings

The browser now distinguishes the currently imported inventory analysis
from the selected campaign draft. Changing brand or channel revokes the
existing draft approval, copies and exports **without erasing** the UTC
assessment date, held item reasons or private inventory decision-trace
download. This prevents the interface from hiding quality caveats while
retaining the same underlying CSV. A dedicated browser scenario and
source regression test were added. The branch and all new checks remain
unverified until the exact-head Kali run.
