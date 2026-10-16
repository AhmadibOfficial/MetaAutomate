# P2-03n — Business Decision Intelligence Workspace (source-only)

## Purpose
Turn P2-03m synthetic Business Value Intelligence evidence into explainable, useful business decisions without claiming income generation, net profit, causation, or production readiness.

## Read-only interface contract
`decision_dashboard(report, workspace)` exposes two 30-day financial snapshots, gross sales, identified costs, modeled contribution, changes, workflow review counts, and evidence-ranked opportunities. All financial amounts are **DEMO_CREDITS_NOT_USD**, never real cash. Opportunity rankings inherit P2-03m's HIGH/MEDIUM/LOW priority and show `SYNTHETIC_ONLY` evidence quality. No actual sales or validated incremental growth is implied.

`simulate_decision` takes three integer basis-point sensitivities, each in [-5000, 5000]: unit price, order count, and variable unit cost. It applies price and order assumptions to gross sales and order and unit-cost assumptions to variable costs. All other identified costs stay constant. Arithmetic is descriptive and hypothetical, **not an earnings forecast**; unobserved overhead, returns response, price elasticity and taxes are not predicted.

`create_manual_action`, `transition_manual_action` and `verify_outcome` offer an ephemeral illustrative task lifecycle. The only transitions are PROPOSED → APPROVED_FOR_MANUAL_REVIEW → IN_PROGRESS → COMPLETED, with optional DISMISSED until completion. There is no persistence, tenant authentication, provider integration, real human identity/approval verification or external execution. Completing a task never establishes a causal effect. The outcome function only repeats the previously modeled period difference and explicitly returns no effect estimate.

## Evidence & safety
- Inputs must validate against P2-03m source evidence and tenant-scoped synthetic examples; unknown tenants, invalid adjustments and mutated reports fail closed.
- No customer records, card requirements, subscriptions, external messages, background agents, scheduled actions, provider API calls, payment operations, write endpoints or deployments.
- To run the isolated tests (after P2-03m branch dependency is present):
  `python -m pytest -q tests/test_synthetic_business_decisions.py`
- This branch is based on **draft PR #75** because P2-03n consumes its not-yet-merged module. Merge P2-03m first, then retarget and revalidate P2-03n; do not merge this dependent work independently into main without a successful CI run.
- This is a **backend decision-contract foundation, not a completed browser UI**. A polished mobile/desktop dashboard should be added as a separate source-only reviewable implementation, with strong accessibility tests and a clear demonstration-data watermark.

## Gate
DRAFT / SOURCE ONLY / NO LIVE EXECUTION. Foundation Phase 01 3/9 verified; operational Phases 02–03 NO-GO. No website release, database migration, external financial connection, customer activation or subscription purchase is authorized.
