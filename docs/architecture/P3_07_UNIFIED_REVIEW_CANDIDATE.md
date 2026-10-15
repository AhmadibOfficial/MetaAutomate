# Phase 03 P3-07 — Unified Cross-Module Security Review Candidate

**Status: draft source-only, DENY-only; NOT merged or released.** This branch **reconciles two sibling PRs** #50 and #51 that independently branched from #49. Its base is **PR #51 head `61467163275df9a47d7356fd596d2956a81a633e`**, with PR #50's typed detailed review report and adversarial tests imported and adapted. Both parents remain DRAFT/UNMERGED. The final unified SHA, not either parent SHA, is the only evidence for the combined revision.

## Architectural reconciliation

| Element | Earlier PR #50 | Earlier PR #51 | Final combined approach |
|---|---|---|---|
| End-to-end capability denial | Separate `phase03_integrated_conformance.py` | `phase03_integration_safety.py` | **One shared implementation:** `run_offline_integration` in `phase03_integration_safety.py` |
| Detailed trace/reconstruction | Rich report and `inspect_integrated_demo` | Compact DENY report | Thin compatibility/reporting facade over shared engine; no duplicate admission/planning/evidence/execution code |
| CLI | `integrated-demo` | `integration-demo`, `ecosystem-check` | Both kept for test/developer compatibility; both dispatch to the same denial engine |
| Source contracts | `integration_conformance.json` | Eight-contract `integration_safety.json` and audit | Retain explicit report-spec contract; keep the **eight-source** security audit as authoritative local source preflight |
| Tests | Forged/rehashed rich reports, monkeypatched cross-module success claims, tenant isolation | Eight-contract drift and contract flag/type confusion, all four operations | Run both tests and dedicated no-dual-engine regression on a **single SHA** |
| Security notes | `P3_07_CROSS_MODULE_REVIEW.md` | `P3_07_CROSS_MODULE_SECURITY_REVIEW.md` | This reviewer packet captures the reconciliation; both original PRs stay historical draft evidence |

The facade in `phase03_integrated_conformance.py` **must not** import capability, planning, outcome, business or execution modules. Instead it converts typed inputs for `run_offline_integration` and formats that single engine's negative result. Direct layer checks now include DENY receipt consistency, tenant/operation/scope/request parity, immutable source plan and replay denial, negative readback flags and simulated audit-chain consistency. The compatibility report is not a signed attestation or external provider receipt.

## Current and future acceptance

1. **Source CI** must pass Python, PostgreSQL disposable backup/restore/upgrade, browser and release-evidence gates on the exact final unified PR head. Parent passing results (PR #50: 833 Python, PR #51: 850 Python) cannot be used as integration acceptance.
2. **Owner Kali** must fetch the exact final unified PR commit into a clean named `feat/p3-` checkout and run `scripts/verify_phase03_local_gate.py --expect-sha <final_SHA>`. Owner's separate 519 P3-07b passes at PR #51 head are useful history but do not accept the combined revision.
3. **Independent qualified human review** must inspect the final diff/HEAD, source threat models, denial invariants, test gaps, parents' conflicts, public APIs, dependencies, and private branch protections, issue independent actionable findings and approve only if appropriate. No self-approval, silently merging, public repository change or skipped policies.
4. **Live execution** remains blocked until real service identity and revocation, tenant/resource ownership, actual provider/user permission, customer consent, durable idempotency and external receipts/readback, staging recovery evidence, Phase 01 9/9, Phase 02 operational GO, and formal owner release authorization. None is supplied by local DEMO classes or green CI.

## Developer tools (all offline)

```bash
python scripts/phase03_offline_cli.py ecosystem-check
python scripts/phase03_offline_cli.py integration-demo business.inventory.stock-preview.v1
python scripts/phase03_offline_cli.py integrated-demo business.inventory.stock-preview.v1
python scripts/phase03_offline_cli.py integrated-demo business.finance.reconciliation-proposal.v1 --reviewer-count 2
python scripts/phase03_offline_cli.py integration-demo business.inventory.stock-preview.v1 --observed-version 2 --observed-tick 112
```

Expected: `DENY` everywhere, no provider effect, no authenticated real-world evidence. `ecosystem-check` checks **8 local source contracts and 4 invented DENY operations**, not staging. An `integrated-demo` trace includes synthetic hashes for developer debugging, never authorization.

## Independent-review handoff (all explicitly NOT verified)

- Human reviewer name / separation from author: **NOT VERIFIED**
- Independent security review decision: **NOT APPROVED**
- Private GitHub branch protection and required checks: **UNVERIFIED**
- Approved private staging/cost ceiling: **NO**
- Real actor/provider federation and delegated scope: **NOT DEPLOYED**
- Real customer privacy consent and data rights: **NOT APPROVED**
- Provider receipt and independent readback: **NOT PERFORMED**
- Phase 01 Foundation: **3/9 NO-GO**
- Phase 02 operations: **NO-GO** (Issue #40)
- Phase 03 real execution: **NO-GO**
- Production/Phase 03 release decision: **BLOCKED**

**No subscriptions, new hosting, migrations, external identity changes, customer data, financial writes, merge, publicization or deployment are authorized.** Source development may continue independently of cloud spending.
