# P2-064 — MetaAutomate Interactive Universal Experience

**Status:** Source implemented, unmerged draft, not hosted or released. Owner-approved visual direction: problem-first interactive workspace with **no fixed industry limit**. Created 2026-10-28.

## Exact brand color system (source of truth: P2-058)
- Midnight Navy — \`#040D20\`: navigation, major headers, high-emphasis backgrounds.
- Electric Blue — \`#00A7ED\`: selected controls, action surfaces, accent and brand.
- Silver — \`#DCE6F1\`: cards, boundaries and quiet surfaces.
- Signature Gold — \`#EFB94F\`: focus ring, intentional accents and progression.
- Supporting deep navy \`#071932\` may create depth but is **not a fifth signature color**.
- Buttons on bright electric blue use dark navy text. UI includes visible keyboard focus, mobile layouts and \`prefers-reduced-motion\`; no external font/CDN.

## Built source files
- \`apps/site/index.html\`, \`assets/universal-landing.css\`, \`assets/universal-landing.js\`: marketing homepage now uses an accessible interactive goal selector with five capability families, changing descriptive content and an opening link to the relevant new workflow.
- \`apps/site/universal/index.html\`, \`assets/universal-workspace.css\`, \`assets/universal-workspace.js\`: new four-view business workspace:
  1. Home — choose among five **starting goals** (customers, operations, costs, automation, insights). Choose a reviewed **industry label** or custom sector. Create a client-side workflow.
  2. My Work — track up to twelve local plans, check their four proposed steps and separately record human review.
  3. Results — local activity counts, unverified source labels and an explicit empty slot for independently verified savings.
  4. Team & Settings — truthful descriptions of pending accounts, permissions, integrations, localization, and a working in-memory clear-session action.
- Industry choices compiled from source-reviewed \`contracts/domains/v2/domain-packs.v1.json\`: currently 22 **design-only** options, but the platform extension architecture itself does not impose a five-sector cap. Adding a new catalog pack requires an independent reviewed code update. **No pack is activated in the runtime**.
- Existing \`/workspace/\` and its functioning CSV stock-analysis/marketing-draft helper remain unchanged and linked from the new My Work page. Creative Studio and Project Chat links remain available in the marketing footer.
- User-entered descriptions are never rendered using HTML injection and are not transmitted, placed in URL queries, indexed, stored on disk or copied into exported activity metadata.
- All browser activity is transient/in-memory. Refresh clears it. No external execution, sales messaging, medical processing, financial transfer, cloud mutations, authentication or provider connection.

## Source verification conducted
- GitHub readback: scripts parse with a V8 JavaScript parser, HTML IDs and JS DOM references match; 22 compiled industry options match the reviewed design-only source catalog. Exact palette variables present.
- Local mock-DOM execution: 22 options, custom industry, goal selection, plan creation, four checklist steps, review-blocked until separate confirmation, plan review, accurate counters, JSON activity export and clear-session reset **PASS in mock DOM**.
- Marketing interaction mock: mouse and arrow-key goal selector, text switching, and matching local route link **PASS in mock DOM**.
- Added \`tests/test_p2_064_universal_interactive.py\` source contract acceptance.
- Added \`scripts/verify_universal_interactive_browser.py\` for local loopback Chromium desktop/mobile acceptance with no off-origin requests. **NOT RUN**, and no real Chromium pass is asserted.
- Updated previously incompatible homepage-specific tests in \`tests/test_p2_050_functional_site.py\`, \`tests/test_site_customer_clarity.py\` and \`tests/test_p2_062_unified_workspace_ui.py\`. Existing founder-review tool tests are retained.
- Full exact-branch pytest and independent security/accessibility evaluation **NOT RUN**; CI runners have previously been blocked by billing and cannot be treated as green.

## Launch for founder's safe local review

Do not overwrite the existing founder review worktree at \`~/MetaAutomate-Founder-Review\` or edit working copies with pending changes.

\`\`\`bash
cd "$HOME/MetaAutomate"
git fetch origin
git worktree list

REVIEW="$HOME/MetaAutomate-Universal-Review"
if [ -e "$REVIEW" ]; then
  printf 'STOP: %s already exists. Inspect it; do not overwrite.\n' "$REVIEW"
else
  git worktree add --detach "$REVIEW" \
    origin/feature/p2-064-interactive-universal-experience
  cd "$REVIEW"
  python3 scripts/serve_universal_founder_preview.py
fi
\`\`\`

The launcher selects an **available ephemeral port** on \`127.0.0.1\`, prints the Homepage and Workspace URLs, and serves only files from this worktree. It does not stop other services or touch Docker data. Exit with Ctrl+C.

Acceptance from that review directory:
\`\`\`bash
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider \
  tests/test_p2_064_universal_interactive.py \
  tests/test_p2_063_domain_packs.py \
  tests/test_p2_062_unified_workspace_ui.py \
  tests/test_site_customer_clarity.py \
  tests/test_p2_050_functional_site.py

node --check apps/site/assets/universal-workspace.js
node --check apps/site/assets/universal-landing.js
python3 scripts/verify_universal_interactive_browser.py
\`\`\`

A missing approved local Playwright/Chromium installation **blocks** the browser test; do not auto-download or waive acceptance.

## Public Render deployment

There is already a historical public MetaAutomate site at \`https://metaautomate.onrender.com/\`; this source PR is **not** proof the hosted site changed. The new public homepage and universal workspace are staged **only on the GitHub feature branch**.

To publish safely: founder visually approves the changed static pages, exact-head tests are accepted, site service/repository/branch are explicitly identified, and the owner confirms which Render workspace to use. A static-site publication must not open private Objective Workspace APIs, enable background jobs, purchase resources, permit real account data or bypass F04–F09 identity/security gates. If deployment controls are unavailable, report the blocker instead of claiming a live site.

**Keep PR #132 founder review and PR #133 universal architecture intact. No merge/deploy without owner review, no recruitment before founder approval, no restart of hourly automation, no hidden customer execution, and no unverified ROI claims.**
