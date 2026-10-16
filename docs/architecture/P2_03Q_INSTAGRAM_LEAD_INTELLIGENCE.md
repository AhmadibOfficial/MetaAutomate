# P2-03q — Instagram Lead Intelligence, source-only

**NO-GO / no credentials / no connected account / no customer messages / no real lead data / no publication.** This is an offline, no-subscription addition to the existing MetaAutomate CRM, Marketing Intelligence and Growth Autopilot modules.

## Supported product paths

1. **Instagram Lead Ads instant forms:** submitted forms enter a human CRM review queue. Merely opening a form is not lead capture. Form-submission data needs official Meta Lead Ads permissions, Meta App Review/Lead Access Manager authorization and secure authenticated retrieval. A form does not create an Instagram DM conversation or permit marketing messages without the appropriate basis.
2. **User-initiated Instagram Direct messages:** a verified inbound DM can be reviewed during the platform's standard 24-hour messaging window, not scraped from followers.
3. **Owned-media comment keywords:** the official API's private-reply mechanism is a *single restricted private reply* to an eligible comment, commonly within seven days of the comment on owned media. It does not grant indefinite conversation rights. Prior use, comment age, media ownership, authorization and current Meta restrictions must all be verified. No automatic comment reply is active.
4. **Link-in-bio:** a click is not a submitted lead, opt-in or opened DM.
5. **Click-to-Direct ads:** Meta's updated Messenger/Instagram policy notes ad-origin conversations *may* allow up to seven days from the first user message after a qualifying advertisement. The event must be authenticated and verified against current Meta policy before even proposing messaging. This source lab only displays human-review labels. It never sends.

## Official policy/reference locations

- https://developers.facebook.com/documentation/instagram-platform/private-replies
- https://developers.facebook.com/documentation/business-messaging/messenger-platform/policy
- https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login/messaging-api
- https://developers.facebook.com/documentation/ads-commerce/marketing-api/guides/lead-ads/retrieving
- https://developers.facebook.com/docs/graph-api/webhooks/getting-started/webhooks-for-leadgen/

## Source architecture

- **Core:** strict JSON fixtures and parsing in apps/api/app/synthetic_instagram_lead_pipeline.py; constant-time raw-body X-Hub-Signature-256 verification in apps/api/app/meta_webhook_signature.py.
- **Data provenance:** the standalone source-generated browser contract is checked against the validated Python fixture.
- **Privacy:** no personal names, handles, Meta IDs, phone numbers, email addresses, raw messages, access tokens or webhook payloads are stored in the fixture.
- **Views:** accessible, white-theme static preview at apps/site/intelligence-lab/instagram/, linked from Growth Autopilot, CRM and Marketing Intelligence views.
- **State:** the frontend changes only hypothetical qualifications in the browser. No cookies, localStorage, server requests, public website rollout or outbound messaging. No production app webhook routes.
- **Cryptographic boundary:** the Meta signature helper verifies bounded raw-body HMAC with constant-time comparison. This is NOT a live webhook receiver, durable replay defense or permission check. Tenant identity must be resolved from verified Meta account mappings; use a durable deduplication ledger, strict retention controls and authenticated actor rights before enabling real data.
- **Human handover:** source-only review priority labels. No actual sales-agent identities or queues, and no approval for dispatch.

## Testing

- python -m pytest -q tests/test_synthetic_instagram_lead_pipeline.py tests/test_meta_webhook_signature.py
- python scripts/build_instagram_lead_contract.py --check
- node --check apps/site/intelligence-lab/instagram/instagram.js
- python scripts/verify_instagram_leads_browser.py

CI produces synthetic screenshots at desktop 1440px and mobile 390/360px; review with a real screen reader remains outstanding.

## Operational gate — still explicitly blocked

Connect Meta only after independent approval of authorized professional business accounts; approved permissions; credential vault and token rotation; correctly configured TLS/webhooks; verified signatures and idempotency; tenant/workspace isolation; lawful privacy notices and minimization; secure encrypted CRM storage and deletion; opt-in evidence and opt-out handling; human handover access; billing/ad-budget ceilings; independent security review; and Phase 01–03 release gates (Foundation 3/9, operational NO-GO).

No live WhatsApp or Instagram integration, customer activation, advertising, paid subscription, production database migration, social publication or Render deployment is authorized by merging this source feature.

## Business measurements

Track qualifying conversations, submitted forms, response times and agent decisions only from verified permissioned sources. Do not attribute conversions or profit from view counts, reactions, keyword comments or provider-unverified campaign tags. Evaluate incremental commercial outcomes separately with reliable event definitions, costs, comparison periods and uncertainty.
