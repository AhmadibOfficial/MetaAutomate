# P2-04c — Offline synthetic delivery observability and incident analysis

**Status:** source-only draft, not deployable. Phase 01 Foundation **3/9, NO-GO**; private repository stays private. PR #32 P2-04a and PR #33 P2-04b remain draft/unmerged. This milestone is branched directly from the merged `main` and does **not** import or activate either pending workstream.

## Goal

Practice deriving safe, understandable incident summaries from **invented delivery events only**. P2-04c does not receive webhooks or actually process delivery. A caller supplies an ordered list of `SyntheticObservation` values; `analyze_synthetic_incidents` returns an immutable `SyntheticIncidentReport` with counts, deterministic per-job summaries and **non-executable** incident-review guidance.

### Signals

- `SIM_QUEUED`: synthetic job observed queued (attempt 0)
- `SIM_RETRY_WAIT`: simulated transient failure with exactly one attempt increment (only attempts 1–2), logical backoff 2 then 4 ticks
- `SIM_COMPLETED`: invented successful result
- `SIM_PERMANENT_FAILURE`: invented terminal failure
- `SIM_DEAD_LETTER`: invented exhaustion at automatic attempt 3 or, after one recovery rehearsal, total attempt 4
- `SIM_RECOVERY_REHEARSAL`: one hypothetical operator review after dead-letter attempt 3, delay 8 logical ticks; does **not** authorize or execute anything

The model rejects events that skip attempts, arrive before a due tick, go backwards in time, continue after a terminal state, claim another recovery, or mix tenant partitions. It does not replay or repair a malformed timeline.

### Bounded by design

- At most 128 invented observations in one call, at most 32 demo jobs per tenant, at most 8 observations per job.
- `DEMO-JOB-` and `DEMO-EVT-` identifiers only, valid UUID tenant partition supplied as an argument.
- Integer logical ticks between 0 and 1,000,000; no real timestamps or wall-clock reliance.
- A synthetic queued/retry/recovery event is marked stalled if its due tick is **10 or more logical ticks** in the past.
- Reports expose only demo labels, synthetic state counts and an advisory `REVIEW_SYNTHETIC_INCIDENTS_ONLY` marker. They do **not** issue actual incident tickets, compensate actions or manage approval.

### Security boundaries

Tenant UUID **is not authentication**. Any future real runtime must supply verified tenant identity from a secure server-side context and prove isolation. A demo observation is not an authoritative provider acknowledgement; no external action or real business record is validated. The immutable report is not tamper-proof evidence or a durable audit trail.

No network, provider SDK, database read/write, Redis, disk I/O, API router, secrets, cloud resource, worker or real-time scheduler is implemented. No new migration; no environment, payment or deployment configuration modified. The module remains **unimported and unrouted** by the API. Testing synthetic events is not a release approval.

## Local verification on Kali

Use the existing private repository clone and virtual environment. The branch is independent of PR #32 and PR #33.

```bash
cd ~/MetaAutomate
git status --short
gh pr checkout 34
git rev-parse HEAD
source ~/.venvs/metaautomate-p204a/bin/activate
PYTHONPATH=apps/api python -m pytest -q \
  -p no:cacheprovider --import-mode=importlib \
  tests/test_phase02_synthetic_incident_observability.py
```

Only mark Kali verified after matching the **final PR head SHA** and observing a passing local result. GitHub CI runs all existing suites on disposable infrastructure. No external provider account is used.

## Deferred (not waived)

- Merging P2-04a/b/c pending PRs and integration tests, subject to independent code review and branch protection
- Trustworthy identity, signed real callbacks, durable storage and legitimate provider receipts
- Actual incident on-call/approval workflow, key rotation, webhook delivery and recovery
- Production rate controls, persistence, dashboards, SIEM export and incident tickets
- All six outstanding Phase 01 gates, including enforceable branch protection

**Merge NO-GO:** Keep this draft unmerged; foundation remains **3/9 NO-GO**. No paid GitHub upgrade, public repository, subscriptions, Render/DO activation, migrations, OneCall federation, actual customer records or cloud infrastructure.
