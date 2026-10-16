# MetaAutomate Business Autopilot — synthetic investor demonstration

This source increment turns **assess → plan → approve → simulate → verify** into a reproducible local demonstration. It is a proposed first commercial product, not a deployed customer operating system. It reuses the Objective Workspace's pure `build_preview`, Operational Core `produce_report` and P2-03b `parse_synthetic_inventory_bytes` functions.

No website publication, backend deployment, subscription, new credential, database migration, customer-data import or operational execution is part of this change. Phase 01 remains **3/9, NO-GO** in the recorded evidence; Phase 02/03 live operations remain NO-GO. Existing default-disabled integration routes and every real capability's DRAFT/DENY/unbound state are unchanged. Other draft Phase 03 PRs are not merged or superseded by this demo.

## Run locally without Docker or a database

Use an isolated checkout containing this branch. To preserve an existing checkout's work, you can fetch the branch and create a separate worktree:

```bash
git fetch origin feat/business-autopilot-synthetic-demo-20261015
git worktree add ../metaautomate-autopilot-demo FETCH_HEAD
cd ../metaautomate-autopilot-demo
python3 -m venv .venv
.venv/bin/python -m pip install -r apps/api/requirements.txt
.venv/bin/python scripts/business_autopilot_demo.py serve
```

Open **http://127.0.0.1:8090** in a browser on the same computer. This is a different process and port from the authenticated Objective Workspace on 8000. It does not initialize or change that workspace. Stop with Ctrl+C. `--port` accepts only an unprivileged port; the host is always 127.0.0.1. Do not place it behind a reverse proxy or expose it publicly.

The only accepted scenario inputs are three committed identifiers. The browser cannot upload files, records, prompts, URLs, tenant IDs, credentials or reviewer identities. All records are deliberately invented. The demo uses a fixed fixture namespace, **not real multi-tenant storage or a real login**.

Run handles are unguessable, separate, memory-only and expire after 30 minutes. A handle is not a customer session or an authorization token for MetaAutomate. Restart removes the old run; reloading the page starts a fresh run; stopping the host loses every run. Nothing is stored in cookies, localStorage, sessionStorage or server-side files. Only clicking Download saves the generated JSON in the user's browser download location.

Dependencies require an initial download. Thereafter the demonstration and CLI replay use no external network, AI models, cloud resources or database. It is intentionally a deterministic product demonstration; do not describe it as live AI integration.

## A seven-minute walkthrough

| Time | Screen | What to demonstrate |
| --- | --- | --- |
| 0:00–1:00 | Scenario | Four invented inventory records. Two SKUs below threshold, 68 suggested units. No customer or government relationship implied. |
| 1:00–2:00 | Assess | Fifteen fixed invented ratings pass through the existing transparent maturity rubric. An inventory finding points back to its source checksum. |
| 2:00–3:15 | Plan | The existing Objective Workspace planner structures a draft proposal. Inspect exact quantities, dependencies, constraints and input-bound plan hash. |
| 3:15–4:15 | Approve | Explicitly approve only synthetic drafts, or reject. Approval cannot enable connectors, place orders, send email or move money. No reviewer identity is authenticated here. |
| 4:15–5:15 | Simulate | Two in-memory drafts, or one blocked draft. Inventory is unchanged. No purchase order or supplier contact occurs. |
| 5:15–7:00 | Verify | A fresh replay must match the entire report. Download sources, assumptions, results and chained audit receipts. Separate observed simulation results from financial estimates and unmeasured customer outcomes. |

Use the **One step blocked** scenario to show that a failed supplier check stays blocked, contributes no estimated time benefit, and requires human review. **Cost exceeds estimated benefit** keeps the negative estimate visible. A rejected plan cannot simulate or export a completion report.

## What the financial numbers mean

These are invented **per-run assumptions**, not Qatar market prices, a proposed customer price, actual runtime measurements or an exchange rate. QAR is an illustrative unit only. There is no extrapolation into annual revenue or customer ROI.

