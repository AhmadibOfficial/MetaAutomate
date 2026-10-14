# P2-04a — Local synthetic delivery state-machine rehearsal

**Status: SOURCE ONLY. No worker, route, deployment, or real delivery. Phase 01 Foundation remains 3/9, NO-GO.**

## Scope and trust boundary

P2-04a models how future domain integration deliveries might safely track work, without executing any work. The Python module `apps/api/app/synthetic_delivery.py` is deliberately **not imported or routed by the API**, and it has no queue, DB connection, network, webhook, provider SDK, subprocess, filesystem writes, timer, or background worker. Its state exists only in one Python object in one process; restarting loses all jobs and receipts.

A UUID passed to this low-level pure simulation is **not authenticated tenancy**. It is only a test partition key. A later runtime adapter must derive tenant/product/actor from verified server-side identity, enforce authorization, and prove the cross-tenant boundary independently. Do not expose this class directly as a public API.

All inputs are invented scenario names, bounded `DEMO-` idempotency keys and events, and integer **logical ticks**, not real timestamps or business records. No free-form payload or callback is accepted. Work outcomes are explicitly **supplied simulations**, not evidence of external delivery.

## State chart

- `SIM_QUEUED` → `SIM_COMPLETED` on invented success.
- `SIM_QUEUED` → `SIM_RETRY_WAIT` on invented transient failure.
- `SIM_RETRY_WAIT` → `SIM_RETRY_WAIT` on second transient failure, with bounded 2-tick then 4-tick backoff.
- Third transient attempt → `SIM_DEAD_LETTER`, no further automatic attempts.
- Invented permanent failure → terminal `SIM_PERMANENT_FAILURE`; no recovery.
- One explicit **synthetic-only** manual recovery is allowed from dead letter, after 8 logical ticks. A fourth outcome attempt can complete or return to final dead letter. No second recovery. This is not a production approval.

Idempotency keys are indexed by `(tenant_uuid, key)`. Reuse with the same allowlisted scenario returns the prior snapshot; reuse with a different scenario fails. Each distinct event ID is processed once per job; a conflicting replay fails. The object uses an in-process lock for atomic transitions. Work units are bounded at 32 per demo tenant and 128 per object. No persistent or distributed idempotency is claimed.

Each immutable snapshot includes a SHA-256 chained **demo receipt** for each in-memory transition. This supports consistency checks but is **not signed, immutable storage, trusted time, audit compliance, tamper-proof evidence, or a provider acknowledgement**.

## Local test

From a correctly cloned checkout, with Python dependencies installed:

```bash
PYTHONPATH=apps/api python -m pytest -q tests/test_phase02_delivery_rehearsal.py
```

This test does not start a server, connect to PostgreSQL, touch Kali migrations, use a cloud service, or authorize the platform. Existing CI tests remain required before review.

## Deferred P2-04 work (not implemented here)

- Verified tenant/actor provenance, job storage with row-level tenancy, transactional idempotency, data minimization, retention and secure deletion.
- Actual provider adapters, timeout/circuit-breaker/retry budgets, backpressure and cross-worker leases.
- Signed inbound webhook verification, rotating provider keys, freshness, replay prevention, trusted origin and incident controls.
- Provider-issued receipts, independent reconciliation, compensating actions and operator authorization for real retries.
- Real metrics, redacted audit storage, disaster recovery, concurrency and abuse testing under approved private staging.

**Release gates remain unchanged:** no new paid subscription, Render/DO deployment, secrets, live provider, customer data, OneCall federation, Kali migrations, or customer activation. BIZ-011 remains DRAFT/DENY.
