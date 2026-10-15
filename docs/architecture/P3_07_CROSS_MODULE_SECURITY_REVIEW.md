# P3-07 — Cross-Module Source Integration and Security Reviewer Packet

**Status:** DEVELOPMENT / SOURCE-ONLY DENY FLOW. This is a *draft independent-review preparation*, not an independent review or release acceptance. No paid subscription required.

## 1. Dependency provenance, separate evidence

| PR | Source milestone | Recorded evidence |
|---|---|---|
| #44 | P3-01 capability catalog / denial | CI #143: 440 Python passes; owner exact-head Kali P3-01 not separately recorded |
| #45 | P3-02 denied planning | CI #145: 501; owner Kali: 170 passed |
| #46 | P3-03 synthetic negative outcome | CI #146: 573; owner Kali: 242 passed |
| #47 | P3-04 synthetic analytics | CI #147: 640; owner Kali: 309 passed |
| #48 | P3-05 local developer tools | CI #150: 708; owner Kali: 377 passed |
| #49 | P3-06 execution denial rehearsal | CI #151: 768; owner Kali: 437 passed |
| #50 | P3-07 cross-module security | **Current draft — evidence pending until exact-head CI/Kali** |

PR #50's source history is stacked on #49 (which itself contains earlier unmerged drafts). The PR temporarily targets `main` to trigger existing GitHub CI. This **does not merge the parent PRs or independently approve their contents**. Reconcile the branch topology and reviewer findings before any merge.

## 2. Trust and architecture boundaries

P3-07 introduces `phase03_integration_safety.py` as **one synthetic, read-only, no-execution function** that connects P3-01 capability DENY → P3-02 DENY plan → P3-03 invented no-dispatch and readback DENY → P3-06 execution-rehearsal DENY / volatile audit-chain consistency. P3-04 invented business analytics may be included separately; P3-05 local Python tool contracts are checked but **no API, network, queue, customer account, provider or production SDK** is exposed.

`ecosystem-check` loads **eight local source manifests**: Phase 02 domain, P3-01 capabilities, P3-02 planning, P3-03 outcome, P3-04 analytics, P3-05 developer, P3-06 execution and P3-07 integration. It verifies required default DENY / NO-GO flags and compatibility. It **does not authenticate human review or check staging**. A green doctor is not a release approval.

### CLI examples (exact source branch only)

```bash
python scripts/phase03_offline_cli.py ecosystem-check
python scripts/phase03_offline_cli.py integration-demo business.inventory.stock-preview.v1
python scripts/phase03_offline_cli.py integration-demo business.finance.reconciliation-proposal.v1 --reviewer-count 2 --demo-analytics
python scripts/phase03_offline_cli.py integration-demo business.inventory.stock-preview.v1 --observed-version 2 --observed-tick 112
```

Every CLI response must remain `decision=DENY`, `provider_called=false`, `business_effect_performed=false`, `release_authorized=false`. A forged demo reviewer remains unverified. An expired plan or changed version is noted, not executed.

## 3. Security threat review — outstanding independent disposition

| Risk ID | Threat | Negative control available in source | Real mitigation not established |
|---|---|---|---|
| P3T-01 | Tenant confusion/BOLA | Distinct invented UUID markers and strict per-flow resource binds | Authoritative server-side tenant ownership; BOLA test in authorized environment |
| P3T-02 | Forged approver/privilege | DEMO reviewer labels cannot authorize finance; all decisions DENY | Independent verified approvers, revocation, per-effect signed approvals, separation of duties |
| P3T-03 | Replay/duplicate effects | Bounded in-memory duplicate conflict denial | ACID durable idempotency and distributed replay control |
| P3T-04 | Plan expiry/resource conflict | Logical expiry/version mismatch denies and records reasons | Real transactional conditional update and clock/revocation enforcement |
| P3T-05 | Fake provider receipt/audit | No external receipt accepted; local SHA-256 explicitly untrusted | Authenticated provider signature / independent readback; durable tamper-evident audit |
| P3T-06 | Data poisoning/profit misstatement | Synthetic validated inputs, demo units, no verified income claims | Authorized customer data provenance, reconciliation, accounting review and privacy |
| P3T-07 | Code/contract privilege drift | Exact tool and domain specs; eight-source gate checks | Real codeowner review, protected private `main`, trusted CI and release process |
| P3T-08 | Recovery/compensation | Explicit no-dispatch; manual recovery *notes* for future write effects | Authorized compensating procedures, provider state check, disaster recovery drills |
| P3T-09 | SSRF/service impersonation | No network stack or arbitrary target is exposed | TLS/service issuer lifecycle, provider endpoint allowlist, secret controls |
| P3T-10 | Supply-chain/CI tampering | PR SHA-bound source evidence and no merge | Independent reproducible build, dependency review and enforceable branch rules |

**Important limitation:** `tenant_id` is caller-supplied **invented fixture input**, not an authenticated subject. Synthetic hash checks cannot supply authenticity or independently observed real effects. All high-risk controls listed above remain unverified. In particular, **do not promote this module to an HTTP endpoint or production tool dispatcher** by toggling source flags.

## 4. Reviewer work order

A qualified reviewer **distinct from the implementer** should inspect PRs #44–#50, exact base/head SHAs, generated tests, package dependencies, negatives and parent merge conflicts; challenge each above threat with test evidence and a clear PASS/FAIL/REMEDIATION REQUIRED disposition. The reviewer must independently verify the repo's actual branch protections; previous access to policy details was not sufficient to demonstrate enforcement.

**Required signoff fields** (left intentionally blank):
- Reviewer GitHub identity / independence from authorship: **NOT VERIFIED**
- Reviewed immutable branch/head and source manifest revisions: **NOT VERIFIED**
- Review outcome and outstanding high-severity defects: **NOT VERIFIED**
- Enforced branch protection and required CI job names: **NOT VERIFIED**
- Owner cost/provider/customer authorizations, tenant governance: **NOT VERIFIED**
- Live staging, service identity, durable effects and recovery evidence: **NOT VERIFIED**
- Owner release GO for Phase 01 9/9 and Phase 02 / Phase 03 operations: **NOT AUTHORIZED**

## 5. Release boundary

**Phase 01 remains 3/9 verified (NO-GO). Phase 02 operational NO-GO (Issue #40). Phase 03 source engineering continues, but real authorized execution and commercial deployment remain NO-GO.**

No subscriptions, DigitalOcean/Render provisioning, migration 012–015, merge, repo-publication, real customer import, AI tool side effect, account write or payment is permitted by this source packet. Authoritative human consent/approvals cannot be provided by an AI-generated document.
