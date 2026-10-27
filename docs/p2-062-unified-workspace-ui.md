# P2-062 — Unified Workspace graphical interface (source-only)

**Status:** Draft / review-only / no merge or deployment authorization.
**Dependency:** Stacked on Stage 01 F06 draft #131; itself dependent on #122 → #121 → #120 → #119. Foundation 3/9 historically verified; operational NO-GO.

## P2-062b — 20-second first-use redesign (27 October 2026)
The opening screen now answers just three questions without showing the
technical roadmap, release metrics or a catalog of nine modules:
1. **What does this do?** "Sell smarter with the stock you have."
2. **What should I do first?** "Start with my inventory" or "Try an example instead."
3. **What happens?** Add products → see potential stock opportunities → write a post.

Main navigation is **Home / My inventory / Create a post**. Reports, tools
and project status remain accessible under a visually secondary "More" section.
Content uses everyday language, a light reading surface and compact cards,
while preserving MetaAutomate's navy, electric blue, silver and gold palette.

The one-click example processes **three explicitly fictional records** using
the existing stock engine. Display and downloaded receipts label the data
\`SYNTHETIC_EXAMPLE_UNVERIFIED\`, never customer evidence or traction. A new
file selection or session reset invalidates stale imports and prior approvals.

### Verified in this authoring run
- Committed GitHub source readback, JavaScript compilation, unique HTML
  element IDs, complete JS-to-DOM target mapping, and no external request
  primitives: **PASS** (developer-local source checks).
- In-memory mock-DOM interaction with the actual committed campaign engine:
  sample 3 products / 2 candidates, draft creation, review-gated download,
  edit-triggered revocation and local evidence download: **PASS**.
- Updated source-level pytest and Chromium fixture for the new first-use
  walkthrough, including explicitly synthetic JSON receipts: **committed,
  not executed at exact branch HEAD**.

Real browser viewport screenshots, keyboard/screen-reader checks,
full pytest, Chromium acceptance, GitHub Actions and independent security
review are **still pending**. No release approval is implied.

## Delivered
- New responsive workspace dashboard with navigation for overview, inventory, campaign studio, evidence, existing modules and Qatar START readiness. Skip link, labels, keyboard-operable controls, focus styles, mobile sidebar and reduced-motion treatment.
- Reuses the actual P2-060 MetaCampaign engine rather than recreating stock logic. Fatal UTF-8 decoding; existing 128 KB/400-row bounds and CSV security checks. User-declared product CSV stays in browser memory.
- Inventory table, counts, conservative stock opportunities, sample CSV download and local JSON assessment export. Choosing a new file invalidates previous results and approvals.
- Editable campaign drafts created from eligible stock. Copy and text export require explicit internal review; editing or changing inputs revokes approval.
- In-memory event list and JSON receipt expressly declaring no independent source authentication, revenue verification, provider publishing or signed attestation. Local browser clock is untrusted.
- Module search links to existing pages; private encrypted storage, AI operations and future modules are labelled gated/planned and are NOT made available to public users.
- Alignment with ten-stage roadmap: Stage 01 security first, Stage 02 Inventory-to-Growth MVP, Stage 03 Qatar buyer research in parallel. No subscription, paywall, checkout, or billing features.

## Source files
- apps/site/workspace/index.html
- apps/site/assets/unified-workspace.css
- apps/site/assets/unified-workspace.js
- apps/site/assets/campaign-engine.js — existing engine reused, unchanged
- tests/test_p2_062_unified_workspace_ui.py
- scripts/verify_unified_workspace_browser.py
- apps/site/index.html — labelled navigation link on draft only

## Acceptance — trusted clean exact-head checkout
Run the commands separately:

    PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_p2_062_unified_workspace_ui.py
    node --check apps/site/assets/unified-workspace.js
    python3 scripts/verify_unified_workspace_browser.py

The browser harness requires previously installed, approved Playwright/Chromium and does not install packages. If explicitly choosing an installed Chromium binary, set MAT_CHROMIUM_EXECUTABLE to that path. Optional proof artifacts use --output-dir with a new private path outside the repository. The harness binds 127.0.0.1 on an ephemeral port, allows exactly five static assets, blocks off-origin traffic, uses fake inventory, and checks desktop/mobile layout, downloads, approval invalidation, navigation and provenance flags.

## Limits
This is a functional **browser-local GUI** with links to existing tools; it is not a complete operational or authenticated SaaS backend. It does not integrate the protected apps/web data vault, execute real AI or social operations, retain/upload commercial business information, verify revenue or invent customers, or connect to QDB/F6S. Access to the public preview is not an authentication gate; do not use sensitive records.

## Release gates remain outstanding
- Exact-head source tests, real Chromium test and independently witnessed browser acceptance
- Independent security/accessibility review and regression review
- Foundation F04–F09, especially real OIDC/MFA and isolated PostgreSQL acceptance
- Human review of stacked drafts plus separate explicit release approval
- Qatar buyer interviews, genuine pilot outcomes, validated business-model assumptions without billing features, team/legal evidence, founder-reviewed financial plan and funding narrative
- CI runners available and actual green checks; current account billing/spending-limit block is not a test pass

**Operational NO-GO, no merge/deploy/migration/live data/social or AI/billing/spending/funding submission.**
