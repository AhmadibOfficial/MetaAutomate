> Superseded for the public website by [P2-057 Blue Workspace](p2-057-blue-workspace-navigation.md): the old structured form, black theme and unused marketing chrome were removed. This file remains as historical implementation evidence, not a description of the current live page.

# P2-056 — MetaAutomate Start a Project: Dark Chat / Work Workspace

## Delivered website interface

The /engage/ page now uses the approved dark, immersive conversational dashboard direction. It is original MetaAutomate branding rather than a claim to be ChatGPT.

- **Chat:** current five-step guided project intake, editable answers, explicit project brief copy/download/email review, and opt-in on-device WebGPU text AI. No fake server AI or automatic submissions.
- **Work:** functional links to Canvas PNG graphics, WebM video assembly using user-provided narration, guided project brief and optional local AI. Work actions do not claim autonomous cloud execution.
- **Sidebar:** real New Project reset, local search of shipped starting points, templates and functional creative/services links. No fake customer account, chat history or persistent library.
- **Mobile:** collapsible sidebar, Escape dismissal, keyboard project search, responsive controls, focus rings and reduced-motion support.
- **Preserved:** original structured enquiry form (#brief-form), mailto handoff, privacy/rights gates, direct image/video routes and opt-in model download disclosure.

## Verification commands

Source:
- python -m pytest -q tests/test_p2_056_dark_project_workspace.py tests/test_p2_04w_project_chat_static.py tests/test_p2_04y_device_ai_static.py tests/test_p2_051_direct_creation.py tests/test_site_customer_clarity.py
- node --check apps/site/assets/project-workspace-dark.js
- node --check apps/site/assets/project-chat.js
- node --check apps/site/assets/project-device-ai.js

Browser:
- python -m http.server 18080 --bind 127.0.0.1 --directory apps/site
- python scripts/verify_dark_project_workspace_browser.py

Test 1440, 860, 390 and 360 pixel widths. Verify mode switch, actual links, consent before any model download, guided input, filter, keyboard, no uninvited provider requests, overflow and screenshots.

## Still unavailable

The static site does not run a hosted LLM, a customer identity/database service, stored chat history, authenticated private worker, or neural image/video/voice inference. The existing optional WebGPU client model is experimental and depends on capable visitor hardware. The graphic and video makers are actual downloadable browser utilities, not neural generative models.

CI issue #100 has historically failed jobs before steps execute. Source and mock interaction checks alone do not prove real browser acceptance. Neither the unfinished private P2-052/054/055 backend nor its migrations/credentials are activated by this website-only milestone.
