# P2-03m — Business Value Intelligence

**Status:** Source-only development; no release authorization.

The business purpose is to help owners answer five questions without manufacturing
financial success: What happened to revenue? Which identified costs affected
contribution? How did a comparable period change? Which workflows reached
human review rather than actual customers? Which business questions deserve
attention next?

## Implemented

- Strictly validated, invented **30-day baseline and comparison** periods for
  Academy and Bespoke. All current source-order gross sales, variable costs,
  advertising costs, completed orders, and repeat-order counts must reconcile
  to the existing P2-03j source engine. No mismatched or real customer data.
- **Identified-cost waterfall:** gross sales less variable/direct costs,
  marketing spend, processing fees, fulfillment cost, software spending and
  refunds. Named *modeled contribution after identified costs*, not net
  profit, income generated, total profit, cash flow, ROI or a real statement.
  Rent, salaries, tax, overhead, returns processing and other unrecorded
  costs may exist; staff minutes are separate and not monetized.
- **Descriptive baseline comparisons:** absolute change, basis point change
  only when nonzero baseline exists, transparent undefined denominators,
  cost-mix movement, measured-in-scenario time differences and margin
  indicators. Comparable 30-day durations do not establish seasonality,
  matching cohorts or causation.
- **Workflow effectiveness:** states from the existing goal-specific engine:
  reviewable, deferred, provider/consent suppressed. Approved and delivered
  actions are zero. Actual conversion rate, attribution and incremental
  sales are explicitly unavailable.
- **Prioritized questions, not automatic promises:** contribution below
  target, rising cost ratios, lower sales, repeat-order observations,
  review efficiency and safeguarded customer contact. Every priority includes
  its evidence needed, a stable identifier, and a hard zero on validated
  causal benefit and automatic execution.
- **Integrity and safety:** exact input schema, bounded integer values,
  duplicate-field detection, workspace and period validation, all workspaces
  validated even when selecting one, reconciled source figures, and a
  deterministic SHA-256 evidence digest. This digest is not authenticated,
  signed or immutable.

### Example internal numbers (not USD, not public customer results)

| Illustrative workspace | Gross | Identified costs | Contribution | Target gap |
|---|---:|---:|---:|---:|
| Academy | 25,000 | 12,700 | 12,300 | 7,700 |
| Bespoke | 35,000 | 30,300 | 4,700 | 10,300 |

The comparison scenario intentionally includes a software-cost rise for the
apparel business to test cost leakage; it does not claim that MetaAutomate
caused or prevented any expense.

### Run

\`\`\`bash
python -m pytest -q tests/test_synthetic_growth_value_intelligence.py
python scripts/verify_synthetic_growth_value_intelligence.py \
  --report artifacts/validation/p2-03m-growth-value-source.json
\`\`\`

All values remain invented controlled engineering fixtures. The existing free
Growth Autopilot explorer stays as-is; the value intelligence report is NOT
displayed as actual income. Source-only PR review and CI are not a website
publication authorization.

## Independence from PR #74

P2-03m is intentionally based on the already-merged P2-03j goal engine and
does not require merging the separate draft review/audit PR #74. A subsequent
milestone can consume authenticated, verified approval/delivery evidence once
its security and operational controls exist; until then effectiveness metrics
remain explicitly unmeasured.

Foundation Phase 01: **3/9 verified**; gates F04–F09 still outstanding.
Phases 02–03 operational NO-GO. No real customer orders, live connectors,
migrations, tracking, subscriptions, billing, external messages, Render
deployments, customer activation, or provider API calls were enabled.
