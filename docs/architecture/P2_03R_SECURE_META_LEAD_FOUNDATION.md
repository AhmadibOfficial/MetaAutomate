# P2-03r — Secure Meta Lead Integration Foundation

**Status:** SOURCE-ONLY SECURITY FOUNDATION, NO LIVE META INTEGRATION, NO PRODUCTION GO.

Merged dependency: Instagram PR #79. This incremental PR is distinct and remains unmerged until an explicit approval.

## Shared business scope

MetaAutomate Growth Autopilot, CRM, Marketing Intelligence and human Workflow Automation share the following channels.

| Channel | Acquisition and signed intake boundary | Messaging boundary |
|---|---|---|
| Facebook | Submitted Lead Ads form produces a leadgen webhook metadata event; real lead details require authorized separate retrieval | Form submission is not a DM or general marketing consent |
| Instagram | Official professional account DM/comment/lead event integration | Respect verified inbound window and one-private-reply restrictions |
| WhatsApp | Approved WABA webhook event and verified business account mapping | Purpose-specific consent, opt-out and template/time-window controls |

**Do not assume a Facebook Page is connected** because the user has approved a code merge. Facebook and other social providers remain excluded from live publishing until individually verified.

## Implemented trust boundary

- `apps/api/app/synthetic_meta_lead_federation.py` verifies Meta-style **raw-body HMAC SHA-256 signatures first**, using the previously implemented `meta_webhook_signature.py` primitive, before even decoding JSON.
- The trusted, immutable synthetic registry binds each example Page, Instagram business account and WABA to exactly one internal demonstration workspace. The untrusted webhook body cannot choose its own tenant.
- Strictly bounded JSON envelopes, exact allowlisted event fields, strict types, duplicate field and event rejection, and rejection of customer messages, phone numbers, names, emails, tokens and profile contents.
- Facebook Page leadgen event carries only the sample form and lead IDs. **Lead retrieval is not implemented**; actual field-level lead data cannot be fetched.
- Messages for Instagram and WhatsApp carry only generated event IDs and no text, contacts or account owner identity.
- In-memory `SyntheticMetaReviewLedger` deduplicates samples, creates human-review-only tasks, supports fictional agent assignment and purpose-specific synthetic consent review with a local hash-linked history. A revoked example cannot silently become granted.
- Permission checklists for the three channels always return NO-GO—even when caller-supplied flags say they are complete. An independent Meta grant check and actual operator authentication remain absent.
- A source-only **unapplied** PostgreSQL 16 tenant-isolation blueprint proposes explicit tenant keys, row-level security with FORCE, per-tenant deduplication, reference-only review history, outbound-disabled tasks and closed privileges by default. The blueprint is not an applied or verified migration, an encrypted PII vault, or a running CRM.
- The static white-theme Facebook view illustrates the difference between opening a prefilled form and submitting it. It is generated from signed simulated examples, not actual customers or advertising. The view is linked from the existing Growth, CRM and Marketing sections.

## What *cannot* be claimed

- A valid synthetic HMAC is **not** live Meta identity or webhook ownership authentication. Live webhooks require separately provisioned Meta app secrets, official event signatures, independently verified account bindings, HTTPS, replay defense, provider retries and threat-reviewed ingress.
- No real user consent exists. Consent-review history contains synthetic evidence references, not compliant customer consent records. Actual consent must include user choice, purpose, timestamp, disclosure language, source and independent lawful-basis assessment, protected storage, withdrawal propagation, expiration and deletion support.
- No real human agent is authenticated, and no real conversation, CRM record, message, ad, form submission, billing operation or external API request is performed.
- The SQL blueprint is NOT a source of deployment authority: enforce RLS with real restricted roles and authenticated tenant context; demonstrate cross-tenant isolation and backups on approved private staging before migration.
- In-memory deduplication and hash chains **do not** provide durable anti-replay, tamper-proof logs or resilient audit records.
- Form prefill does not prove contact identity, consent or completed submission. Reporting ad reach, clicks or submitted forms as closed sales is prohibited without independently reconciled evidence.

## Future operational implementation gates

1. Meta Business ownership and app review, valid permitted scopes and Page lead access, verified professional IG account, verified WABA ownership; separate authorization and credential vault with rotation.
2. Authenticated HTTPS webhooks with secret/rotation and source mapping, durable replay/idempotency ledger, redacted immutable security logs and queueing with retry/backoff.
3. Audited tenant user authentication, scoped roles, encrypted customer-data vault with consent evidence, retention, deletion, subject access and cross-tenant adversarial tests.
4. Instagram/WhatsApp compliant reply-window and template verification; explicit unsubscribes and consent withdrawal across every channel. Human approval, inbox ownership, escalation, SLA and real-time abuse controls.
5. Official Meta lead retrieval with advertiser-approved data access, only for leads who actually submitted a form; no scraping, contact harvesting or unapproved automated messages.
6. Approved cost ceiling, independent security testing, live platform permission evidence and operational release approval. Foundation Phase 01 remains 3/9 verified; Phase 02/03 remain NO-GO.

No hosting subscriptions, Meta ad spend, DigitalOcean, Render deployment, migration or customer activation are authorized by this increment.

## Source-only verification

- `python -m pytest -q tests/test_meta_webhook_signature.py tests/test_synthetic_meta_lead_federation.py`
- `python -m pytest -q tests/test_synthetic_instagram_lead_pipeline.py tests/test_synthetic_whatsapp_lead_pipeline.py`
- `python scripts/build_meta_facebook_lead_contract.py --check`
- `node --check apps/site/intelligence-lab/facebook/facebook.js`
- `python scripts/verify_facebook_leads_browser.py` (Playwright Chromium; 1440, 390 and 360 pixel screen widths).
- Source-only GitHub workflow `.github/workflows/p2-03r-meta-leads.yml`.

## Primary references

- https://developers.facebook.com/docs/graph-api/webhooks/getting-started/webhooks-for-leadgen/
- https://developers.facebook.com/docs/marketing-api/guides/lead-ads/retrieving/
- https://www.facebook.com/ads/leadgen/tos
- https://developers.facebook.com/docs/graph-api/webhooks/getting-started/
- https://whatsappbusiness.com/policy/
