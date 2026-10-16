# P2-03i Customer-Facing Automation Workspace: static, synthetic, review-only

**Status: DRAFT SOURCE DESIGN / NO DEPLOYMENT.** This page is a genuine interactive browser prototype, not a functioning public SaaS, private customer account or business automation execution layer.

## How to preview

From repository root:

    python3 -m http.server 18080 --bind 127.0.0.1 --directory apps/site

Open http://127.0.0.1:18080/automation/ in your browser.

Run offline checks:

    python -m pytest -q tests/test_growth_workspace_static.py
    python scripts/verify_growth_workspace_browser.py

The browser tests need Playwright and its Chromium runtime. GitHub CI prepares those dependencies in its existing test job and uploads desktop + mobile snapshots. Browser acceptance enforces that every HTTP request stays on the local test server.

## What a business owner can actually experience

The light-first interface reuses the approved MetaAutomate brand mark and offers:

1. **Choose a business example:** Academy (training) or Bespoke (fashion). Synthetic-only. The embedded fictional amounts and event IDs correspond to the checked-in P2-03h fixture in contracts/domains/v1/fixtures/synthetic_growth_autopilot.v1.json.
2. **Select a business goal:** contribution after marketing, repeat fictional orders or completed fictional purchases. Clear context rather than asking people to configure scripts.
3. **Understand contribution:** invented sales minus direct variable costs and advertising, plus the shortfall to an adjustable fictional contribution goal. The model deliberately does NOT claim net income, causal growth or guaranteed ROI.
4. **Inspect automation proposals:** exactly six fictional events per business; four review-only drafts and two suppressions—one checkout reminder handled by the native commerce provider and one missing opt-in. Inspecting a row shows the policy and does not approve/execute anything.
5. **Explore future setup:** three straightforward steps and disabled integration/billing concepts with explicit NO-GO text. Plan prices, where visible, are hypotheses and have no checkout controls.

The UI is real HTML/CSS/JS and supports mobile layouts, keyboard-operated tabs, visible focus, semantic labels, accessible status text and reduced motion. It stores nothing persistently. It makes zero external requests, has no login or new API endpoint, and cannot send, schedule, publish or bill. Source fixtures continue to use **DEMO_CREDITS**; the UI now displays monetary figures with **$ as a fictional dollar-style illustration**. This is not an actual USD transaction, exchange-rate conversion, forecast or real profit. Unavailable Starter ($9/month) and Growth ($29/month) tiers are proposed USD-denominated pricing research examples, **not a conversion** of previous ₦ hypotheses, and no billing is activated.

## Security, privacy and release boundaries

- The prototype is stateless and browser-only, with example data embedded in the page. It does not import actual Selar or Metricool accounts. Real business names are not represented as paying customers.
- No persistent profiles, tenant/session claims, real customer contact data, order/finance records, consent records, analytics collectors or third-party connections.
- The marketing site links to /automation/ **in the draft source branch only**. Render is configured with autoDeploy=no and the site must not be redeployed without a **separate explicit website publication approval**. Merge of source code is not website publication.
- The existing 19-entry capability registry, accepted lifecycle event LCE-0001, 33 DRAFT business catalog items and cross-sector business contract are not modified.
- Foundation Phase 01 remains 3/9, gates F04–F09 blocked. Phase 02 operational NO-GO and Phase 03 live-execution NO-GO. This prototype has no operational release rights.

## Later customer-readiness requirements

Before anyone can register, connect Selar or a social channel, allow automation, import consented orders or pay a subscription, the team must separately approve and verify: protected tenancy, account access and MFA, provider-specific least-privilege authorization, consent ledger/unsubscribe controls, idempotent messaging deduplication, quiet hours/rate limits, verifiable audit logs, billing/plan entitlements, privacy/deletion flows, signed release gates, monitoring/recovery, and an isolated staging acceptance test.

No subscription is purchased or charged in this milestone.
