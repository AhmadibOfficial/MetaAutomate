# MetaAutomate Website — Keyboard and Screen-Reader Walkthrough

**Scope:** Website-only draft PR #55. This document does not grant publication or Phase 03 release permission.

## Evidence boundaries

Automated Chromium tests can confirm focus transitions, keyboard controls, ARIA names/roles/states and the browser accessibility tree. They **cannot prove** that a human using Orca, NVDA, JAWS or VoiceOver hears and understands the correct announcements. An actual assisted-technology test remains pending until reported by a human tester.

The CI workflow runs the existing browser review plus a new source-only accessibility-tree test; it uploads a JSON evidence report with screenshots. All example brief inputs are synthetic. Nothing is sent to customers, providers or a backend.

## Reproducible Kali screen-reader session (no subscriptions)

On a clean, pinned PR #55 checkout, launch a local static server from the repository root:

    python -m http.server 18080 --bind 127.0.0.1 --directory apps/site

Open http://127.0.0.1:18080/ in Chromium. Start the system's accessible screen reader, such as Orca where installed and configured. On a GNOME desktop the usual toggle is Super+Alt+S; on Kali configurations this may differ. If Orca is unavailable or cannot speak reliably, mark the check BLOCKED, not passed. Never type real credentials or personal client details.

## Human observation log — initially NOT TESTED

| ID | Key action | What must be heard or experienced | Current status |
|---|---|---|---|
| H01 | Open home, browse landmarks/headings | Accurate page title, banner, navigation, main and footer landmarks; one descriptive main heading | NOT TESTED |
| H02 | Tab then Enter on skip link | First focus is visibly Skip to content; Main becomes reading target and focus remains logical | NOT TESTED |
| H03 | On mobile-width browser Tab to menu; Enter, Escape | Open navigation named/expanded, links reachable, Escape closes and restores button focus | NOT TESTED |
| H04 | Tab across 3 Workspace example buttons; Enter/Space | Each button's name and pressed state; changed plan stage title/description announced in live region | NOT TESTED |
| H05 | Read diagram | Announced as *illustrative* with no live client action; no redundant decorative content | NOT TESTED |
| H06 | Browse five operating principle tabs with arrows | Selected state announced and associated updated tabpanel described | NOT TESTED |
| H07 | Start a project, navigate quick email | Recognizable email link; no claim of a submitted contact form | NOT TESTED |
| H08 | Submit empty enquiry by keyboard | Required field names and validation alert read; focus moves to first invalid field | NOT TESTED |
| H09 | Enter invented brief, keyboard submit | Result heading receives focus and is announced; email/copy/download controls available | NOT TESTED |
| H10 | Read the generated draft | Clearly says nothing is sent until user sends email, including abbreviated draft warning when applicable | NOT TESTED |
| H11 | Browser zoom at 200 percent | Focus, readable text and access to menu, form and demonstration remain usable | NOT TESTED |
| H12 | 360px mobile and desktop | No obscured controls, missing labels or serious text contrast problems in actual use | NOT TESTED |

## Tester report fields

- Actual tester, system, screen-reader name/version: NOT RECORDED
- Test date and pinned final source commit: NOT RECORDED
- For each H01–H12: PASS/FAIL/BLOCKED, observed speech, keyboard steps and issue references: NOT RECORDED
- Confirmed defects, fixes, screenshots (synthetic data only): NOT RECORDED
- Real screen-reader test decision: NOT COMPLETED
- Owner content, mailbox and privacy wording approval: NOT GIVEN
- Owner publication and merge permission: NOT GIVEN

A human screen-reader walkthrough is useful usability evidence; it is not by itself independent professional accessibility certification. Automated testing alone does not meet this gate.

## Release gate

Publication remains **HOLD**. Render auto-deploy is off. PR #55 remains a draft and must not be merged or deployed without explicit owner approval. Phase 01 3/9 NO-GO, Phase 02 operational NO-GO and Phase 03 real execution NO-GO are separate and unchanged. No subscriptions or cloud provisioning are required for this review.
