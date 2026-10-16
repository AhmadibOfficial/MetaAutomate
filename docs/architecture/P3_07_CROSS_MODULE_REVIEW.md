# P3-07 — Cross-Module Security Integration and Independent Review Preparation

**State: source design and testing only.** Parent Phase 03 PRs #44–#49 are draft/unmerged, and the new P3-07 branch builds on exact P3-06 SHA `65c12cbd8476d6fd527a9179dd67719648cccc40`. No subscriptions or staging are required to test these local modules.

## Purpose: check the *same* transaction across module boundaries

All Phase 03 components can independently pass unit tests yet disagree on tenant, request, resource, scope, review, audit or business value. The added pure-Python `phase03_integrated_conformance.py` independently reconstructs the same invented request across six source modules:

| Source | Joined test | Deliberate limitation |
|---|---|---|
| P3-01 capability admission | Verify denial receipt, operation and scope | Actor and service credentials are invented |
| P3-02 capability planning | Verify plan checksum, target, tenant and expiry | No executable authorization |
| P3-03 negative verification | Verify local *invented* non-dispatch and readback snapshot | No real provider receipt |
| P3-04 business analytics | Attach fictional source-scoped, tenant-local sales/cost metrics | No real revenue, income or ROI |
| P3-05 developer SDK contract | Validate the local allowed operation set and disabled transport | No public API or externally trusted SDK |
| P3-06 controlled-execution rehearsal | Require rejection, check volatile hash-chain continuity and denial causes | No provider call, side effect or durable audit |

The `OfflineIntegratedReport` is immutable. It includes exact IDs, digests, denial causes, synthetic KPI values and **explicit false production authority flags**. `inspect_integrated_demo` independently reconstructs the expected denial report; an altered report does not verify. Because anyone can reconstruct local SHA-256 hashes, this comparison proves **internal consistency only**, not real-world nonrepudiation, signature trust or approval.

The code has **no transport, queue, real tenant identity, database writes, customer data, payment, external finance or AI agent action**. It never returns `ALLOW`.

## Local command-line exercises

In an exact-head checked-out local feature branch:

```bash
python scripts/phase03_offline_cli.py integrated-demo business.inventory.stock-preview.v1
python scripts/phase03_offline_cli.py integrated-demo business.finance.reconciliation-proposal.v1 --reviewer-count 2
python scripts/phase03_offline_cli.py integrated-demo business.inventory.stock-preview.v1 --observed-version 2 --observed-tick 112
python scripts/verify_phase03_local_gate.py --expect-sha EXACT_PR_HEAD_SHA
```

The second command tests that two **DEMO reviewer labels** do not authorize finance; the third detects stale plans and changes in fake resource versions. The synthetic business metric is `DEMO-UNIT`, not a verified accounting outcome. Every report must show `decision=DENY`, `execution_authorized=false`, `provider_called=false`, `real_revenue_measured=false` and `release_authorized=false`.

## Security review handoff — independent human review still required

Suggested checklist for an outside human reviewer, to be signed **outside the source tree**, with SHA-bound evidence:

1. Review PR #44 through PR #49 (including their unmerged ancestors) and P3-07 together; pin exact head SHA and compare Git tree against tests. Resolve dependency/merge strategy rather than merging drafts out of order.
2. Review the trust boundaries of actor identity, tenant ownership, revoked service credentials, genuine customer and provider scopes, and any actual approval principals. The source supplies **none** of these external controls.
3. Probe type-confusion (`0` vs `false`), self-reported authority, forged/rehashed checksums, cross-tenant receipts, conflicting request IDs, stale resource versions, missing/duplicate reviewer identities and fake high-risk finance signoff.
4. Verify the local-source tests and whether they detect corrupted intermediate module outputs, real provider claims masquerading as synthetic data, and contradictory finance/ROI interpretations.
5. Assess that no Phase 03 module has an executable route, background worker, DB writer, tool invocation, provider connector or secret, even if another file imports the pure functions.
6. Inspect reproducible exact-head GitHub CI and independent Kali results. **GitHub CI is not an independent human approval**.
7. Document any findings with severity, fix/exception owner, SHA, repro and independent retest. Track external branch protections and all outstanding Phase 01/02 operational requirements in Issue #40.
8. Sign an independent human review or record **REJECT**. Do not mark GO by changing a JSON flag, README or automation report.

## Source-based release limits and open work

- All PRs remain draft/unmerged; private branch protection and independent human security review are not verified.
- **Phase 01 Foundation: 3/9 NO-GO; Phase 02 operational: NO-GO; Phase 03 real execution: BLOCKED.**
- Real release would require authenticated actor and OneCall/MetaAutomate service identity, authoritative tenant authorization, provider/customer agreements, isolated approved staging and cost controls, migrations/recovery, durable transactional replay prevention, independent readback, genuine audit/incident response, real pilot/customer acceptance and explicit formal GO.
- The P3-07 draft may be targeted at `main` **only to run existing CI**, without merging or waiving any review dependencies. The combined diff includes its draft ancestors.

**Milestone acceptance means Phase 03 source-conformance tests passed at an exact SHA, not that a real-world platform was evaluated or authorized.**
