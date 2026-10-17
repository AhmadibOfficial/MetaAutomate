# P2-04x — Private Conversational AI Gateway (Development Only)

Status: **optional OIDC-authenticated source implementation**, not a live customer AI service. The website's recently merged chat-first project intake is still a browser-only guided project brief. It is not connected to this gateway, and **no AI model has been installed or invoked** by this project milestone.

## Delivered in source

- \`apps/api/app/project_chat_private.py\`: a read-only \`POST /v1/private-project-chat/reply\` interface. Requests must use the existing organization- and user-bound \`get_tenant_session\` (session/CSRF/origin validation) and one of the workspace membership roles.
- The route is not registered unless \`MAT_PRIVATE_PROJECT_CHAT_ENABLED=1\` at startup, and startup rejects enabling it in \`WORKSPACE_AUTH_MODE=dev_key\`.
- Models connect ONLY to explicitly configured \`http://127.0.0.1:<port>/v1/chat/completions\` using direct \`http.client.HTTPConnection\`. No DNS, domain requests, proxies, generic URL fetch, redirects, external provider keys, or web search. Local model endpoint must be independently controlled and network isolated.
- The request's prior dialogue is client supplied, limited to 12 turns and 6500 total characters. System and tool roles cannot be supplied; only alternating user/assistant text is allowed. Generated replies are text-only and capped at 4000 characters. There are **no model function calls, plugins, media or outbound user messages**.
- Each response marks model-execution attestation, history persistence, media generation, external actions, customer contact, publishing and release as **false**. No database writes, cross-request session history or user-tracking telemetry.
- Fail-closed if the private local model isn't configured/responding, is unlicensed, or a request exceeds bounds. Test endpoints using a wholly fake local model connector to avoid network use; passing these tests **does not prove a real neural LLM is running**.

## Required *real* acceptance before a private test deployment

1. Restore GitHub Actions startup (issue #100), or record independent exact-commit local tests with actual environment metadata and sign-off.
2. Obtain private OIDC Identity Provider, MFA evidence, strict tenant isolation, origin/CSRF controls and approved staging ingress. Never reuse developer access tokens for public customers.
3. Stage a specifically licensed local LLM checkpoint on a host approved for its runtime cost/privacy envelope. Hash the actual model/weights, dependencies and version. Verify no unsupported outbound networking and memory/CPU/GPU limits.
4. Independently approve a model risk assessment and grounded content policy. **The current flags (\`MAT_PRIVATE_CHAT_LICENSE_REVIEWED\`, \`MAT_PRIVATE_CHAT_NETWORK_ISOLATED\`, \`MAT_PRIVATE_CHAT_HUMAN_POLICY_REVIEWED\`) are only operator assertions**, not cryptographic legal/technical validation. A signed deployment-admission gate and revocable trust registry must be added before enabling live customers.
5. Independently verify prompt-injection containment, tenant authentication, application-level rate limits, anti-DoS, inference quotas, incomplete/slow responses, privacy/consent disclosures and logging exclusions.
6. Integrate the public site only after a secure deployment design accounts for separated Render static website vs private API origin, CORS/CSRF/SSO, signed-in users, explicit retention consent, accessibility and security review.
7. Add tenant-scoped **persistent history** only after encrypted storage, RLS, deletion/export and retention controls have been implemented and tested. No current code claims the history exists.
8. Creative image/video/Piper speech workers remain separately gated under draft PRs #94/#95/#97/#101/#102/#103; a private text chat must not be able to activate those services or publish media.

## Configuration — engineering staging only

\`\`\`text
WORKSPACE_AUTH_MODE=oidc
MAT_PRIVATE_PROJECT_CHAT_ENABLED=1
MAT_PRIVATE_CHAT_LICENSE_REVIEWED=1
MAT_PRIVATE_CHAT_NETWORK_ISOLATED=1
MAT_PRIVATE_CHAT_HUMAN_POLICY_REVIEWED=1
MAT_PRIVATE_CHAT_LOCAL_ENDPOINT=http://127.0.0.1:11434/v1/chat/completions
MAT_PRIVATE_CHAT_APPROVED_MODEL=<reviewed-local-model-identifier>
MAT_PRIVATE_CHAT_MODEL_SHA256=<sha256-of-approved-model-checkpoint>
\`\`\`

**Do not use these example flags to activate customer service.** They are not independent admission evidence. The actual \`main.py\` OIDC startup also requires fully configured issuer, callback, HTTPS origin, restricted Postgres role and signed SSO state.

## Deployment and release boundary

Website PR #104 was separately merged as a **browser-only** redesign under direct user authorization. It contains no API call to this gateway and generates no AI content. Its Render publication requires the account's workspace confirmation, successful website runtime testing and a separate service deploy.

This P2-04x backend PR remains **draft and unmerged**; it must not be deployed automatically and must not be interpreted as completed customer accounts, persistent conversation history or actual model inference. No billing, credentials, production traffic, uploads, image/video generation or deployment performed.
