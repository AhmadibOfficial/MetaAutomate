# P2-060d — Responsive reflow and visual review evidence

## Scope and test truth

This is a draft extension of P2-060c's locally accepted keyboard/focus
Campaign Workbench. It strengthens the **existing first-party, rules-only
synthetic inventory-to-campaign workflow**. There are no real customers,
AI inference, external social publishing, model downloads, telemetry,
database migrations, new permissions or production rollout.

**Important zoom distinction:** Chromium's Playwright viewport size is
not the same as clicking the browser's native Zoom to 200%. At a
nominal 1280-pixel-wide desktop, 200% browser zoom often leaves about
640 CSS pixels for responsive layout. This verifier uses an actual
headless Chromium browser at **640 CSS px** as a *reflow approximation*
and **also** tests the WCAG-style 320 CSS-pixel reflow case. It does
**not** manipulate or attest real browser zoom, and does not
establish WCAG 2.2 conformance.

## Engineering changes

- Loosen narrow flex field min-width constraints so form controls can
  shrink or stack rather than escaping the white panel.
- Wrap long labels, field explanations, button labels, product titles
  and navigation instead of creating horizontal document overflow.
- Use non-sticky status text on compact widths so it cannot obstruct
  a user trying to reach keyboard controls at small viewport heights.
- Keep the four MetaAutomate brand colors and the original graphic
  dimensions (1080x1080). Improve small brand-caption legibility.
- Add a self-hosted, network-denying Playwright verifier at five CSS
  viewports: 1280x720, 640x360, 390x844, 360x780 and 320x640.
- Exercise real synthetic inventory import, draft, internal-only
  approval and self-reported metrics. Then check critical control
  bounding boxes, sibling overlap, document horizontal overflow,
  text-block scroll-clipping, actionable buttons via Playwright
  trial clicks and focused keyboard Tab navigation.
- Save **only fabricated** full-page screenshots, a JSON check report,
  and an owner-generated SHA-256 manifest to a **new private directory
  outside the source checkout**. Do not overwrite or delete older
  P2-060b/P2-060c artifacts. Screenshot pixels are for later human
  review, not an automatic aesthetic or contrast PASS.
- Run six zero-dependency Python source unit tests including geometric
  overlap, width scenario and no-production-effects assertions.

## Kali verification (no new package installations)

First verify the local branch is clean and fetch the remote draft
branch. Do not overwrite uncommitted work.

    cd ~/MetaAutomate
    git status --short --branch
    git fetch origin
    git switch --track origin/feature/p2-060d-responsive-reflow-proof

    PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
      tests/test_p2_060_reflow.py \
      tests/test_p2_060_accessibility.py \
      tests/test_p2_060_campaign_workbench.py \
      tests/test_p2_060_browser_harness.py \
      tests/test_p2_060_evidence_review.py

    PLAYWRIGHT_BROWSERS_PATH="$HOME/.cache/metautomate-playwright-browsers" \
      "$HOME/.local/share/metautomate-browser-venv/bin/python" \
      scripts/verify_campaign_reflow.py

    git status --short --branch

The runner uses the **existing** isolated Playwright 1.55.0 wheel and
downloaded full Chromium browser; it does not need headless-shell, an
internet connection or a new pip/apt install. Its read-only server
binds only to ephemeral 127.0.0.1 and denies HTTP mutation, unexpected
Hosts and off-origin browser requests.

The browser gate prints DEVELOPER_LOCAL_REFLOW_AUTOMATION_PASS only
if **all five** viewport cases pass. It prints the newly created
private artifact path; report.json distinguishes genuine observations
from unverified accessibility and financial claims. On test failure
only partial evidence may exist; **do not claim an acceptance pass**.

## Separate human review to perform

- Run Chrome/Firefox GUI native 200% browser zoom on a **1280 px
  display**; inspect effective viewport CSS width and compare it to
  the 640px automated layout approximation.
- Check actual 400% browser zoom or a 320 CSS px equivalent without
  horizontal scrolling for the primary one-column content.
- Visually inspect each screenshot for legibility, button labels,
  visible focused elements, overlap, text wrapping, truncated icons,
  user comprehension and errors that DOM geometry does not detect.
- Check 200% text-only font scaling, different font stacks and
  high-contrast/forced-colors modes where applicable.
- Complete manual keyboard-only end-to-end, screen-reader testing
  (e.g. Orca on Kali Linux), and color contrast/visual focus review.
- Arrange independent AppSec review, exact-commit hosted CI and
  independent acceptance before considering a release.

## Gate policy

P2-060b browser flow and saved evidence review passed on Kali.
P2-060c keyboard/focus automation passed on Kali at parent commit
8217a14843c340e5219cc2949fdfebc49e867793 (33 source tests,
DEVELOPER_LOCAL_ACCESSIBILITY_AUTOMATION_PASS). **P2-060d's new source
and browser tests have not yet been run on Kali or hosted CI.**

No implied merge, customer access, deployment, audited revenue,
real model-backed automation or Startup Qatar submission. Foundational
release remains 3/9 verified and operational NO-GO.
