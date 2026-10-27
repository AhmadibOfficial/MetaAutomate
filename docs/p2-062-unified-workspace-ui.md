# P2-062 — Unified Workspace graphical interface (source-only)

**Status:** Draft / review-only / no merge or deployment authorization.
**Dependency:** Stacked on Stage 01 F06 draft #131; itself dependent on #122 → #121 → #120 → #119. Foundation 3/9 historically verified; operational NO-GO.

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
