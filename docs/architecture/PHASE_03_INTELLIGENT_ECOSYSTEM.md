# Phase 03 — Intelligent Ecosystem

**Development state:** Phase 03 **source development opened**, not live activation.  
**Release state:** Phase 01 **3/9 NO-GO**; Phase 02 **operational NO-GO**; Phase 03 **execution unavailable**.

## Vision

MetaAutomate's Intelligent Ecosystem will expose **authorized** capabilities through well-defined developer contracts, enforce security/tenancy/approval before any real action, independently verify outcomes, and report measured business value. AI or an agent may recommend or describe a capability, but model output never provides identity, scope, permission, payment authority or approval.

**Design principle:** build the sources, test the boundaries, preserve release autonomy for authorized humans. Skipping the Phase 02 *development queue* is not waiving its operational security gates.

## Phase 03 engineering milestones

| Milestone | Capability | Initial implementation |
|---|---|---|
| P3-01 | Versioned capability catalog and developer interface | **This PR:** source-only manifest, strict Phase 02 contract parity, local CLI catalog |
| P3-02 | Policy and authorization gateway | **This PR:** offline DEMO inspection, permanent DENY, isolated idempotency; trusted policy issuance is blocked |
| P3-03 | Independent outcome and audit verification | **This PR:** invented checksum consistency check only; real provider/owner attestations blocked |
| P3-04 | Analytics and measurable outcomes | **This PR:** counts of DEMO denials only; customer KPI, ROI and revenue not measured |
| P3-05 | Developer tools, audited APIs and SDKs | **This PR:** local catalog/preview/analytics CLI; no remote API, tokens, plugins or external tool calling |
| P3-06 | Controlled capability execution | **Future, gated:** per-tenant authenticated scopes, actual human approvals, idempotent effect, independent provider receipt, safe rollback and incident response |

## Implemented in P3-01

- `contracts/intelligent/v1/capabilities.json` is a draft, deny-only versioned machine contract for existing BIZ-002, BIZ-006, BIZ-011 and BIZ-012 operations, tied to the Phase 02 source operation manifest. It explicitly rejects a missing/extra capability, wrong required scope, fake grant or provider-execution flag.
- `apps/api/app/phase03_intelligent_ecosystem.py` is a **standalone unrouted** Python demo-only gateway. Invented actor/tenant/request/scenario inputs are schema-checked; all outputs deny. A bounded lock-serialized request registry demonstrates idempotent replay and tenant separation but is not durable or distributed.
- A local SHA-256 receipt checksum detects accidental DEMO tampering, but is **not signed, durable, provider issued or authoritative**. Validation additionally compares expected exact source denial fields. An attacker who controls all in-memory values could regenerate checksums. Receipt verification *never* sets real-execution evidence flags.
- Analytics counts only synthetic denials. No customer data, financial metrics, business revenue, provider events or verified return on investment is calculated. Empty streams are `NOT_MEASURED`, not fictitious success.
- `scripts/phase03_offline_cli.py` allows **local-only** discovery, deny previews and DEMO denial analytics; it does not access GitHub/cloud/provider APIs or load customer records.

### Developer quickstart

From the private MetaAutomate repository and approved developer venv:

```bash
python scripts/phase03_offline_cli.py catalog
python scripts/phase03_offline_cli.py preview business.inventory.stock-preview.v1
python scripts/phase03_offline_cli.py preview business.finance.reconciliation-proposal.v1
python scripts/phase03_offline_cli.py demo-analytics
```

Each command is strictly local and will report `decision=DENY`. The demo tenant UUID is a fixed invented constant; it is not an identity grant.

### Kali source verification

After independently verifying an exact final PR SHA and saving all local work:

```bash
git status --short
git -c http.version=HTTP/1.1 fetch --no-tags origin refs/pull/PR_NUMBER/head
test "$(git rev-parse FETCH_HEAD)" = "EXPECTED_FINAL_SHA"
git switch -c feat/p3-01-kali-check EXPECTED_FINAL_SHA
source ~/.venvs/metaautomate-p204a/bin/activate
python scripts/verify_phase03_local_gate.py --expect-sha EXPECTED_FINAL_SHA
```

The verification helper requires a clean named `feat/p3-` branch at exactly the supplied SHA. It runs all checked-out `tests/test_phase03_*.py` tests, never calls the network or creates any service and reports `PHASE03_SOURCE_RESULT=PASS/FAIL`. Green results accept only the offline source milestone.

## Mandatory live authorization design (NOT implemented/approved)

A later executor must verify *all* of the following, bound to the same trusted transaction before any external business effect:

1. Server-established identity, user session, product membership and true tenant/resource ownership; dedicated trusted OneCall/MetaAutomate service identities, active revocation.
2. Precisely versioned capability and effect contract with deny-by-default permissions, trustworthy product-scoped and tenant-scoped credential, provider/target allowlist and secure network identity.
3. Verified authorized human approval for the exact effect and immutable request version, with separate reviewers for higher-risk finance operations and enforceable separation of duties.
4. Durable atomic idempotency and replay resistance, rate limits, deadlines, lock-safe retries, review of financial consequences, safe failure and incident alerting.
5. Provider-issued signed/independently authenticated execution receipt and independently authorized readback of actual postconditions; no local simulation or generative text may substitute for evidence.
6. Real privacy authorization, billing/spend ceiling, isolated staging, independently tested disaster recovery, audit retention, security review and explicit owner release decision.

**There is no capability executor, HTTP route, external API, worker, provider token, customer data access, write operation, or model tool invocation in P3-01.**

## Release dependency and acceptance

The Phase 02 operational issue [#40](https://github.com/AhmadibOfficial/MetaAutomate/issues/40) remains open, with source draft PRs #32–#43 unmerged and independent review/branch enforcement still outstanding. Passing Phase 03 source tests never closes a Phase 01 or Phase 02 operational gate. No merge, deployment, new hosting plan, migrations, OneCall federation, pilot activation, autonomous write or customer transaction is authorized by this document.

**Phase 03 source work: IN DEVELOPMENT. Phase 03 real execution: NO-GO.**
