# P2-053 — Global & International AI Provider Adapter

**Working source adapter for live API protocols; no provider was contacted or billed.** This module is a provider-level network integration and normalized text output engine. It is NOT a deployed, commercially activated MetaAutomate AI service.

## Supported providers — text generation

| Operator provider code | Official destination fixed in source | Wire protocol | Region/data-transfer note |
| --- | --- | --- | --- |
| \`OPENAI\` | \`api.openai.com/v1/responses\` | OpenAI Responses | Residency subject to provider account terms |
| \`ANTHROPIC\` | \`api.anthropic.com/v1/messages\` | Claude Messages | Residency subject to provider account terms |
| \`GOOGLE\` | \`generativelanguage.googleapis.com/v1beta/models/{model}:generateContent\` | Gemini Generate Content | Residency subject to provider account terms |
| \`MISTRAL\` | \`api.mistral.ai/v1/chat/completions\` | Chat Completions | Residency subject to provider account terms |
| \`DEEPSEEK\` | \`api.deepseek.com/chat/completions\` | Chat Completions | Region, privacy and retention review required |
| \`QWEN_INTL\` | \`dashscope-intl.aliyuncs.com/compatible-mode/v1/chat/completions\` | Alibaba/Qwen compatibility | Singapore API endpoint; **not** a residency guarantee |

All model identifiers are chosen by **server operator configuration** and allowlisted exactly. New model releases, support, pricing, quality, country availability and commercial policies must be independently checked. No hardcoded invented active model version or price is claimed.

## What the adapter actually implements

- Immutable catalog of six provider-specific hosts and paths; users cannot pass arbitrary URLs or override egress destinations. Direct HTTPS transport with host verification; no redirect follow, DNS URL in prompt, proxy selection, cross-provider failover or retries.
- Correct provider-specific authentication headers. API keys read from private process environment only; never returned in metadata, copied into the browser, logged or committed.
- Correct request envelopes: OpenAI Responses with \`store:false\`; Claude Messages with version header; Gemini Generate Content; compatible chat API for Mistral, DeepSeek and Qwen.
- Uniform \`ModelResult(text, provider, model, input_tokens, output_tokens)\`. The source parses each provider's distinct JSON response safely. Token usage comes from the **provider's statement**, not an authenticated financial invoice.
- Rejects provider attempts to make a tool call, multimodal action, blocked/refused/unfinished response, overlong result, invalid content or unexpected HTTP status.
- Bounded user prompt (20–1200 characters), bounded response (4000 characters / 16 KB JSON), 400 output-token request target, direct 18-second timeout, and no automatic billable retries.
- **Fail closed before any network call** unless explicit recipient/data transfer approval and independently verified *durable cost reservation* are provided. The adapter's \`spend_reservation_verified=True\` argument is a narrow trusted-caller contract, **NOT** itself evidence that a financial ledger exists.

## Architecture and cost boundary

\`\`\`text
Authenticated MetaAutomate user
  -> tenant- and actor-bound request + explicit cross-border consent
  -> provider/model/country/terms eligibility policy
  -> atomic durable currency-denominated budget reserve (NOT IMPLEMENTED)
  -> approved external egress and credential vault
  -> provider-specific HTTPS adapter [THIS PR]
  -> normalized answer + provider-reported usage
  -> reconciled finance ledger + audit (NOT IMPLEMENTED)
  -> sanitized, tenant-scoped artifact download (P2-052, DRAFT)
\`\`\`

**Never set \`spend_reservation_verified=True\` in live code without a genuine, atomic and independently reviewed pre-request reservation.** A boolean supplied by the front end, a user, a test fixture or the operator's environment is not an adequate financial proof. No public task route invokes the new adapter yet.

Provider failure after a billable request may still incur charges. Implement durable reservation and lifecycle states (RESERVED, COMPLETED, UNKNOWN_BILLING, SETTLED) and lock/reconciliation rules **before** exposing provider calls. Never automatically fall back to another provider and accidentally incur a second charge.

## Operator configuration contract (private staging only)

\`\`\`text
WORKSPACE_AUTH_MODE=oidc
MAT_GLOBAL_AI_ENABLED=1
MAT_GLOBAL_AI_EGRESS_APPROVED=1
MAT_GLOBAL_AI_CROSS_BORDER_REVIEWED=1
MAT_GLOBAL_AI_PROVIDER_TERMS_REVIEWED=1
MAT_GLOBAL_AI_COST_RESERVATION_REQUIRED=1
MAT_GLOBAL_AI_ALLOWED_PROVIDERS=OPENAI,ANTHROPIC,GOOGLE,MISTRAL,DEEPSEEK,QWEN_INTL

MAT_GLOBAL_OPENAI_MODEL=<reviewed-model-id>
MAT_GLOBAL_OPENAI_API_KEY=<vault-secret>
MAT_GLOBAL_ANTHROPIC_MODEL=<reviewed-model-id>
MAT_GLOBAL_ANTHROPIC_API_KEY=<vault-secret>
MAT_GLOBAL_GOOGLE_MODEL=<reviewed-model-id>
MAT_GLOBAL_GOOGLE_API_KEY=<vault-secret>
MAT_GLOBAL_MISTRAL_MODEL=<reviewed-model-id>
MAT_GLOBAL_MISTRAL_API_KEY=<vault-secret>
MAT_GLOBAL_DEEPSEEK_MODEL=<reviewed-model-id>
MAT_GLOBAL_DEEPSEEK_API_KEY=<vault-secret>
MAT_GLOBAL_QWEN_INTL_MODEL=<reviewed-model-id>
MAT_GLOBAL_QWEN_INTL_API_KEY=<vault-secret>
\`\`\`

**These are config names and examples, not instructions to provision paid accounts.** Configure only one approved provider at a time initially; enable a second only after separate data-processing/cost/quality acceptance. Do not add secrets to GitHub or Render's public static site. The six flags are an *additional* developer gate, not independent authorization evidence.

Data-processing and sovereignty requirements: document provider terms, retention, training, data-location claims and permissions per tenant and per data class, including Nigeria NDPA and other applicable country-specific law. Never promise EU/UAE/Qatar/Nigeria residency merely because the URL is regional. Do not transmit personal, regulated or confidential customer data before appropriate authorization.

## Source-only acceptance

\`\`\`bash
PYTHONPATH=apps/api pytest -q tests/test_p2_053_global_models.py
\`\`\`

Tests simulate all six HTTPS connections and validate wire shapes, consent/budget denial, endpoint injection denial, normalization, token accounting, tool-call rejection and fail-closed response handling. **No paid external API was called**. Exact-commit runner results still require verification because issue #100 has repeatedly caused \`steps:null\` failed workflows.

## Release dependencies

- PR #110 (P2-052 task engine) is draft and unmerged. This adapter is stacked on it, also draft. Do not merge or deploy independently to public \`main\`.
- Atomic PostgreSQL/ledger reservation and cost-accounting worker, idempotency and anti-double-charge evidence.
- Operator-approved provider accounts and secret storage, country-by-country service eligibility, retention and data transfer review, provider policy and pricing acceptance.
- Private OIDC/MFA/staging restricted DB and signed service admission; real provider test against explicitly authorized bounded billing with actual output and reconciliation.
- Real independent tests, secure logs, redaction, rate limits, abuse and quality evaluation.
- Separate user-facing image/video/voice model adapters; this is strictly **text generation**.

## Official provider references

- OpenAI: https://developers.openai.com/api/reference/resources/responses/methods/create
- Anthropic: https://platform.claude.com/docs/en/api/messages/create
- Google Gemini: https://ai.google.dev/api/generate-content
- Mistral: https://docs.mistral.ai/getting-started/quickstarts/studio/activate-and-generate-api-key
- DeepSeek: https://api-docs.deepseek.com/
- Qwen/Alibaba Cloud International: https://help.aliyun.com/en/model-studio/base-url
