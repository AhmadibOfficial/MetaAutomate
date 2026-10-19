# P2-057 — Blue Start a Project Workspace

The Start a Project page is now **a focused blue MetaAutomate workspace** rather than a black-themed dashboard.

Delivered: stronger, responsive typography using privacy-preserving font stacks; a top navigation button that collapses and restores the sidebar on desktop and opens a dismissible drawer on mobile; keyboard Escape and Ctrl/Cmd+K support; functioning Chat/Work tabs, guided project conversation, opt-in WebGPU AI, and links to existing image and video tools.

The old **"Prefer a structured project form? Open the original enquiry form"** section is completely removed from the rendered HTML, together with unused website header/footer markup and duplicate navigation. Existing marketing calls to action formerly targeting `/engage/#brief-form` now link to the active composer `/engage/#project-chat-input`.

No customer accounts, cloud AI service, persistent history, autonomous agent worker or paid provider is activated by this website-only update.

Acceptance:
- Static checks: `python -m pytest -q tests/test_p2_057_blue_navigation.py tests/test_p2_056_dark_project_workspace.py tests/test_p2_04w_project_chat_static.py tests/test_p2_04y_device_ai_static.py tests/test_p2_051_direct_creation.py tests/test_site_customer_clarity.py`.
- JavaScript: `node --check apps/site/assets/project-workspace-dark.js`, `node --check apps/site/assets/project-chat.js`, `node --check apps/site/assets/project-device-ai.js`.
- Browser: serve `apps/site` on localhost port 18080, then run `python scripts/verify_dark_project_workspace_browser.py` and `python scripts/verify_project_chat_browser.py`.
- Browser screenshots should cover 1440px, 860px, 390px and 360px viewport widths and show brand-blue surfaces, no overflow, sidebar keyboard actions and no legacy form.

Source-level markup/JS and mocked interaction checks were performed during development, but **full Chromium acceptance and accessibility review are not certified** until CI runners execute or an independently witnessed equivalent test is completed. GitHub Actions runner startup issue #100 is still an unresolved dependency.

This update changes only the public static website and supporting regression tests.
