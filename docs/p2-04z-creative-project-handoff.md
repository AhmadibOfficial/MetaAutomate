# P2-04z — Start a Project → Creative Workbench

## What is usable

This is a standalone static website integration of the already deployed
conversation-first intake and Creative Workbench. It does NOT add new backend
services, paid inference subscriptions or media generation.

- After finishing the five-step guided project intake, users can choose
  image or video and explicitly select **Continue in Creative Workbench**.
- In the optional experimental on-device WebGPU chat, after a successful
  model response, users can explicitly choose **Plan visuals**. The handoff
  transfers **only the latest user's question** (not AI output or history).
- An explicit **Download conversation** action exports the bounded recent
  local model turns as a plain text file. No server receives these by default.
- Handoff stores only a format, bounded project goal and optional audience in
  **sessionStorage** in the same browser tab. The data expires after 10 minutes
  and is removed on the first attempted read (including invalid/expired data).
- The Creative Workbench prefills only kind, goal and audience and displays
  an alert that rights, consent and approval are NOT established.
- The creative form keeps rights \`unknown\`, likeness \`unknown\`, and does
  not submit, run a model, publish or pay for anything automatically.
- No prompt or personal info is embedded in the URL fragment or query string.
- Users who reject/disable browser storage can still manually copy their brief.

## Independent verification limits

Developer-side V8 syntax and contract checks verified:
- Four modified JavaScript files parse.
- Same-tab handoff is one-time, bounded and expires as designed.
- Only explicitly selected project fields are copied.
- The added markup IDs are unique and scripts are loaded in order.

The repository includes new static and Playwright acceptance tests for
desktop/mobile, no external requests and preservation of rights HOLD.
GitHub Actions issue #100 has previously failed BEFORE job steps run.
**No passing GitHub CI or human accessibility review may be claimed
until those checks actually execute.**

Real image/video/Piper/Kokoro inference is *not* included; its signed model
rights, runtime, source evidence, quality and customer activation remain
in draft gated PRs (#94, #95, #97, #101, #102, #103).
The private OIDC/LLM backend draft #105 remains unmerged and disabled.
The experimental browser-based Qwen model is still optional and needs
GPU-specific model execution testing. This project handoff does not create
a public login, cloud history or a production multimodal model.

## Acceptance checklist

1. Start a Project static assets and Creative Workbench served from one
   Render static website origin.
2. Real browser checks of both handoffs, source rights defaults and cleanup.
3. Browser and keyboard accessibility checks for the additional buttons.
4. CDN/local model license and security policy reviewed independently.
5. Manual publication of static website commit ONLY after release selection.

User-approved release scope is existing website features and safe
planning integration. No change to private Phase 01/02/03 NO-GO or
media generation authorization.
