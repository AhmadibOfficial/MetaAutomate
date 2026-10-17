# P2-04w — Chat-first "Start a Project" Experience

**Goal:** MetaAutomate's "Start a project" interface feels like a clean, conversational creative/business workspace. It is **not** a copy of ChatGPT branding, nor a claim that ChatGPT/another language model powers the site today.

## Implemented in source

- **New primary interface** at \`/engage/\`: white, responsive 2-column composition on desktop and compact, single-column layout on phones. A project sidebar, five guided conversational questions, bottom textarea composer, suggested project starting points and clear input state.
- **Guided, deterministic discovery**: idea/problem → desired business outcome → audience → timing → requirements/constraints. Replies are retained only in the current page's JavaScript memory. Assistant replies are predefined questions. This is not an AI conversation.
- **Project categories**: Creative Studio (image/video/voice plans), business automation, mobile/web products, product design/experience and authorized security assessment. The existing \`?service=Product%20Design%20%26%20Experience\` pre-selection remains supported from service pages.
- **Privacy**: no remote fetch or hidden send, no analytics or storage, no model inference, no credentials, no localStorage, no payment collection, no upload or social post. All user input is inserted with \`textContent\` to resist HTML/script injection. No promise of confidentiality beyond the existing browser semantics; users are explicitly told not to enter sensitive information.
- **Project summary**: locally formatted, downloadable plain text; copy only on explicit click; an abbreviated \`mailto\` link when needed so the user can review/send from their **own** email application. No automatic enquiry submission.
- **Navigation and accessibility**: Shift+Enter inserts a newline, Enter sends, clear focus rings, live log announcements, errors in role=alert, editing last reply, "New project" reset, reduced-motion preferences and mobile responsiveness. An expandable **existing enquiry form** remains present with its original \`id="brief-form"\` and mailto workflow for deep links and accessibility fallback.
- **Source tests and real Chromium test script** validate no external requests, no DOM HTML injection, 360px/390px/1440px views, download, multi-turn flow, reset, editing and legacy form compatibility. Actual CI result must be checked before claiming pass.

## What has NOT been delivered

- A connected LLM or an AI assistant that reasons freely about the project.
- Signed-in user accounts, cross-device conversation history, persistent storage, automated customer CRM records, provider connections, live image/video generation, paid model calls or autonomous project execution.
- A real time messaging channel with MetaAutomate staff.
- Automatically emailed proposals or approved business commitments.

The page must always clearly say \`GUIDED INTAKE · NO LIVE AI\` until a properly deployed, authenticated, consent-preserving AI provider actually exists.

## Next stage: real AI Project Workspace

1. Implement tenant-scoped, authenticated conversational session storage with explicit privacy/retention choices, deletion and rate limiting.
2. Build a model-independent **conversational orchestration** API with request/response contracts, streaming, error recovery, prompt-injection protection and validated business/creative intents. Avoid exposing model keys or generating unsupported sales/income claims.
3. Ground follow-up questions and scope suggestions in verified business services, approved models, budget, security/consent rules and accessible content.
4. Route image/video/voice tasks into quarantined P2-04c/q/t/u/v workers after their own licensing, compute, inference evidence and independent review gates. A chat message must **never** grant direct production or publish permissions.
5. Provide visual preview, image/video generation job status, retries, audited review, project handoff, attachment permissions and independent export/release authorization. Test with real users and assistive technology.
6. Reassess hosting/compute boundaries and costs before activating production. No subscriptions or payment setup during this branch.

## Release decision

Website-only source for a revised browser prototype; **do not deploy until source, browser and privacy tests pass**, accessibility review covers chat inputs and summaries, and relevant website wording/contact paths are reviewed. Existing Phase 01 verification 3/9, Phase 02/03 operational NO-GO and genuine AI generation NO-GO are unchanged. New P2-04w UI development does not authorize customer model execution or public uploads.

No paid services, cloud provisioning, social media publication or customer data were used in the implementation.
