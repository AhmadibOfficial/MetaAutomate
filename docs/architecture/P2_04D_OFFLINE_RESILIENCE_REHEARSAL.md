# P2-04d — Offline synthetic quotas and resilience rehearsal

**Status: source-only draft. Phase 01 Foundation stays 3/9 — NO-GO.** This change is independent of unmerged P2-04a/#32, P2-04b/#33 and P2-04c/#34. It branches from `main` and does not import or activate them. Their independent review and branch-protection gates are **postponed, not waived**.

## Purpose

Model hypothetical admission protection for independently isolated business integrations without accepting real customer requests, scheduling work, contacting providers or imposing actual network rate limits. The `OfflineSyntheticResilience` instance has only bounded Python dictionaries and an in-process lock. All tickets, outcomes and clock ticks are invented.

### Admission and backpressure rules

- `propose(tenant_uuid, DEMO-REQ-key, tick=int)` returns a frozen `Admission`: a simulated reservation or an explicit denial reason. It **never executes** business operations.
- At most **3 successful admissions per demo tenant per 10 logical ticks** (fixed window measured from the first admitted request of the window).
- At most **2 outstanding reservations per tenant** and **8 globally**, regardless of tenant quota. Completion of a ticket releases synthetic capacity. Rejected proposals do not consume a quota reservation.
- At most **16 tenant partitions**, **64 lifetime tickets** per instance. No eviction occurs, including completed tickets: once history is full, new IDs fail closed. Restart loses all simulated state; there is no durable deduplication or distributed counter.
- Idempotency is keyed by `(tenant UUID, synthetic request key)`; duplicates return the **same** ticket ID and current ticket status and do not consume a new quota slot, even after a terminal result. This is in-process demonstration only.
- Logical ticks (not wall-clock) must be integer 0–1,000,000 and nondecreasing for a given tenant.

### Circuit breaker rehearsal

- `SIM_CLOSED`: ordinary admitted DEMO tickets. Two consecutive simulated failures enter `SIM_OPEN` for **5 logical ticks**. A synthetic success resets the consecutive failure counter.
- `SIM_OPEN`: new synthetic proposals are denied until cooldown. After cooldown, one admitted proposal becomes `SIM_HALF_OPEN`'s **single probe**. Capacity, per-tenant quota and history limits still apply and can delay the probe.
- `SIM_HALF_OPEN`: all other new proposals are denied while the one probe is unresolved. A successful simulated probe closes the breaker; failure reopens for another 5 logical ticks.
- Responses to earlier outstanding tickets while a breaker is open or half-open do **not** impersonate the probe or close the breaker.
- All results are supplied explicitly to `simulate_result`; no time-triggered work, retries, scheduling, delivery, webhooks, background loops or provider calls occur.
- Every ticket can be completed once. The API caller-supplied UUID is **not authenticated** and is only a demo partition key.

### Security considerations

- Inputs are limited to strictly formatted `DEMO-REQ-` synthetic keys, UUID demo tenant partition and bounded logical ticks. No arbitrary body, URL, destination, tenant claim, credential, payment, SQL, or business record is accepted.
- A ticket ID is not a permission or bearer token. The mock policy cannot establish true tenant isolation, external authorization, real rate-limits, cross-process concurrency, callback correctness, or resilient queue processing.
- Frozen status snapshots explicitly mark `simulation_only`, `authenticated_tenancy=false`, `real_rate_limit_enforced=false`, `provider_operation_performed=false`, and `persisted=false`.
- Never call this module from an API route, application worker or provider adapter. `apps/api/app/main.py` does not import it. A static negative test checks common I/O/router imports; that is not a formal runtime sandbox.
- No new dependencies, cloud services, Render/DO deployment, database migrations, subscriptions, secrets, staging privileges, OneCall federation or customer records.

## Local Kali acceptance

From the existing private checkout and its venv (do not modify the protected `main` branch):

```bash
cd ~/MetaAutomate
git status --short
gh pr checkout 35
git rev-parse HEAD
source ~/.venvs/metaautomate-p204a/bin/activate
PYTHONPATH=apps/api python -m pytest -q \
  -p no:cacheprovider --import-mode=importlib \
  tests/test_phase02_synthetic_delivery_resilience.py
```

Confirm the checked-out commit equals the PR's final HEAD and focused pytest passes. CI runs the full existing suite with disposable PostgreSQL and browser tests in GitHub Actions. None of this constitutes real platform authorization.

## Explicit postponed gates

- Independent review of P2-04a/b/c/d, and GitHub-enforced protections for the **private** repository
- Proper real tenant/actor identity, rate-limit middleware, trusted wall clocks, durable backing store, queues and distributed circuit-breaker control
- Production access controls, monitoring, cost ceilings, real recovery and incident approvals
- All outstanding Foundation security, private staging, release and commercial pilot gates

**No merge and no deploy.** Keep the PR draft. Foundation remains **3/9 verified NO-GO**. No GitHub upgrade, public repository conversion, paid subscriptions, DigitalOcean, Render activation, Kali migrations or real customer/provider operations.
