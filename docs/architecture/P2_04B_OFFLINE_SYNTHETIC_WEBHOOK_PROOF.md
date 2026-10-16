# P2-04b — Offline synthetic webhook-proof verification

**Status: source-only draft. NO DEPLOYMENT.** This milestone follows P2-04a but **does not depend on PR #32**: it branches from the currently merged `main` and contains no P2-04a code. PR #32's independent review / merge and branch-protection controls remain **postponed, not waived**. Phase 01 Foundation remains **3/9, NO-GO**.

## Intent

Explore how a future integration could reject forged or replayed inbound callbacks, using only invented data and fixed fixture inputs. This is **not** a webhook receiver. There is no registered API endpoint, network listener, worker, scheduler, outbound request, provider SDK, database migration, persistent queue, secret manager, signing service or actual business record.

`apps/api/app/synthetic_webhook_proof.py` provides a deliberately unbound in-memory verifier with:

1. HMAC-SHA256 over **the original raw bytes** of a bounded UTF-8 JSON fixture, domain-separated and bound to the supplied demo tenant UUID and key ID.
2. Synthetic-only key IDs, an ASCII `DEMO-KEY-MATERIAL-` test-key convention and at most two demo keys per tenant. The keyring is passed into the object in memory; no environment secrets are read and no provider keys are used. A naming convention **cannot attest that the material is truly synthetic**; never insert live credentials.
3. Exact allowlisted flat JSON shape with duplicate-key rejection, no extra metadata and no arbitrary JSON payloads. A deterministic `DEMO-TENANT-` marker, allowlisted scenarios and `DEMO-EVT-` IDs enforce demo-only schema syntax.
4. Freshness checked against a **caller-supplied logical tick**, at most five ticks old and one tick ahead. This is not a trusted wall-clock check.
5. Thread-safe, in-memory, tenant-partitioned event-ID replay rejection. Maximum 32 distinct accepted demo events per tenant, 128 per verifier object; once full, reject rather than silently evict proof IDs. Duplicate deliveries are always denied.
6. A minimal frozen synthetic proof with `executed=false`, `persisted=false`, `actual_business_data=false`, `webhook_endpoint_available=false`. No delivery event is dispatched or job scheduled.

HMAC verification uses `hmac.compare_digest` for signature comparisons. Failure returns one generic `DemoWebhookDenied` message, not key existence, detailed signature mismatches or payload content.

## Trust and safety boundaries

- **Tenant UUIDs are NOT authenticated.** The enclosing product must eventually bind the tenant to a verified session/service identity; passing a UUID does not grant product access or prove origin.
- **Fixture HMACs do NOT constitute provider-signed webhooks.** A real integration would need a per-provider signature specification, inbound transport identity, raw-body handling and key rotation, trusted timestamps, durable distributed replay prevention and incident-response controls.
- This proof has no real clock, no persistent replay cache, no cross-process synchronization, no public HTTP rate limit, no real key rotation, no receipt verification, and no webhook acknowledgement. Restarting the object loses deduplication.
- This module must remain **unimported by `apps/api/app/main.py`**, unrouted and unable to ingest customer data. A static test checks the absence of common network/DB imports and route wiring; it is not a comprehensive sandbox or proof of arbitrary code safety.
- **Never** reinterpret a signed `DEMO-` event as authorization to write, deliver, spend, modify inventory, sync customer data, or merge user identities with OneCall.

## Local acceptance

From the user's existing Kali checkout and activated `~/.venvs/metaautomate-p204a` environment:

```bash
cd ~/MetaAutomate
git status --short
gh pr checkout 33
git rev-parse HEAD
PYTHONPATH=apps/api python -m pytest -q -p no:cacheprovider \
  --import-mode=importlib tests/test_phase02_synthetic_webhook_proof.py
```

Only after passing focused tests at the exact PR head and GitHub's full CI should this be considered source-tested. No local PostgreSQL migration, Docker service, DigitalOcean, Render, paid product, real provider or credentials are required.

## Beyond P2-04b (not implemented)

- Actual approved webhook contract and receiver adapters for named providers
- Transport trust + provider-specific signature/nonce requirements + trusted time
- Durable, transactional tenant-scoped replay/idempotency storage
- Cross-process rate limits, bounded backpressure, circuit breakers and queue lease handling
- Secure secret rotation and revocation, real provider acknowledgements and redacted incident observability
- Integration with P2-04a after that draft passes its independent review and merge gates

**Release:** PR #32 remains draft/unmerged and independent review stays unresolved. P2-04b must also remain a **draft, unmerged** until separate source review and local acceptance. Phase 01 (3/9) remains **NO-GO**. These controls are postponed, **not waived**. No subscriptions or cloud infrastructure are activated.
