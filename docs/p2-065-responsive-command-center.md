# P2-065 — Responsive MetaAutomate Command Center

**Status:** new responsive UI branch; founder-review candidate, not merged or deployed.
**Reference:** owner-supplied screenshot of a dark, chat-centered AI workspace (2026-11-04). Original MetaAutomate design, branded navy `#081c36`, blue `#0788d2`, gold `#e9b84f`, silver `#e2e9f1`. Third-party names and branding are not copied.

## User experience

- Desktop: narrow icon navigation rail, searchable recent-chat sidebar, central intelligent-workspace screen with abstract CSS sphere, real tool cards, bottom command composer.
- Tablet: collapsed sidebar with menu/drawer, intact main controls.
- Mobile (320/360/390px): bottom 5-item navigation, off-canvas chat list, safe-area support, one-column cards and accessible responsive composer.
- Tools: Image Studio, Video Studio, AI Project Guide, Business Intelligence, Workflow Planner, Growth Autopilot.
- Every advertised 'Open tool' action connects to an **existing** MetaAutomate static browser route. No dead controls.
- Chat: session-only local deterministic guidance, draft intent, up to 12 local chats and 30 turns per chat, search, new chat, typed command, downloadable TXT, clear all. No persistence or hidden tracking.
- Avatar is CSS/SVG/MetaAutomate mark only. No third-party JS, fonts, photos or remote asset calls.

## Privacy and accuracy

- `connect-src 'none'`; no account system, cookies, local/session storage, remote API, server AI inference, publishing, payment, CRM mutation, automated messages or infrastructure writes.
- **No autonomous agents here.** Guided responses are controlled static plans; the optional Qwen browser-side AI on `/engage/` is separate, WebGPU-dependent and experimental.
- Browser image PNG creator and narrated WebM export are available at `/creative/` and not duplicated or rewritten.
- Workflow planner, inventory CSV, activity metrics at `/workspace/` are preserved. Synthetic intelligence views at `/intelligence-lab/` and `/automation/` remain previews.
- Do not enter confidential records, customer or patient data, credentials, trade secrets, or proprietary logs in any preview.
- Operational release gates remain **NO-GO** (F01–F03 verified; F04–F09 blocked). No change to production static site, API, databases, keys, provider settings, or paused development automation.

## Founder review on Kali

Do not overwrite or change the existing `~/MetaAutomate` tree or `MetaAutomate-Founder-Review`. Open a separate detached worktree:

```bash
cd "$HOME/MetaAutomate" || exit 1
git fetch origin
REVIEW="$HOME/MetaAutomate-Command-Review"
if [ -e "$REVIEW" ] || [ -L "$REVIEW" ]; then
  echo 'STOP: review directory already exists. Inspect before continuing.'
else
  git worktree add --detach "$REVIEW" origin/feature/p2-065-responsive-command-center
fi
cd "$REVIEW" || exit 1
python3 -m pytest -q -p no:cacheprovider tests/test_p2_065_command_center.py
node --check apps/site/assets/command-center.js
python3 scripts/verify_command_center_browser.py
python3 -m http.server 8879 --bind 127.0.0.1 --directory apps/site
```

Open `http://127.0.0.1:8879/command/` in Kali browser. Stop server with Ctrl+C. If port busy, use another free port; do not kill unrelated processes.

## Acceptance requirements

1. Founder confirms visual match to the uploaded design direction and readability on desktop and mobile.
2. Real Chromium QA passes at 1440, 1024, 768, 390, 360, 320 width. No horizontal overflow, absent actions, crash, off-origin request or keyboard trap.
3. The five navigation panels, chat create/search/open/clear, tool selection, TXT export and real tool links all work.
4. Existing workspace, creative, guided brief, Growth Autopilot and Intelligence Lab remain unchanged and available.
5. Independent accessibility, security and release review before making this the default `/workspace/` route. No customer/AI backend claim without verification.

## Delivery sequence

PR #PENDING is a dedicated interface proposal. Do not switch live homepage/workspace navigation or deploy this branch until founder signs off, CI passes, independent review and explicit deployment approval.
