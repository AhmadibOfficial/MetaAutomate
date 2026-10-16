# P2-03x — Restricted Intelligence Execution Rehearsal

**Classification: SOURCE-ONLY, DISPOSABLE TEST DATA. Not an autonomous agent service.**

Dependency order: P2-03u draft PR #83 → P2-03v draft PR #84 → P2-03w draft PR #85 → **P2-03x**. F04–F05 draft PR #86 is independent of this stacked Intelligence branch. Nothing has been merged or deployed by this development milestone.

## What was built

`apps/api/app/synthetic_bounded_intelligence_executor.py` adds a small deterministic worker **without network interfaces, provider SDKs, terminal execution, dynamic code evaluation, external publishing, or customer data**.

1. **Existing two-identity gate:** Each owner/reviewer request is verified against both independently signed **offline test IdP claims** and existing signed app session claims, tenant and role mapping. These claims are not real employee authentication.
2. **Two-person authorization:** A fictional project must already pass original-owner approval, independent-security-reviewer approval and the P2-03u three-step internal synthetic workflow rehearsal. The original security reviewer alone can approve a *specific proposed virtual command*.
3. **Module- and purpose-restricted tools:** The existing 12-module and five-engine governance matrix determines which of three in-process deterministic helpers are available. A command is bound to module, purpose, fictional project, input SHA-256, approved workflow digest and current module source evidence.
4. **No discretionary tool execution:** Exactly three virtual calculations are available:
   - `ANALYZE_SAMPLE`: count synthetic flagged records; compute a basis-point ratio.
   - `GENERATE_REVIEW_PLAN`: calculate a number of manual review batches for fictional cases.
   - `SUMMARIZE_EVIDENCE`: compare two fictional bounded integer counts without asserting causation.
   Inputs consist only of fixed-name bounded integers; arbitrary strings, personal details, code, network endpoints, model IDs, credentials, and unknown tools are denied.
5. **Lease, replay, revocation:** A fictional command ID may be reviewed only once per tenant, cannot be rewritten with different parameters, has a 120-second maximum synthetic lease, and is independently checked against current app-session revocation and test-IdP key or JTI revocation. The *original approved owner* is the only permitted simulated executor.
6. **Durable evidence:** The temporary SQLite DB writes exact synthetic command intent, approved actor session references, code/fixture evidence hashes, output, SHA-256, plus chained audit metadata in one serialized transaction. Retries return the exact same deterministic evidence and never run a new action.
7. **Recomputation and recovery:** Read-only authorized auditors re-run the deterministic calculation and check stored hashes and the local audit chain; the prior disposable snapshot procedure can be restored and retested. A trusted independent audit-head checkpoint can detect some rollback, but none is automatically anchored off host. Host administrators can rewrite the local store, so **do not claim tamper-proof audit evidence**.

## Threat and failure cases under test

- Unauthenticated/no-claim/wrong-role/cross-tenant request.
- Owner attempting to bypass separate security reviewer.
- Draft or un-simulated project attempting virtual work.
- Tool not permitted for a module or for the declared purpose.
- Unknown fields, PII-like data, negative/fractional/boolean/oversized integers, possible divide-by-zero.
- Expired synthetic command lease, signed actor or reviewer revocation.
- Signed test identity signing-key rotation and key revocation.
- Replayed command IDs, changed input or approved workflow digest.
- Injection/corruption of audit or saved result hashes.
- SQLite failure inside audit write and transactional rollback.
- Recovery of fictional tool receipts with offline backup and independent recomputation.

## What remains missing before any real Intelligence operation

Real OIDC/MFA with independently verified staff and organization membership, correct authorization-code PKCE login lifecycle, a provisioned private staging environment, protected PostgreSQL production task states with RLS and encryption, centralized revocation, worker isolation and network egress policy, secrets management, separately approved customer consent and data classification, accurate model evaluations with authorized samples and cost limits, independent remote audit anchors, recovery/rollback metrics, external provider integration scopes, monitoring/kill-switch and independent operational acceptance.

This **does not satisfy F04–F09**. GitHub main is not protected; the owner's private repo must remain private, and source CI cannot activate live staging. Phase 01 remains **3/9 verified**, Phase 02/03 operational **NO-GO**. No hosting, subscriptions, model API calls, production migrations, customer activation or website deployment may be inferred from this draft.

## Test

```sh
python -m pytest -q tests/test_synthetic_bounded_intelligence_executor.py
python -m pytest -q tests/test_synthetic_oidc_governed_gateway.py tests/test_synthetic_governed_orchestration.py
python -m pytest -q tests/test_synthetic_model_governed_portfolio.py tests/test_synthetic_intelligence_project_architect.py
```

CI: `.github/workflows/p2-03x-bounded-intelligence.yml`. No provider credentials or resource provisioning are used.
