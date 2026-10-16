# P2-03p — WhatsApp Lead Generation (Policy-First Source Lab)

**Classification:** SYNTHETIC_SOURCE_ONLY · NO_GO · NOT DEPLOYED

Meta policy: https://whatsappbusiness.com/policy/ (updated September 23, 2026).
Official CTWA guidance: https://whatsappbusiness.com/resources/resource-library/lead-generation-strategies-smb-whatsapp/

## One connected MetaAutomate product

- Growth Autopilot: inbound lead source and proposed response eligibility.
- CRM Intelligence: synthetic qualification, consent, opt-out and review queues.
- Marketing Intelligence: campaign evidence needed, never assumed ad attribution.
- Workflow Automation: human-review-only routing; no dispatch.
- Business Value Intelligence: potential qualified-lead costs and conversions only after real evidence and authorization.

## Four-step customer journey

1. **Acquisition:** CTWA ads, owned website links, QR codes and direct business links. A click is NOT a chat, contact, lead, consent or confirmed ad attribution.
2. **Qualification:** four voluntary non-sensitive questions (interest, broad budget band, location band and timeline). No personal contact data in the demo. Answers never authorize marketing.
3. **CRM review:** synthetic lead ID, source label, qualification bands and separate marketing/utility consent flags. Opt-out overrides all messaging. Real referral metadata requires independently authenticated webhook evidence; claimed campaign IDs are not verified.
4. **Human handover:** prepare an internal review queue. Real automated replies must have an accessible escalation channel. No API or real sales agent is connected.

## Policy controls

- Non-template **service responses** are permitted inside the 24-hour window from the most recent real customer message; merely clicking a link does not open that window.
- Outside that window, Business Platform outreach requires approved message templates. This engine only proposes review and requires appropriate purpose-specific opt-in, a template with matching purpose, and no opt-out before proposing that review.
- Marketing cannot inherit a utility opt-in or permission from a one-off inbound service question.
- Opt-outs supersede consent and templates. Do not automate unsolicited cold followups.
- A WhatsApp sender identifier is not real-world identity verification.
- No universal 98% message-open claims, causal conversion claims or profit guarantees.
- Live WhatsApp Business Platform may charge per delivered messages depending on country, type and effective pricing. No free live usage is guaranteed.
- No unofficial WhatsApp Web bot, contact scraping, number harvesting, purchased lists, policy evasion or unauthorized mass messaging.

## Future security and privacy requirements (all blocked)

Official business ownership and lawful platform access; provider-signed webhook verification; session and origin provenance; idempotency, anti-replay and tenant isolation; legal consent notices and revocation ledger; privacy notices and lawful retention/deletion; verified template authorization; human escalation; abuse and budget rate limits; independently reviewed security and operational gates.

No real numbers, messages, CRM writes, provider API calls, templates, tokens, public release or subscriptions are used here.

## Source tests

- python -m pytest -q tests/test_synthetic_whatsapp_lead_pipeline.py
- python scripts/build_whatsapp_lead_contract.py --check
- node --check apps/site/intelligence-lab/whatsapp/data.js
- node --check apps/site/intelligence-lab/whatsapp/whatsapp.js
- python scripts/verify_whatsapp_leads_browser.py

Browser tests cover desktop 1440px and mobile 390px/360px, opt-out, 24-hour service decisions, unapproved templates and local qualification. This source-only PR does not authorize release or production operations.
