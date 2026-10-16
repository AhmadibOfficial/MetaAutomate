# P2-03j — Goal-driven Business Growth Automation Engine

**Engineering status:** Source-only development, operational NO-GO. Builds on the accepted P2-03h business source and P2-03i branded customer workspace. Public-facing copy should remain professional, helpful and clear about feature availability. This source engineering document uses explicit synthetic/test terminology to prevent accidental activation or misleading claims.

## Five coordinated product building blocks

1. **Business goals → workflow priorities**. The engine accepts only validated business-specific source scenario goals, targets and trigger types. Academy targets contribution after workflow and marketing costs, prioritizing opt-in learning journeys; Bespoke prioritizes repeat-order activity and post-delivery care.
2. **Event-driven orchestration → review queue**. A pure function maps each synthetic event to a goal relevance, provider contract, human-review state and deterministic idempotency preview. Checkout-recovery events are suppressed in favor of Selar native recovery; opt-in not recorded means marketing is suppressed. Human approval is mandatory and cannot be granted or bypassed through this module.
3. **Provider integration contracts**. Proposed Selar, Metricool, email, customer messaging and subscription billing capabilities are explicitly **CONTRACT_ONLY**. No provider adapter, credential access, sign-in, OAuth callback, webhook receiver, API route, network request, auto-publication or delivery exists. No assertion that any commercial provider permits a particular scope. Provider terms, scopes, pricing, data processing and consent permissions need independent validation before implementation.
4. **Financial measurement and goal gap**. Source illustrations track gross sales, unit variable costs, marketing spend and proposed workflow operating costs separately. Distinct buying journeys, session counts and enquiry counts are explicitly synthetic; the calculated basis-point conversion is **not a real conversion rate or causal uplift**. After-cost contribution is not net profit: rent, taxes, fixed overheads and other omitted expenses remain unknown. Real customer revenue, realized ROI and incremental impact are deliberately null/unproven.
5. **Subscription readiness without activation**. Two plan **research tier identifiers** exist only as schema values, not prices, trials, charges or entitlements. Six required gates prevent treating source validation as commercial readiness: (a) Foundation release authorization; (b) authenticated tenant isolation; (c) verified consent/provider authorization; (d) durable idempotency/audit; (e) measured incremental customer value; (f) secure billing entitlements and commercial approval.

## Deterministic reference scenarios

- Academy: 40 synthetic sessions, 7 enquiries, 2 purchase-order records across one distinct buying journey. Modeled contribution after variable costs, marketing and workflow costs: 25,000 − 8,000 − 2,500 − 600 = **13,900 demo credits**, target 20,000, remaining 6,100.
- Bespoke: 25 synthetic sessions, 5 enquiries, 2 purchase-order records across one distinct buying journey. Modeled contribution: 35,000 − 23,500 − 1,500 − 500 = **9,500 demo credits**. The chosen goal is 3 repeat-order records; illustration currently has 1, remaining 2.
- Both workspaces generate four review-only proposals, one checkout-recovery provider suppression, one missing-consent suppression and one duplicate/replay preview. **No proposal is approved, delivered, activated or charged.**
- All amounts use internal **DEMO_CREDITS**; public UI may use an explicitly illustrative $ presentation but never imply exchange conversion, real transactions or earned customer results.

## Source validation

The validator rejects unknown/extra fields (including PII/credentials), invalid provider roles or execution flags, disabled consent policy, unsupported workspace, goal type/trigger mismatch, bad amounts and negative/float/bool inputs, session/enquiry inconsistencies, cross-workspace or duplicate replay IDs, mismatched source orders, repeated JSON keys, excessively large JSON and real-world currencies. It validates all workspaces **before** filtering the read-only report. Deterministic replay prevention here is a **preview**, not secure durable idempotency. The platform cannot process real users without a genuine authenticated authorization/consent architecture.

## Verify (stdlib source engine; no subscriptions required)

    python -m pytest -q tests/test_synthetic_growth_orchestrator.py
    python scripts/verify_growth_orchestration_source.py \
      --report artifacts/validation/p2-03j-growth-orchestration.json

GitHub CI runs the same verification and uploads a reproducible JSON report. This is source evidence only; release gates remain unchanged.

## Release separation and next engineering decision

- PR under review stays draft and unmerged. No new public site change, Render deployment or migration is needed.
- Existing public Growth Autopilot preview remains its separate website milestone. This engine is **not connected** to the public website; do not claim a live customer or production automation feature.
- Foundation Phase 01 remains **3/9 verified**, F04–F09 remain blocked. Phase 02 operational and Phase 03 live execution remain NO-GO. Keep the 19-entry capability registry, accepted lifecycle event LCE-0001, 33 disabled legacy capability IDs and cross-sector contract unchanged. Do not promote a capability solely from source tests.
- Future staging proof must verify tenant-scoped auth, least-privilege provider integration, revocation, consent logs, quiet hours/rate limits, enduring dedupe and event replay rejection, incident/audit/recovery, data retention/deletion, subscription entitlements and economics. No production billing or client access prior to separate owner approval.
