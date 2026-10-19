# P2-058 — MetaAutomate four-signature-color Project Workspace

## Brand source of truth

Source: `docs/brand/GLOBAL_EXPERIENCE_V2.md`, confirmed against `apps/site/assets/site.css`.

| Signature role | Color | Exact HEX |
| --- | --- | --- |
| Foundation, full-screen background and navigation | Midnight Navy | `#040D20` |
| Primary controls, focus hierarchy and completion actions | Electric Blue | `#00A7ED` |
| Project composer, user messages, Work cards and legible surfaces | Silver | `#DCE6F1` |
| Restrained headings, sidebar accent, consent CTA and keyboard focus | Signature Gold | `#EFB94F` |

Deep Navy `#071932` is a supporting tonal extension, **not an alternative fifth signature color**.

The page uses a separate scoped last-loaded CSS layer `apps/site/assets/project-workspace-brand.css`. It intentionally overrides P2-057's generic blue CSS while retaining that milestone's functioning desktop/mobile nav, Chat/Work switch, safe guided project flow, consented browser AI experiment, graphic and video creators, no legacy structured enquiry form, and no subscription requirement.

Design checks: text contrast >= 4.5 for the intended solid text/surface pairs; refined typography via system/Inter stacks without fetching remote fonts; bright blue with navy text for primary actions; gold with navy text for the model-consent download and gold outlines for focus; silver surfaces with navy body text. Heading gold underline is decorative and does not add misleading text.

## Acceptance

```bash
python -m pytest -q \
  tests/test_p2_058_brand_palette.py \
  tests/test_p2_057_blue_navigation.py \
  tests/test_p2_056_dark_project_workspace.py \
  tests/test_p2_04w_project_chat_static.py \
  tests/test_p2_04y_device_ai_static.py \
  tests/test_p2_051_direct_creation.py \
  tests/test_site_customer_clarity.py

node --check apps/site/assets/project-workspace-dark.js

# Actual browser acceptance (requires local Chromium via Playwright):
python -m http.server 18080 --bind 127.0.0.1 --directory apps/site
python scripts/verify_dark_project_workspace_browser.py
```

Browser test checks 1440, 860, 390 and 360 pixel widths, computed CSS custom properties, silver composer, blue send button and gold heading underline, working Work tools, nav hide/show, mobile Escape, project chat, and no unsolicited network requests. Full browser and screen-reader verification should not be claimed while GitHub Actions issue #100 causes `steps:null` pre-run failures.

## Release boundary

Static marketing website redesign **only**. No live cloud model, external AI model keys, customer accounts, persistent conversation history, billing, agent execution, private database migrations or new hosting subscriptions. A successful Render static deploy confirms only file publication.
