# P2-03k — Free Pre-Launch Growth Autopilot Explorer

**Status: source-only development. No deployment or customer automation approval.**

## Product decision

MetaAutomate will offer a **free pre-launch exploration experience** so business owners can understand how Growth Autopilot supports decisions before paid plans are introduced. The initial experience is browser-based, no sign-in or payment card required, and uses example scenarios rather than anyone's actual customers or revenue. No email capture or account activation is added.

This is **not** a free live automation subscription, hosted private workspace or unrestricted trial. Any real customer free pilot needs its own verified staging, tenant separation, documented consent, recovery and operational approval. Foundation Phase 01 remains **3/9 verified**; Phases 02 and 03 operational **NO-GO**.

## Engineering contract

- `scripts/build_growth_workspace_contract.py` derives a deterministic public-safe browser contract from the source-tested P2-03j engine for 2 scenarios × 3 goals.
- `apps/site/automation/engine-snapshot.js` is a **generated, checked-in static asset**, loaded before the workspace script. No hosted API, requests, cookies, analytics or client records.
- Goal selector now changes real **engine-derived workflow decisions** in the page. Users can inspect review-needed actions, deferrals outside the chosen goal, provider-owned reminder suppression and missing-permission suppression.
- Goal target slider changes only the locally displayed illustration. Financial figures remain dollar-styled examples, not real USD revenue, profit or investment outcomes.
- The free access layer offers no payments, accounts, message delivery or work scheduling. Source-engine evidence is separated from public business-language copy.

## Reproducible tests

```bash
python scripts/build_growth_workspace_contract.py --check
python -m pytest -q tests/test_growth_workspace_engine_contract.py
```

The existing Playwright workflow tests desktop, 390px and 360px mobile layouts, keyboard navigation, goal changes and network isolation. The new engine-contract tests confirm both source/business scenarios, all goal decisions and unchanged suppressions.

**Constraints:** no Render deploy, migration, service connection, subscription, customer order processing, AI sending, publishing, secret or API endpoint. No registry maturity promotion; P2-03k remains source-only pending PR review and explicit merge/publication approvals.
