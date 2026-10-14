# P2-05a — Offline controlled write-proposal foundation

**Status: source-only draft. No execution, no customer data, no provider.** Phase 01 remains **3/9 verified — NO-GO**. This branch comes from the currently merged `main`, **not** from the unmerged PRs #32–#36. Their independent review and enforceable private-repository branch protection are deferred, **not waived**.

## Business purpose

MetaAutomate should eventually be able to *prepare* an explicit proposal to update a CRM record or reconcile a financial record, without assuming it may *perform* the change. This rehearsal uses allowlisted invented scenarios only, no freeform customer data and no real provider operations.

The existing `contracts/domains/v1/operations.json` defines two **DRAFT, unbound** `propose_write` capabilities. P2-05a does not change, activate, or assign their scopes.

| Operation | Capability | Effect | Required future scope | Risk | DEMO review model |
|---|---|---|---|---|---|
| `business.crm.sync-proposal.v1` | BIZ-006 | `propose_write` | `business.crm.write` | moderate | One distinct demo reviewer |
| `business.finance.reconciliation-proposal.v1` | BIZ-012 | `propose_write` | `business.finance.write` | high | Two distinct demo reviewers |

Other domain operations such as `validate_only` and `read_external` are explicitly rejected. A test checks that the above metadata exactly matches the official machine-readable domain contract.

## Deliberate design

`apps/api/app/synthetic_write_proposals.py` contains `OfflineSyntheticWriteProposals`, a bounded in-memory object. No FastAPI import, API route, service worker, database query, provider SDK, file operations, network listener, payments or external credentials are added.

- `propose(tenant_id, operation_id, demo_scenario, demo_proposer, idempotency_key, tick=...)` accepts exactly the two allowlisted domain operation IDs and one of four hardcoded `DEMO-` scenario labels. It rejects arbitrary business bodies, clients, URLs, customer identifiers, real transaction payloads and unknown operation IDs.
- The caller provides a UUID **demo partition**, a `DEMO-ACTOR-` label, a `DEMO-IDEMP-` key and bounded integer **logical** tick. These are **not** authenticated identities, real-world human attestations, verified scope grants, wall-clock timestamps, or transaction IDs.
- A duplicate `(tenant_id, idempotency_key)` returns the original proposal/snapshot without charging history; a conflicting body/actor/operation or backward tick is rejected. No idempotency entry is evicted.
- The synthetic reviewer submits only `SIM_ENDORSE` or `SIM_DECLINE`, with an expected state version and a new DEMO reviewer label. A proposer cannot self-endorse, and the same DEMO reviewer cannot review a proposal twice.
- CRM: one simulated endorsement completes the **review rehearsal**. Finance: two *distinct* simulated endorsements are needed. A simulated decline is terminal. Concurrent stale-version attempts are rejected under a Python `RLock`.
- Demo review is permitted at a logical tick no later than **20 ticks after creation**. No scheduled expiry job exists; overdue reviews are rejected. A synthetic reviewed status `SIM_REVIEWED_NOT_AUTHORIZED` is **not an authorization grant**.
- Capacity is capped at 16 proposals per demo tenant, 64 proposals total, and 16 tenant partitions per object, never evicting records to silently re-admit old demo keys. Restart loses all history.
- Returned `SyntheticProposalView` objects are frozen, including tuple snapshots of the fake reviewer labels. **Every returned view**, including those with endorsements, carries `decision="DENY"`, `execution_authorized=false`, `executed=false`, `scope_verified=false`, `tenant_authenticated=false`, `human_approval_verified=false`, `provider_called=false`, `provider_receipt_verified=false`, `persisted=false`.

## Threat model and limits

Nothing in this source proves the person behind a DEMO reviewer label, the tenant UUID, the provider state, a real approval, account ownership, or possession of a legitimate write scope. Reviewer separation here is a **simulation rule**, not verified segregation of duties. There are no signatures, durable transaction locks, tenant-scoped database grants, paid provider accounts, authentic approval tokens, execution adapters, authoritative provider receipts, compensation or recovery workers.

For a future live implementation, identity and tenant must be derived from a trusted server-side principal; the independent human approval must be signed/bound to one exact effect and expiry; backend permissions, provider preflight, revalidation, transactional idempotency, execution receipts, evidence review, audit retention, and Phase 01 operational gates must separately pass. AI-generated prose can never serve as execution authority.

No AMBOY or OneCall product is granted execution access merely because these synthetic tests pass.

## Acceptance on the existing Kali clone

Check `git status --short` is clean before switching branches; preserve any uncommitted work rather than overwriting it. From `~/MetaAutomate`:

```bash
cd ~/MetaAutomate
git status --short
gh pr checkout 37
git rev-parse HEAD
source ~/.venvs/metaautomate-p204a/bin/activate
PYTHONPATH=apps/api python -m pytest -q \
  -p no:cacheprovider --import-mode=importlib \
  tests/test_phase02_synthetic_write_proposals.py
```

The PR's exact final HEAD must match the displayed local SHA before recording acceptance. GitHub CI validates unit tests and existing regression/Chromium/recovery workflows using disposable CI services. No Kali migrations, hosting plan, new key, paid provider or real customer records are required.

## Release decision

**No merge or production activation.** Leave PR #37 draft, preserve PRs #32–#36 draft, and retain independent review and private branch-protection as unresolved required controls. Phase 01 stays **3/9 — NO-GO**. No subscriptions, DigitalOcean, Render deployment, staging, Kali migration, AMBOY/OneCall live integration, or customer onboarding.
