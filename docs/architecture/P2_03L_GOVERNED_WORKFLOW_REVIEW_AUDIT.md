# P2-03l — Consent-First Workflow Review & Audit Lab

**Engineering status:** source-only, in-memory, non-operational. This is not a deployed automation service, a real authorization layer or a production audit solution.

## Why this is valuable

Businesses need more than automation suggestions. They need confidence that every customer-facing action is intentional, legitimate, explainable and measurable. This milestone prototypes **review lifecycle integrity**, a prerequisite to responsible business automation. It consumes the source-verified P2-03j goal-specific review proposals and applies a conservative decision process to strictly invented events.

## Behavioral contract

- **Synthetic review actions:** INSPECT, REVIEW_ACCEPT, REVIEW_DECLINE, REVOKE_CONSENT, ACK_PROVIDER_OWNERSHIP. Only local simulation; acceptance means \`REVIEWED_IN_SANDBOX\`, never approval to send.
- **Role gating:** VIEWER may inspect; OWNER and REVIEWER may mark a proposal reviewed or declined when its state allows it; OWNER alone may revoke example consent or note provider ownership. Role values are **not real authenticated identities**.
- **Consent change:** a revoked invented journey blocks every associated reviewable, reviewed or deferred proposal. Existing provider-owned native checkout recovery remains suppressed. Missing permission is never promoted into a review.
- **Provider duplication:** Selar owns its own checkout reminders. A note confirming conceptual ownership never calls or schedules anything.
- **Idempotency:** identical synthetic intent IDs with identical payloads produce one review record; reuse of an intent ID for a different instruction fails closed. A stale or second approval attempt is denied by precondition.
- **Traceability:** each accepted or denied *synthetic* instruction appends a deterministic SHA-256 hash-linked audit record. This is not signed, durable, immutable or tamper-proof. An integrity verifier rejects modified records in a given report.
- **Fail closed:** reject unknown workspaces/events (including cross-workspace references), goals, actors, unsupported verbs, extra keys, duplicate JSON fields and large/malformed payloads.
- **No live work:** no credentials, background job, customer contacts, email, account, stateful storage, database writes, provider API calls or messaging.

### Reproducible verification

\`\`\`bash
python -m pytest -q tests/test_synthetic_growth_review_lab.py
python scripts/verify_synthetic_growth_review_lab.py --report artifacts/validation/p2-03l-growth-review-source.json
\`\`\`

The \`MetaAutomate CI\` workflow runs both pytest (through its existing suite) and a dedicated source evidence gate for this component. Review the evidence before any source-only merge.

## Readiness separation

Existing static free explorer stays as it is; no website publication or additional payments. Foundation Phase 01 **3/9 verified**, blocked F04–F09. Phases 02–03 operational **NO-GO**. Real customer usage later requires authorized tenant identity, secure private staging, policy-reviewed consent and opt-outs, abuse and rate controls, isolated durable audit, rollback/recovery tests, provider lifecycle testing and independent release authorization. No subscription/billing and no new external actions are permitted by this change.
