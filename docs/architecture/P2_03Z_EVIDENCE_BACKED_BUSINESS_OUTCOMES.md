# P2-03z — Evidence-Backed Business Outcomes (source-only implementation)

**Purpose:** establish a *real-data-capable*, evidence-backed financial measurement workflow instead of making unsupported income claims. **Not currently approved to process real customers.**

## Current status

This milestone extends the actual private MetaAutomate PostgreSQL/FastAPI application. It is **not** another fictional model-ranking or static visualization. A future properly approved, real-staff-authenticated business can submit **aggregated financial period figures** with explicit consent and source-document digests; a distinct account owner/administrator reviews them; the system then computes a historical before/after comparison. Merely submitting numbers or hashes **does not authenticate the underlying bookkeeping, obtain verified consent, or prove MetaAutomate caused the difference**.

The current public Render service remains a separate **static website**, and the private application is not deployed.

## What is implemented

- **Production-shaped PostgreSQL migration 016**: organization-scoped immutable `pilot_outcome_periods` and `pilot_outcome_reviews` with composite tenant keys, forced RLS, original submitter membership FK, reviewer membership FK, independent reviewer trigger, required role checks, source-hash matching, immutable receipts, least-privilege runtime SELECT/INSERT only, and audit-event inserts. **Migration 016 is unapplied to owner's databases**, even if tested on temporary CI Postgres.
- **Authenticated FastAPI router `/v1/pilot-outcomes`**: creation of bounded aggregate-only observed baseline/current periods, all values exact integer *minor currency units*; idempotent write receipt bound to original actor and content hash; restricted roles; explicit aggregate consent *claim* and SHA-256 of external consent/source records; review by a different OWNER/ADMIN; read-only two-period descriptive difference for distinct reviewed, non-overlapping periods in one organization and currency. Source originals stay in an independently approved secure store, not raw or uploaded to this API.
- **No false profit claims**: comparison returns contribution after **identified costs**, never net profit, causally attributable revenue, proven ROI or true unambiguous value delivered. Results include `source_documents_independently_authenticated=false`, even after a human marks `EVIDENCE_CHECKED`. Evidence hashes protect integrity of the stored claim, not source authenticity.
- **Default OFF**: backend routes register only if explicitly set `MAT_PILOT_OUTCOMES_ENABLED=1` in a privately authenticated `WORKSPACE_AUTH_MODE=oidc` runtime and a separate HTTPS `MAT_PILOT_ACCEPTANCE_RECORD` exists. **These environment checks are operational tripwires only**, not cryptographic authorization or proof of F04/F05. The deploy operator must inspect actual independent acceptance before enabling anything. Public site never imports this API.
- **Disposable real PostgreSQL integration**: CI migrates a new PostgreSQL 16 instance, creates fictional tenants/users, exercises actual RLS queries, submission, replay collision, self-review failure, immutable mutation failure, independent receipt and noncausal comparison. It does not touch the owners' Kali database or customer staging.
- **Operational truth report**: `scripts/verify_p2_03z_pilot_readiness.py` confirms the source implementation, reconciles the Foundation ledger and refuses `--require-operational-go`.

## Data model boundaries

A period contains: project identifier, BASELINE/CURRENT, observed start/end dates, currency, gross sales, variable cost, marketing spend, processing fees, fulfillment cost, software cost, refunds, completed order count, approved evidence source kind (`BOOKKEEPING_EXPORT`, `POS_SUMMARY`, `MANUAL_AGGREGATE`), source SHA-256, consent SHA-256, signer ID, input receipt hash and idempotency key.

It contains **no customer names, lead records, phone/email addresses, raw receipts, model prompts, provider API credentials, bank details or transaction-level payments**. Figures must be reviewed with the business's accountant or authorized representative before any customer-facing claim. Do not add a generic metadata field or unreviewed blob uploads.

## Operational acceptance prerequisites

1. **F04:** private `main` enforced with required `Release Evidence Gate`, independent reviewer and witnessed failed-check merge denial.
2. **F05:** approved private staging host, region, security perimeter, cost ceiling, provider-account review and a separate database.
3. **F06:** real OIDC Authorization Code/PKCE login, MFA, directory provisioning and secure ingress; independently verified staff and tenant roles, revocation/expiry/CSRF tests.
4. **F07/F08:** off-host encrypted recovery, separate witness, tenant-isolation evidence, worker/AI network egress prohibition, audit/integrity tests, monitoring and emergency suspension.
5. **Before F09 pilot:** verified business owner consent **and its actual source artifact**, data protection/retention agreement, authorized accountant review, documented baseline/current collection windows and independent customer success measures. A source digest alone is not adequate.
6. **Never** mark measured contribution change as `net_profit`, `platform_generated_income` or `proven_roi` without external evaluation and a controlled causal design.

## Risk notes and limitations

- An observed period with all numeric fields is not actual authenticated accounting data. A fake issuer or self-reported operator acceptance reference can be supplied if an administrator bypasses operational process. Source controls alone cannot replace independent approval.
- Model-based decisions and real agent integrations remain off; this is a human-driven, narrow financial measurement and evidence intake component.
- PostgreSQL RLS is a second line of defense, not an identity provider; authentic sessions and least-privilege database roles are required.
- Pilot comparisons are descriptive differences of *identified* amounts and may omit tax, inventory changes, fixed expenses, financing, seasonal trends or external market effects.
- Because Phase 01 remains **3/9 verified** and F04–F09 remain **blocked**, the API cannot be made generally available and customer data cannot be collected.
- Code in this source branch is **unmerged and undeployed**, and the official Foundation evidence register remains unchanged. PR #89 is a separate, draft F05 rehearsal.

## Development-only tests

```sh
python -m pytest -q tests/test_p2_03z_pilot_outcomes.py
python scripts/verify_p2_03z_pilot_readiness.py
# expected failure:
python scripts/verify_p2_03z_pilot_readiness.py --require-operational-go
```

The CI workflow also runs the separate PostgreSQL-backed tests against an ephemeral database and reports NO-GO. No hosting subscription is required to run the already available CI.
