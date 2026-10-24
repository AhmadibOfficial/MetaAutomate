# P2-060c — Keyboard, focus and descriptive-media accessibility gate

## Why this is required

P2-060b's live Chromium campaign demonstration and preserved-evidence
consistency checks passed **on the developer's Kali machine**. They did not
prove keyboard reachability, accessible focus after conditional reveals, text
alternatives for generated Canvas artwork or screen-reader behavior.

P2-060c is a deliberately narrow improvement to the existing, **browser-only
rules-driven** Campaign Workbench. There is no subscription, neural model,
publishing API, customer identity, cloud deployment, new database or
production rollout.

## Implemented source

1. The Skip to campaign workbench link targets a programmatically focusable
   main landmark, and the revealed Results/Campaign headings are
   programmatically focusable. Successful inventory import moves keyboard
   focus to the Results heading; preparing a campaign moves focus to the
   Campaign heading. Users can tab forward into newly revealed controls.
2. Native fields retain associated labels/fieldset legends. A Canvas
   role=img exposes a dynamic aria-describedby text alternative that
   identifies product, brand and listed price, plus the unverified/publishing
   limitations. This is a draft summary, **not** a description of pixels
   inspected by a screen reader.
3. Focus indicators use MetaAutomate dark navy on white/light panels and
   gold on dark surfaces, with a 3px CSS outline. Reduced-motion
   behavior remains enabled. All four brand colors are retained.
4. The isolated Playwright gate exercises Skip/Enter, form labels, heading
   focus after reveal, fieldset legend, Tab and Space controls, approval
   invalidation after editing, visible focus style, an original Canvas
   description, and synthetic measurement across 1440/390/360 CSS px.
   Browsers use the already-downloaded official Playwright full Chromium
   channel (not the separately packaged headless shell).
5. Browser route blocking and loopback-only read-only server are inherited
   from P2-060b. No test needs real customer files or external HTTP access.

## Verify locally on Kali

From feature/p2-060c-keyboard-accessibility, run:

    cd ~/MetaAutomate

    PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q \
      tests/test_p2_060_accessibility.py \
      tests/test_p2_060_campaign_workbench.py \
      tests/test_p2_060_browser_harness.py \
      tests/test_p2_060_evidence_review.py

    PLAYWRIGHT_BROWSERS_PATH="$HOME/.cache/metautomate-playwright-browsers" \
      "$HOME/.local/share/metautomate-browser-venv/bin/python" \
      scripts/verify_campaign_accessibility.py

    git status --short --branch

The Python source-only suite does not install Playwright or Chromium;
run the second command with the **existing** isolated wheel/browser on Kali.
The second command prints DEVELOPER_LOCAL_ACCESSIBILITY_AUTOMATION_PASS
**only after** all viewports and controls are exercised. No screenshot or
evidence directory is created by this gate. Failures must remain failures;
do not bypass focus checks or allow outbound connections to force PASS.

## Acceptance boundary

- [ ] Exact-HEAD source-only tests actually run and pass on Kali
- [ ] Exact-HEAD Chromium keyboard/focus workflow actually run and pass
- [ ] Independent NVDA/VoiceOver/TalkBack or another relevant screen reader
- [ ] Manual keyboard review including 200% browser zoom and screen magnifier
- [ ] WCAG color contrast and focus-obscuring evaluation using actual pixels
- [ ] Independent AppSec/privacy review, CI at exact commit and signed evidence
- [ ] Separate production release and migrations approval

**Not a claim of WCAG 2.2 conformance**: This source gate checks a small
subset of keyboard and focus behaviors. It does not test every assistive
technology, speech output, font scaling, color perception or aesthetic
quality. The screen captures still need human visual and accessibility
inspection. Automated PASS cannot override the original Foundation
**3/9 verified**, Phase 02/03 **NO-GO**, private billing-blocked CI,
unmerged PR prerequisites, or the release policy.

## Source custody

P2-060c is stacked on draft PR #123, which was itself built on
#122 -> #121 -> #120 -> #119. Do not merge the head branch straight into
main, run migrations, enable customer traffic, or deploy on the strength
of these local validation scripts. Archive historical P2-060b screenshots
separately: the new accessibility source changes do not alter or certify
that earlier screenshot evidence.
