# P2-05b — Offline preflight and one-command Phase 02 validation

**Development status:** source-only draft. **Foundation: 3/9 — NO-GO.** The repository remains private; PRs #32–#37 are unmerged with independent reviews and enforced branch protection deferred, **NOT WAIVED**.

## Security goal

Before MetaAutomate or AMBOY could execute a business-changing CRM or finance operation, real production must validate the actor, tenant, exact proposal and version, risk, scoped authority, human approval, expiry, idempotency, provider readiness and verifiable backend receipt. P2-05b is **a DEMO-only denial evaluator**, not an implementation of these real checks.

This branch comes directly from merged `main`, without importing the unmerged P2-05a model (#37). It copies only the exact official BIZ-006 and BIZ-012 *declarations*, with an independent test checking them against `contracts/domains/v1/operations.json`.

### Synthetic policy engine

`apps/api/app/synthetic_approval_preflight.py` checks a bounded invented `SyntheticPreflightRequest`:

- two allowlisted write-proposal operation IDs and strictly `DEMO-` scenarios (no actual customer, ledger or provider payload);
- UUID tenant/proposal test labels, strict demo actor/reviewer labels and `DEMO-PREFLIGHT-` request ID;
- simulated CRM reviewer count 1; high-risk finance reviewer count 2, both distinct and distinct from proposer;
- claimed proposal version exactly matching invented reviewer count, a nondecreasing logical tick, and an invented 20-tick expiry window;
- four caller-supplied **synthetic boolean claims**: identity-match, scope-match, version-match and provider-readiness; they are **not evidence**;
- in-memory replay registry of 16 request IDs per tenant, 64 total, 16 tenant partitions, no eviction, atomic idempotent replay under RLock. Conflicting identical IDs are rejected.

**Critical control:** Every output is an immutable snapshot with `decision="DENY"`, `execution_authorized=false`, `executed=false`, `server_identity_verified=false`, `real_scope_issued=false`, `human_approval_verified=false`, `provider_receipt_verified=false`, `persisted=false`. The `demo_checks_complete` attribute means only that the untrusted invented test labels and booleans are internally consistent. It **never clears** the nine permanent denial gates.

This model has no FastAPI router, webhook, provider client, database, real signer, cloud or worker, customer content, migration, AI inference, OneCall connection, payout or real approval.

## Automating the engineering cycle

We avoid repeating many manual commands for each Phase 02 branch. GitHub automatically runs the existing three-job CI workflow when a draft PR is opened. The local Kali one-command helper `scripts/verify_phase02_local_gate.py` performs:

1. Inspect branch name, exact Git commit SHA and working-tree cleanliness; refuse dirty checkouts or non-Phase-02 branches.
2. Detect all existing `tests/test_phase02_*.py` suites in the **currently checked-out branch**.
3. Run them with the active Python interpreter, `PYTHONPATH=apps/api`, no pytest cache, without Docker/SQL migrations, and produce simple PASS/FAIL, Python version and SHA evidence.
4. Print the **non-negotiable NO-GO** result. It never merges, pushes, deploys, provisions, modifies production, fetches credentials, or posts approvals.

The helper does not install dependencies and expects the existing Kali Python virtual environment and test requirements. It runs **only** tests that exist in the current checkout, not tests from six other unmerged PRs. The prior P2-04e local four-branch overlap rehearsal is a separate, pinned-source smoke test and does not turn unmerged code into `main`.

### Kali acceptance

After inspecting `git status --short` and preserving changes if any, check out the draft PR:

```bash
cd ~/MetaAutomate
gh pr checkout 38
source ~/.venvs/metaautomate-p204a/bin/activate
python scripts/verify_phase02_local_gate.py --expect-sha <PR-38-FINAL-HEAD-SHA>
```

The report will print the exact SHA, Python version, branch, suite count, pytest summary and final `PHASE02_RESULT`. Paste a credential-redacted summary for the acceptance record. An unexpected SHA or dirty working tree will fail closed. Do not claim Kali acceptance without the real output.

### Boundaries and next steps

Source-only engineering may proceed in draft feature branches; CI and local synthetic tests may be automated. **Automatic merging, marking ready, modifying `main`, production deployment, issuing real tokens, authenticated approvals, migrations, provider calls, subscriptions, customer access, and real business writes stay disabled.**

Independent human code review, enforceable private GitHub protection, authenticated runtime tests, live staging isolation, trusted time and evidence-based receipt validation must separately pass their release gates. Phase 01 remains **3/9 verified — NO-GO**. Tests on this demo module are never authorization to execute.
