# P3-06 — Controlled Execution Architecture: DENY-Only Source Rehearsal

**Status: SOURCE DESIGN IMPLEMENTED, REAL AUTHORIZED EXECUTION NOT AVAILABLE.** This phase continues subscription-free engineering without waiving release controls. Phase 01 foundation remains **3/9 NO-GO**, Phase 02 operational **NO-GO**, Phase 03 live actions **BLOCKED**. The private PR remains draft and unmerged.

## Architecture: a rejected request is still useful evidence

A future intelligent ecosystem must decide which exact capability may act, for whom, on which resource, under which risk controls, and what will count as independently verified completion. P3-06 implements a **non-executable rehearsal** of that decision:

1. Begin with an earlier P3-01 DENY receipt and P3-02 fixed DEMO plan bound to tenant/operation/request/resource/checksum.
2. Accept only invented `DEMO-ATTEMPT-*`, bounded logical ticks, a typed expected resource version, and zero, one or two `DEMO-REVIEWER-*` labels. A label **cannot** establish real identity or approval.
3. Revalidate the entire negative plan against its original request; reject forged `ALLOW`, input type confusion, changed authority flags, cross-tenant binding, unsupported effects, non-DEMO resource targets, duplicate fake reviewer identities and conflicting attempt replays.
4. Compare a P3-03 synthetic no-dispatch event and invented readback state. If the DEMO resource version changed or the invented plan expired, append explicit denial reasons. **Still DENY even when the version matches and two fake reviewers are present.**
5. Produce immutable `ExecutionRejection` with state `REJECTED_NO_DISPATCH`, explicit missing external trust codes, and effect-dependent recovery notes. `side_effects_performed=false` is guaranteed in the source model.
6. Optionally record the result in an instance-local, per-tenant bounded SHA-256 hash chain. This records only invented denials. A separate local recomputation checks internal hash and sequence consistency. It is **not authenticated, not durable and can be recomputed by an attacker**. No security approval can rely on it.

## Real risk and rollback model — future design only

| Effect | Source rehearsal | Required real production safety work |
|---|---|---|
| `validate_only` (BIZ-002) | No dispatch; no compensation required | Trusted actor, tenant, input ownership, controlled rate and logs |
| `read_external` (BIZ-011) | No provider read; no side effect | Provider-bound server scope, permitted tenant read, consent, privacy and independent security review |
| `propose_write` (BIZ-006) | Reject effect; explanatory manual triage note | Authenticated customer and reviewer, exact immutable approval, idempotent provider effect, rollback and independent readback |
| High-risk `propose_write` (BIZ-012) | Explicit second human reviewer *missing* even with DEMO labels | Real segregated approver identities, transaction threshold policy, per-effect dual signoff, verified provider receipt, audited compensating transaction procedures |

**Never automatically undo financial transactions or assume a rollback was performed.** A future real rollback requires the operator to verify actual external state and provider semantics, authorized compensating action and an independently verified receipt. Stating a recovery plan is not performing recovery.

## Deliverables and reproducibility

- `apps/api/app/phase03_execution_rehearsal.py`: strict reject-only simulation; per-tenant bounded replay index, transparent missing trust and recovery explanations, local demo audit with separately recomputable internal links.
- `contracts/intelligent/v1/execution_rehearsal.json`: machine-readable NO-GO scope and 11 later *real-world* prerequisites, all external truth flags explicitly false.
- `scripts/phase03_offline_cli.py execution-rehearsal`: command for invented local scenarios; no `--execute`, `--provider`, `--credentials`, `--merge`, `--approve`, `--rollback` or customer records.
- `tests/test_phase03_execution_rehearsal.py`: four capability types; fake dual-approval attempts; forged plan and cross-tenant inputs; stale resources and expired plans; bounded memory and replay; hash-chain sequence and tampering; CLI safety and absence of API wiring.

Sample invocation in an exact-head approved local P3 branch:

```bash
python scripts/phase03_offline_cli.py execution-rehearsal business.inventory.stock-preview.v1
python scripts/phase03_offline_cli.py execution-rehearsal business.finance.reconciliation-proposal.v1 --reviewer-count 2
python scripts/phase03_offline_cli.py execution-rehearsal business.inventory.stock-preview.v1 --observed-version 2 --observed-tick 112
```

Every command returns a **DENY** rejection and a single local unauthenticated audit entry; none calls a provider or performs a business effect. The second command proves that two **invented labels** do not represent verified human approvers. The third reveals a version change and expired DEMO plan but never executes anything.

## P3-06 operational acceptance — not complete

Future trusted authorization will require **independent human review and private branch enforcement, Phase 01 9/9, Phase 02 operational GO**, actual service/actor identity with revocation, authoritative tenant ownership, provider scope and customer consent, real effect-specific multi-person approvals (where applicable), durable ACID idempotency and authenticated replay protection, provider-origin receipts, independent external readback, disaster-recovery and rollback drills, and an explicit signed owner release GO. **No programmatic editing of source flags or invented checksums can authorize live execution.**

This branch begins from P3-05 PR #48 exact accepted source head. It targets `main` for existing CI workflow triggers only; the combined diff includes unmerged PRs #44–#48 and will require independent dependency review before any merge. No subscriptions, secrets, migrations, staging, live tenant operations, customer onboarding or cloud activity are activated.

**Source completion does not satisfy the P3-06 real authorized execution milestone.** It provides tested security design for future work while protecting business trust.