| Input / result | Standard | One step blocked | High delivery cost |
| --- | ---: | ---: | ---: |
| Drafts prepared in simulation | 2 | 1 | 2 |
| Blocked steps | 0 | 1 | 0 |
| Assumed manual / assisted minutes per prepared draft | 12 / 3 | 12 / 3 | 12 / 3 |
| Modelled capacity released | 18 min | 9 min | 18 min |
| Assumed hourly staff cost | QAR 60 | QAR 60 | QAR 60 |
| Illustrative capacity value | QAR 18 | QAR 9 | QAR 18 |
| Assumed delivery cost | QAR 10 | QAR 10 | QAR 50 |
| Net capacity value | QAR 8 | **−QAR 1** | **−QAR 32** |
| Verified real time, cash savings or recovered revenue | **Not measured** | **Not measured** | **Not measured** |

The invented QAR 2,905 inventory purchase amount is a proposed cost, never counted as a benefit. No stock is purchased. Blocked steps are excluded from the capacity estimate; delivery cost is still charged to that model. A matching replay can therefore verify an **incomplete preview** or a **negative estimated benefit**. Verification is not the same as meeting the objective or demonstrating profit.

## Reproduce and check evidence offline

```bash
.venv/bin/python scripts/business_autopilot_demo.py replay > /tmp/metaautomate-demo-evidence.json
.venv/bin/python scripts/business_autopilot_demo.py verify /tmp/metaautomate-demo-evidence.json
.venv/bin/python scripts/business_autopilot_demo.py replay --scenario partial_failure
.venv/bin/python scripts/business_autopilot_demo.py replay --scenario high_cost
PYTHONPATH=apps/api .venv/bin/python -m pytest -q tests/test_business_autopilot.py tests/test_business_autopilot_http.py
```

`replay` writes only to stdout; shell redirection in the example explicitly saves a local file. `verify` reads a bounded regular local file and returns nonzero on invalid or changed evidence. Duplicate JSON keys and non-finite numbers are rejected. Verification compares the complete artifact against a fresh deterministic reference, including current fixture hashes, plan, exact simulation approval, results, assumptions and event order. Recalculating an edited report's hashes does not make it match.

This is **reproducibility against the checked-out source**, not a digital signature, verified human approval, independent audit, measured customer benefit or production security acceptance. Anyone with the source can regenerate a matching report. Changing fixtures or engine behavior invalidates old reference comparisons; retain the exact source commit alongside evidence if you need to replay an earlier version.

Browser acceptance (includes a real download, desktop/mobile screenshots, keyboard rejection, blocked steps and negative estimated value):

```bash
.venv/bin/python -m pip install 'playwright>=1.55,<2'
.venv/bin/python -m playwright install chromium
.venv/bin/python scripts/verify_business_autopilot_browser.py
```

The browser test starts and stops its own loopback server. It creates only synthetic QA artifacts under `artifacts/business-autopilot/`. HTTP negative tests cover origin/Host/peer checks, proxy and client-authority rejection, body limits, stale handles, wrong stage and capacity bounds. Those are tests of this **local demo**, not a replacement for the authenticated workspace's tenant or operational acceptance tests.

## Product and investment work after the demo

1. Validate this specific problem through 15–20 structured SME interviews; record current process, frequency, loss/cost, integrations, decision maker and willingness to pay. These are proposed targets, not QDB requirements or completed traction.
2. Seek 3–5 credible written expressions of interest and an integration requirements list. Explore local partnerships without implying an existing government relationship.
3. Define a consented pilot baseline: task volume, manual time, error/stockout rate, observed collections if relevant, delivery/AI/support cost and attribution method. Avoid double-counting revenue and cash collections or treating staff capacity as cash savings.
4. Pass the existing independent security and operational gates before using customer data or enabling real actions. Real workflows require tenant-authenticated identities, narrowly scoped connectors, revocable action-specific approvals, privacy controls, audit, recovery and human acceptance. This demo provides none of those operational permissions.
5. Only then run tightly scoped pilots, ideally including one paid pilot. Record measured results and customer permission to use them in an investment case. Arabic/English localization, real integrations, pricing, Qatar hiring and financial projections follow validated demand and an approved operating plan.

Investor wording supported today: **“We can demonstrate a reproducible, controlled synthetic inventory workflow with transparent assumptions and evidence.”** Customer traction, production readiness, financial savings, government partnerships and funding approval remain unproven. The current increment is not a claim about funding eligibility or current program terms.
