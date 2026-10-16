# P3-03 — Independent Outcome Verification: source architecture, NO-GO

**Development continues subscription-free.** This milestone creates **verification architecture and local negative-control tests**, not real independent verification of customer activity. Parent PRs #44 (P3-01) and #45 (P3-02) remain draft, unmerged and subject to independent review.

## Trust boundary: the two meanings of verification

1. **Verified in source:** two invented evidence fixtures are internally consistent with an immutable, denied P3-02 plan; a fake resource version has not changed; duplicated event IDs are rejected. The code and tests establish source properties of a denial-only design.
2. **Not verified in operations:** whether an actual provider executed a request, whether a real customer object changed, whether a signature came from a legitimate provider, whether an actor was entitled to act, or whether verified revenue/business value arose. There are no authenticated external sources, real credentials, real customers or deployed workers.

A locally computed SHA-256 digest **cannot** establish provenance, even if the digest matches. Therefore, the verifier never emits `ALLOW`, a genuine execution result, a provider receipt, or a verified real-world outcome.

## Source deliverables

- `apps/api/app/phase03_outcome_verification.py`: standalone pure Python verifier that compares two separate **DEMO** sources against a precise P3-02 denial plan: `DemoNoDispatchEvent` and `DemoReadbackFixture`. Each is bound to synthetic tenant, operation, request, immutable planned target and plan checksum. Conflicting request/replay, forged fields, fake signed success claims, wrong tenant, unsupported event sources and invalid clock inputs fail closed.
- `contracts/intelligent/v1/outcome_verification.json`: machine-readable description of proof capabilities and what remains unverified.
- `scripts/phase03_offline_cli.py verify-denial <operation>`: a CLI that generates the two local fixtures and prints a denial report. `--simulated-observed-version 2` illustrates *simulated* change detection and cannot access an actual resource.
- `tests/test_phase03_outcome_verification.py`: tampering and recomputed fake digests; expiry, version changes, replay; two different DEMO tenants; bounded event memory; developer CLI no-real-operation checks.

## How to use the local developer CLI

```bash
python scripts/phase03_offline_cli.py verify-denial business.inventory.stock-preview.v1
python scripts/phase03_offline_cli.py verify-denial business.finance.reconciliation-proposal.v1
python scripts/phase03_offline_cli.py verify-denial business.inventory.stock-preview.v1 --simulated-observed-version 2
```

The report's `decision` remains `DENY` and every production verification authorization remains false. If both DEMO fixtures are structurally consistent and the invented version matches, it reports `DEMO_NO_DISPATCH_CONSISTENT_NOT_EXTERNAL_VERIFICATION`. If the fake version differs or the plan is expired, it reports `DEMO_NEGATIVE_CONTROL_UNVERIFIED`. If identity, plan/receipt fields or checksum integrity are invalid, it refuses the record. No notification, payment, database query, third-party API or hosting service is touched.

## P3-03 future real verification contract — not activated

For a real-world outcome, **a separate authorized provider evidence channel** must authenticate the issuer and bind a signed immutable provider operation identifier, exact actor, tenant, scope, target, request, timestamps, authorization version and effect to the approved plan. A *different authorized readback identity* must independently query real provider postconditions and compare immutable expected changes. The trust roots must be centrally administered, rotating, revocable and protected from the implementation actor. The system requires durable transaction deduplication, secure audit retention, monitoring, rollback readiness, customer permission and independent security review.

None of these conditions are met by P3-03 source simulations. No local event can be promoted to trusted evidence without fresh, separately reviewed authorization and reissued credible provider attestations. No claims of income generation, cost savings or real customer value may be derived from local fixtures.

## Change control and acceptance

PR #46 is temporarily targeted at `main` to activate existing GitHub PR CI triggers, while its history includes unmerged P3-01/P3-02 changes. Parent branches still require independent review, protected repo controls and separate integration acceptance. GitHub CI tests source only; owner Kali acceptance must be run at the exact final SHA and recorded separately.

**Phase 01 3/9 NO-GO; Phase 02 operational NO-GO; Phase 03 real execution and verification NO-GO.** We continue developing and improving responsibly, without purchasing a subscription or misrepresenting evidence.
