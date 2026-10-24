# P2-060d — responsive reflow and zoom-equivalent workflow checks

P2-060c passed owner-local keyboard accessibility (33 source tests and an
isolated Chromium functional acceptance). This follow-up is a new, draft,
stacked **source-only engineering milestone**, not a production release.

## What changed

- Narrow form groups no longer impose a 200px field minimum at mobile CSS
  widths. Button labels and long user data wrap instead of forcing sideways
  document scrolling. Action controls span the available panel width at
  360px and below, and the sticky status becomes static on small layouts.
- Original four MetaAutomate brand colors and focus/skip behavior remain.
- A new read-only, loopback-only real Chromium gate imports synthetic CSV,
  generates a plan, checks key control bounding boxes and document scroll
  width, uses keyboard Space/Enter for draft approval, checks approval
  revocation after editing and evaluates self-reported metrics.
- Screensize cases: 1280, 640, 390, 320, and 256 **CSS pixels**.
  640 and 320 CSS pixels *approximate* the reflow available to 1280/640
  physical-pixel viewports at 200% zoom. This test does **not** set or prove
  actual browser zoom. User-agent and font behavior may differ.
- Four source-only tests protect the narrow layout rules and same-origin
  browser harness. Neither test suite uploads business data.

## Developer-local acceptance on Kali (required, not yet executed)

On branch `feature/p2-060d-responsive-reflow`:

```bash
cd ~/MetaAutomate
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
```

An actual `DEVELOPER_LOCAL_REFLOW_AUTOMATION_PASS` is required before
marking this gate locally accepted. CSS sizing is checked by the real browser;
the Python source suite alone is insufficient. Do not suppress failures or
loosen the no-egress guardrails to manufacture a PASS.

## Remaining human and independent reviews

- Actual 200% browser zoom with keyboard-only navigation, enlarged text and
  400%/320 CSS-pixel reflow assessment; test with relevant browsers.
- Human inspection for legibility, clipped labels, overlap, contrast,
  obscured focus, screen magnification and original campaign artwork.
- Independent screen-reader usage, formal WCAG 2.2 mapping and AppSec review.
- Trusted CI at exact commit, real customer validation and Foundation
  operational release prerequisites.

P2-060d remains **draft and stacked on #124** (itself based on #123 and
older draft PRs). GitHub Actions billing restrictions, the Foundation
**3/9 verified** state and production **NO-GO** remain unchanged. No merge,
deployment, migration, social publication or QDB application submission.
