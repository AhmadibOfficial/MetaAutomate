# P3-02 — Capability authorization and planning, offline source milestone

**Source-only, not a live authorization system.** This branch is stacked on draft PR #44 (P3-01), **not** merged into `main`. Phase 01 remains **3/9 NO-GO**, Phase 02 operational acceptance remains NO-GO, and Phase 03 live capability execution remains blocked.

## What this milestone adds

- `apps/api/app/phase03_capability_planning.py`: strictly invented, deny-only capability plan generation. It requires a P3-01 *DENY* receipt, exact DEMO tenant/request/target binding, an expected resource version, matching bounded logical tick and explicit expiry.
- `contracts/intelligent/v1/planning.json`: developer-facing versioned planning contract for the four existing BIZ-002/006/011/012 capabilities, required authorization gates, risk-based second review requirement, and a permanent source `DENY` flag.
- `scripts/phase03_offline_cli.py plan`: a local design-only planner command that prints an untrusted DEMO plan; it cannot accept arbitrary resource names, live providers or real customers.
- `tests/test_phase03_capability_planning.py`: replay, quota, stale resource versions, forged/rehashed receipt, cross-tenant, type confusion and non-execution tests.

## Local CLI examples

```bash
python scripts/phase03_offline_cli.py catalog
python scripts/phase03_offline_cli.py plan business.inventory.stock-preview.v1
python scripts/phase03_offline_cli.py plan business.crm.sync-proposal.v1 --resource-version 3
python scripts/phase03_offline_cli.py plan business.finance.reconciliation-proposal.v1
```

All responses remain `decision=DENY`, `execution_authorized=false`, `provider_called=false`, `workflow_enqueued=false`. The `--resource-version` parameter is a **fictional input for negative version checks**, not a database version or permission.

## Planned but unverified trust chain

Real authorization is **NOT** performed. A future, separately reviewed executor would need: authenticated actor/service and valid revocation; authoritative resource ownership and tenant mapping; server-issued scoped credentials; bound provider target; cost and processing consent; required human review for the exact immutable effect (with stronger segregation for high-risk finance); durable transactional idempotency and replay defense; fresh version and expiry revalidation; provider-issued receipt and independent readback; approved private staging, monitoring and recovery; formal owner release GO. A plan produced by this demo can **never** be upgraded to a live grant.

## Threat boundary

The in-memory idempotency registry is bounded and lock-serialized for local testing; it is not durable across processes. A locally recalculated SHA-256 checksum can detect inconsistent demo fields but cannot authenticate human approvals or provider receipts. The review steps are explanatory strings, not executable instructions. The module deliberately has **no API router, DB connector, network request, AI invocation, tool-execution endpoint or deploy action**.

This is **trusted-authorization architecture work**, not completion of trusted authorization.

## Approval and staged PR relationship

PR #45 (this milestone) is based on the P3-01 branch from PR #44; therefore it must not be merged into `main` or treated as an independent deployable change. Parent PR #44 remains draft and is still pending exact-head owner Kali verification and independent human review. Phase 02 operational Issue #40 retains the release blockers.

Use the exact reviewed PR head SHA for local testing, after saving uncommitted work:

```bash
cd ~/MetaAutomate
git status --short
git -c http.version=HTTP/1.1 fetch --no-tags origin refs/pull/45/head
# Verify FETCH_HEAD matches the exact SHA printed on PR #45 before checkout.
git switch -c feat/p3-02-kali-acceptance <EXACT_SHA>
source ~/.venvs/metaautomate-p204a/bin/activate
python scripts/verify_phase03_local_gate.py --expect-sha <EXACT_SHA>
```

**NO-GO:** Phase 03 production execution and Phase 02 operational release remain blocked. No merge, subscriptions, migrations, staging, OneCall product federation, customer account operation, provider read/write or commercial pilot is authorized by this milestone.
