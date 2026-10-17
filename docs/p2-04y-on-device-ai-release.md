# P2-04y — Opt-in On-device AI for Start a Project

## Why this feature exists

MetaAutomate's main marketing site is a **static website** on Render. A
static site cannot run Python FastAPI inference or a large GPU model server.
The previous Start a Project experience used **five predefined questions**
and was not real AI. The user has asked for **genuine conversations** without
a paid inference subscription.

This increment introduces an explicitly opt-in **browser-local** text model,
separate from the existing fixed guide. Its model code and weights are
downloaded by the user's browser only after they press **Download model and
start local AI**. The browser then attempts actual on-device WebGPU inference;
responses come from the language model, not predefined questions.

## Exact model and operating mode

- Engine: WebLLM \`@mlc-ai/web-llm@0.2.85\` loaded lazily from
  \`https://esm.run/@mlc-ai/web-llm@0.2.85\` on **explicit click**.
- Model ID:
  \`Qwen2.5-0.5B-Instruct-q4f32_1-MLC\`, included in the official v0.2.85
  \`prebuiltAppConfig\`; needs approximately **1.06 GB graphics memory**
  plus other browser resources. Underlying Qwen2.5-0.5B-Instruct is
  **Apache-2.0 licensed**. Terms of the exact compiled model, source,
  legal notices and distributed WebLLM code are separate obligations.
- The library downloads its compiled code/model weights from externally
  controlled providers including \`esm.run\`, MLC's model library hosting,
  and Hugging Face. Do **not** enter private business information,
  credentials, or regulated personal data. Third-party executable code has
  **not been independently audited** by MetaAutomate.
- Pre-run check requires a secure context, \`navigator.gpu\` and an available
  WebGPU adapter. If unsupported, the UI reports a clear reason and preserves
  the functional guided intake as fallback. No remote model/API fallback.
- Once loaded, requests use \`engine.chat.completions.create\` with
  \`messages=[system, ...boundedSessionTurns]\`, \`max_tokens=260\`;
  no tool calls or external services. Session turns exist in page JavaScript
  memory only, limited to eight prior turns and length 1000 per user turn.
  No project is emailed, signed, published, billed, uploaded or persisted.
- WebLLM/browser cache **may persist downloaded model assets**. Clearing
  site/browser storage can remove them; clearing the conversation panel only
  deletes chat turns from the page, not browser cache.
- Intended experience: project scoping and brainstorming only. Tiny models
  can hallucinate, repeat themselves, misunderstand multilingual prompts or
  perform worse than large server models. Do not call this equivalent to
  ChatGPT's frontier model quality.

## What this does NOT solve

- **No authenticated customer accounts or cross-device history** (OIDC
  foundation still private/unverified; no RLS storage for customer history).
- **No backend AI instance** or trusted server-side agent. Private backend
  draft PR #105 remains gated, requiring a verified licensed model,
  independently approved OIDC/MFA, operational hosting and privacy review.
- **No actual image, video or natural-voice AI inference**. Related creative
  worker PRs #94/#95/#97/#101/#102/#103 remain separate gated work and
  cannot be activated through a static browser text model.
- **No guarantee of device compatibility or actual successful inference**.
  The full source and Playwright tests validate UI interactions and
  unsupported-device behavior; genuine WebGPU model-load/response tests
  require an actual compatible browser/GPU with internet access to
  model-hosting CDNs. Those acceptance tests are not yet evidenced.
- **Not an authenticated local security sandbox**. This is a browser JS
  experimental feature gated by human consent, not a secure personal vault.

## Acceptance and deployment

At minimum check:
1. Existing guided intake and email/download actions keep functioning.
2. Opening \`/engage/\` sends no requests to WebLLM/CDNs/Hugging Face; even
   opening the optional AI panel does not download external code.
3. Unsupported/disabled WebGPU returns an error and never imports the model.
4. On supported hardware, explicitly approved model loads, first real
   generated response is captured in a local acceptance recording, with no
   network request containing user prompts other than the reviewed model
   asset download flow.
5. Desktop/360px/390px/mobile text and keyboard access and error notices
   remain readable; copy/paste and new project flow work.
6. Browser content security, external code provenance and licensing
   obligations receive separate independent review before treating this
   as fully verified production AI.
7. GitHub Actions #100 startup failure resolved or an equivalent signed
   exact-commit test is obtained; untested code must not be marketed as a
   verified general-availability AI service.

Static website release (if approved) must not automatically enable any
backend, credentials, customer data collection or paid AI calls. The
optional panel remains an **experiment**, not a claim that every visitor
has AI. Keep the guided intake as the default.

Sources:
- https://webllm.mlc.ai/docs/user/get_started.html
- https://github.com/mlc-ai/web-llm/tree/v0.2.85
- https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct
