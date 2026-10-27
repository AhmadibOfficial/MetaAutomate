# P2-062 — MetaAutomate focused five-sector interface

**Status:** Unmerged draft. No launch, financial application, customer onboarding, external AI/social operations or paid services authorized.

## Approved product experience
Public homepage: one clear value statement, exactly five industry solutions, three explainers, direct link to workspace. Removed excessive home landing sections/cards from the draft homepage, **without deleting historical assets, existing product modules or other application source**.

Workspace: **Home**, **My Work**, **Results**, **Team & Settings**. Five home options:
1. Sales & Customers — inquiry/follow-up planning
2. Healthcare — non-clinical scheduling/admin planning
3. Real Estate — viewing/maintenance planning
4. Retail & Stock — inventory decision planning
5. Cloud & IT — authorized audit/change planning

Each option uses an actual deterministic, client-side workflow checklist. The user can enter a non-sensitive challenge, create a local plan, check steps, and separately record human review. The checklist **does not perform the task** or substantiate savings/ROI. Results counts only work in the current browser session.

Real existing P2-060 inventory CSV engine is preserved, exposed as an optional tool within **My Work** with fatal UTF-8 decoding, inherited size limits, conservative stock candidate assessment, approved marketing drafts and review-revoking edits. Actual inventory imports and draft generation are local; there are no model/provider/CRM/cloud/medical integrations.

Team & Settings states the true privacy status: local volatile browser session, no account/team access, English-only UI today; Arabic requires reviewed translation, including RTL and workflow-specific content, before release. The privacy/control section offers a working clear-session action.

The homepage's five sector links select the matching workspace industry using a fixed allowlist; user-controlled URL query strings cannot select other code paths.

## What was intentionally removed from the GUI
- Broad feature/module directories and technology catalog as primary navigation
- Separate developer-oriented funding readiness/release dashboard in the customer UI
- Duplicated inventory/campaign/evidence pages; the relevant functional pieces are grouped under My Work and Results
- Technical readiness counts, unsupported metrics, AI-branded decorative dashboard cards, and placeholders implying live services
- Old long-form homepage service/capability/operating content from the new draft homepage; the old Git version remains recoverable

**Not removed:** authentication and security infrastructure, audited source, private labs, test harnesses, staged PRs, business intelligence engine, release gates and original project directories.

## Files modified
- apps/site/index.html — public focused entry page
- apps/site/assets/focused-home.css — new public homepage styling
- apps/site/workspace/index.html — 4-view 5-sector workspace
- apps/site/assets/unified-workspace.css
- apps/site/assets/unified-workspace.js
- tests/test_p2_062_unified_workspace_ui.py — source and engine regression
- scripts/verify_unified_workspace_browser.py — synthetic-only loopback Chromium acceptance

## Verification / evidence boundaries
- GitHub source readback and V8 parsing; static HTML IDs/links, CSP no-network and DOM-target inspections: developer-local source checks, **PASS**.
- In-memory DOM simulation, actual committed MetaCampaign engine: sector selection, non-persistent work creation, four-item checklist, review gate, fake CSV (3 products/2 candidates), controlled draft creation, approval revocation and local downloads: **PASS in synthetic mock DOM only**.
- **Not run**: exact-branch Python pytest/Node suite on owner Kali, real Playwright Chromium, mobile visual/accessibility/screen-reader review, full repo regression, any real infrastructure authentication/data test, independent AppSec or CI.
- GitHub Actions runner remains billing/spending-limit blocked, and the stacked PR may not trigger current target-branch workflow filters.
- No proof of customer deployment, healthcare/patient operations, cloud savings, sales conversion, UAE/Qatar market traction or financial returns.

## Required clean-checkout acceptance
    PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider tests/test_p2_062_unified_workspace_ui.py
    node --check apps/site/assets/unified-workspace.js
    python3 scripts/verify_unified_workspace_browser.py

If approved local Playwright/Chromium is not already installed, the browser harness stops rather than downloading anything. It allows only ephemeral 127.0.0.1 static assets, blocks other HTTP traffic and uses fictional CSV. Do not bypass or weaken fail-closed checks to mark acceptance.

## Release and funding NO-GO
Foundation 3/9 historically internally verified. F04–F09 remain blocked; real OIDC/MFA, tenant isolation and staging security still require independent acceptance. The Qatar START dossier exists in separate draft #121, but buyer interviews, pilot data, price discovery, team commitments, legal incorporation/eligibility, and financial evidence are unverified. Billing/subscriptions remain deferred.

Keep this PR **draft**, stacked on draft #131. Do not merge, deploy, migrate, purchase cloud resources, enable personal/customer records or provider publishing, run clinical/enterprise automation or submit QDB/F6S application without separately requested and authorized release decision.
