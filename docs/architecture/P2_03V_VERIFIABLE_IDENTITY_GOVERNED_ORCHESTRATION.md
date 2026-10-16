# P2-03v — Verifiable Test Actors & Governed Intelligence Orchestration

**P2-03v is a SOURCE-ONLY SECURITY REHEARSAL** stacked on draft PR #83. It is not an OIDC integration, authenticated production users, agent runtime, SaaS subscription, real-data store or authorized operational service. No live AI inference, Meta API, outbound publishing, external tools or hosting changes.

## Source contract and tests

- `apps/api/app/synthetic_governed_orchestration.py`: transactional, disposable **SQLite WAL + synchronous FULL** state machine under a restricted OS temporary directory. Accepts only the four validated P2-03u fictional project templates; plans are bound to the **SHA-256 of the project, full five-node typed graph and source fixture digest**, avoiding approvals for a subsequently changed plan.
- Reuses the existing P2-03t Ed25519 **signed-test-actor** verification (exact issuer, audience, expiration and pinned public key). Every operation re-verifies test claims and checks a durable per-tenant token revocation ledger.
- **Independent roles:** `tenant_admin` acting as the original workflow owner can create a draft and approve it once; a separate `reviewer` actor must approve the same immutable plan. Role reassignment or signing a reviewer token for the same person does not bypass separation. `auditor` is read-only and may verify the audit chain.
- **Lifecycle:** DRAFT -> OWNER_APPROVED -> SECURITY_APPROVED -> SIMULATED (synthetic internal steps only); revocation moves impacted plans into an irreversible REVOKED state. An operator cannot promote a draft directly to runnable or impersonate the reviewer; sessions are checked in a serialized transaction.
- **Tools:** exactly three *fictional, virtual* review identifiers are available (`ANALYZE_SAMPLE`, `GENERATE_REVIEW_PLAN`, `SUMMARIZE_EVIDENCE`). Those record a review decision only. `SEND_WHATSAPP`, `POST_INSTAGRAM`, shell commands, web requests, charging customers, actual model inference and every unrecognized tool are denied even after both approvals. There is intentionally **no code path to execute a live tool**.
- **Persistence, revocation and recovery:** SQLite data and per-tenant SHA-256-chained audit entries survive process restart; a revoked signing session invalidates existing approvals; externally provided audit head checkpoints detect changes; the SQLite online-backup API creates a consistent disposable snapshot which tests reopen to verify state and audit integrity. An authenticated tenant administrator cannot export a disposable database containing another tenant's records; multi-tenant recovery must be a separately approved operator function. No production backups, encrypted file store or RPO/RTO claims.
- **Attack tests:** role escalation, token signature/audience/expiration, cross-tenant access, same-actor reviewer, approval replay, unauthorized tools, revoked tokens, stale architecture, audit modifications, transaction rollback, backup/restore, unsafe DB paths and synthetic-only safety flags.

`.github/workflows/p2-03v-governed-intelligence.yml` independently exercises P2-03v alongside earlier P2-03u graph and P2-03t Ed25519/source-quality tests. P2-03u's public `/intelligence/` workbench remains a source-only illustration, **not an authenticated review console**.

## Critical limitations

**There is no independently verified live identity.** A test-verified signature does not prove an employee's legal identity, an enterprise OIDC/MFA session or the user's current team membership. P2-03v deliberately cannot issue real identity claims and does not trust a browser-exported plan as permission.

The simulated SQLite authorization and audit model is not tenant-isolated at PostgreSQL RLS level. The separately tested P2-03s/t disposable PostgreSQL controls remain a prerequisite. Strongly verified staff identities, separate key stewardship, revocation events from an enterprise IdP, durable approval state in private Postgres, consent, rotation, encryption-at-rest/KMS, incident recovery and immutable external audit anchoring must be added in an approved and secured private staging environment **before any genuine customer data**.

These tests do not establish that actual AI-generated content is correct, that LLM tools are safe, that paid marketing is allowed, that a workflow has a customer, or that any financial improvement has been achieved.

## Operational release gates

Foundation Phase 01 remains **3/9 verified**; Phases 02 and 03 remain **operational NO-GO**. No Render deployment, DigitalOcean provisioning, Meta/WhatsApp account access, subscriptions, customer records, real identity-provider credentials, production schema migrations, messaging, publishing or charges are permitted by this PR.

## Follow-on engineering: P2-03w

When private staging is explicitly approved and funded as needed: bind these workflows to a real OIDC identity provider (issuer/audience, JWKS refresh, nonce/state, MFA and token revocation), real tenant membership and separate principal-role authorization, replay-resistant signed approvals, purpose-scoped tool tokens, safe model-evaluation sandbox, durable PostgreSQL audit and outbox, reversible operator kill switch, independently verified staging backup/restore and end-to-end failure tests. External execution and customer data remain disabled until each operational gate is met.
