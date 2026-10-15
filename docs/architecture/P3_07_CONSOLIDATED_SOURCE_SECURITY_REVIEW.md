# P3-07 — Consolidated Integration and Security Review Candidate

**Status: DRAFT / SOURCE TESTING, NEVER PRODUCTION AUTHORIZATION.**

This document reconciles two parallel, unmerged draft branches:
- [PR #50](https://github.com/AhmadibOfficial/MetaAutomate/pull/50) — canonical six-module integrated denial and synthetic report verification, GitHub CI #152: 833 Python tests passed; independent Kali for #50 not confirmed.
- [PR #51](https://github.com/AhmadibOfficial/MetaAutomate/pull/51) — additional eight-source contract drift and mutation coverage, CI #154: 850 Python tests; **owner exact-head Kali: 519 tests passed** at `61467163275df9a47d7356fd596d2956a81a633e`. The original P3-07b draft adds a competing cross-module runner and alternate `integration-demo` command.
- **This PR #52** (consolidation candidate; exact head SHA and CI recorded in the PR after validation) begins from PR #50 and **manually ports the distinct security audit from PR #51**, not a blind Git merge.

## Single canonical path, no competing integration engines

`apps/api/app/phase03_integrated_conformance.py` remains **the sole integrated denial flow**:
1. Verify the invented actor/tenant/request and P3-01 `DENY` receipt.
2. Bind the P3-02 denied plan and exact capability, effect, scope, resource, and request.
3. Validate the P3-03 invented no-dispatch and readback consistency; reconcile expiry and fake version.
4. Calculate P3-04 **fictional** business metrics separately from real revenue.
5. Ensure P3-05 local-only tool spec reports no transport or provider capability.
6. Run P3-06 rejected execution rehearsal and unauthenticated one-process audit chain.
7. Independently reconstruct a fresh *synthetic* report; reject altered `ALLOW`, ROI, provider receipt, permissions, token or release claims.

There is **no new `phase03_integration_safety.py` runtime, no duplicate `integration_safety.json` manifest and no second `integration-demo` command**. One supported CLI demonstration remains `integrated-demo` with the same flags used in PR #50. No SDK HTTP router or provider interface was enabled.

## Unique hardening ported from PR #51

`apps/api/app/phase03_contract_audit.py` is a **non-executing** source-manifest validator, separate from runtime integration. It reads exactly eight versioned local manifests: Phase 02 business domain, P3-01 capability catalog, P3-02 planning, P3-03 synthetic evidence, P3-04 analytics, P3-05 developer tools, P3-06 rejected execution, and the canonical P3-07 `integration_conformance.json` contract.

It refuses privilege/source drift: production/read/write/approval flags, `0` versus `false` type confusion, missing contracts, malformed JSON, domain capability duplicates, changed operation declarations, broken release state, artificial Phase 01 gate counts, unauthorized developer tools or unexpected provider authorities. Passing only means known local contract declarations are consistent, not that the system is secure in production. All source hashes, reviewers, audits and business numbers remain synthetic and unauthenticated.

Additional cross-module consistency asserts deny-plan expiry and resource-version agreement among negative evidence and the rejection engine, and forbids fabricated provider readback/financial success. The new `tests/test_phase03_contract_audit.py` is the independent audit regression; existing `tests/test_phase03_integrated_conformance.py` remains canonical.

## Local developer commands (exact final branch)

```bash
python scripts/phase03_offline_cli.py ecosystem-check
python scripts/phase03_offline_cli.py integrated-demo business.inventory.stock-preview.v1
python scripts/phase03_offline_cli.py integrated-demo business.finance.reconciliation-proposal.v1 --reviewer-count 2
python scripts/phase03_offline_cli.py integrated-demo business.inventory.stock-preview.v1 --observed-version 2 --observed-tick 112
```

All flows must report `decision=DENY`, `side_effects_performed=false`, `provider_called=false`, and `release_authorized=false`. The contract audit returns `source_compatible=true` but `external_services_inspected=false`. This is not independent human review, a business outcome, actual provider verification, or live tenant authorization.

## Code-review and integration checklist

Independent qualified reviewer must still:
1. Review P3-01–P3-06 parent branches, canonical P3-07 engine and the manually ported PR #51 audit on a **single immutable exact SHA**.
2. Compare the removed sibling PR #51 runner with the canonical PR #50 engine; verify no unique production-relevant negative check was lost. In particular, audit all upstream receipt/plan/tenant bindings, fake reviewer and replay denials, rehashed checksum acceptance, expiry/version mismatches, and synthetic financial evidence segregation.
3. Assess unkeyed hashes, volatile audit, adversarial mocks, developer contract security, Python dependencies and production-route isolation; formally disposition 10 threat classes in the original P3-07 reviewer packet, including BOLA, approval forgery, replay, integrity, privacy, DR and supply chain.
4. Verify source provenance and all required GitHub checks/branch protections on the **private** repository; existing connector cannot prove branch enforcement.
5. Require exact-head owner Kali acceptance separate from CI; neither the original #50 nor #51 green test authorizes this combined branch.
6. Reconcile parent PR dependency graph and merge conflicts only after independent review; no automated merging, deployment, database migration, customer interaction or subscriptions are authorized by this document.

## Operational gates remain explicitly unfulfilled

**Phase 01 Foundation 3/9 NO-GO; Phase 02 operational NO-GO tracked in [Issue #40](https://github.com/AhmadibOfficial/MetaAutomate/issues/40); Phase 03 live execution NO-GO.** True actor/service identity, revocation, provider/customer consent, independently signed multi-person approvals, durable replay defenses, signed provider receipts, separate authoritative readback, real rollback, private staging, actual branch protection and owner release authority are not established by source-level conformance. `main` and commercial pilot are not changed.

**Source consolidation is review preparation, not a security review or permission to merge.**
