# Phase 02 operational exit — source preparation and external acceptance plan

**2026-10-14 • STATUS: NO-GO • Phase 01: 3/9 verified • Phase 03 live execution: BLOCKED.**

This is a concrete acceptance plan, **not proof that any externally controlled step has happened**. It is tied to `docs/operational-core/PHASE02_EXIT_EVIDENCE.json` and the read-only `scripts/assess_phase02_operational_exit.py` gate. All 12 operational checkpoints start **blocked**. Simulated developer tests or copied online evidence must not change them to "verified".

## Current verified facts

- Consolidated Phase 02 PR #41: GitHub Actions CI #139 **692 passing source tests**; owner's Kali **466 passing local Phase 02 tests**; exact commit `48514555c812bb020d431f63c86a9cde404f7226`.
- Private GitHub repo. PR #41 is draft and unmerged, with no independent review submission found at the audit checkpoint.
- GitHub branch-protection query returned **403 Resource not accessible by integration**. Private repository rulesets query returned **403 Upgrade to GitHub Pro or make this repository public**. Neither 403 means protected branches are enforced. Do not publish the private business repository merely for a free ruleset.
- Previous PRs #32–#39 are separately parked drafts. They must not be bulk merged merely because their blobs passed a source-only conformance test.
- Foundation F01–F03 are source-verified, F04–F09 blocked. The report in GitHub CI is `CI_SOURCE_EVIDENCE_ONLY`: passing CI is **not** production authorization.
- Public Render marketing site is separate from private platform APIs; no dynamic customer execution was enabled by this plan.

## Acceptance gates (evidence requirements)

| ID | Owner action and acceptance criteria | Evidence required | Release condition |
|---|---|---|---|
| P2-G01 | Arrange **independent human** code/security review of PRs #32–#41, verify dependency graph and address findings | GitHub reviews from authorized identities distinct from code authors and tracked remediation | BLOCK until review accepted |
| P2-G02 | Enable enforceable required checks and independent-review rules on private `main` | Provider configuration export or authenticated GitHub policy read and adversarial rejected merge evidence | BLOCK until actually enforced |
| P2-G03 | Build private OneCall peer identity and tenant mapping after reviewing OneCall PRs #3–#5 | Real service-issued proofs, mutual TLS, verified revocation, cross-tenant and replay-negative test | BLOCK, synthetic credentials not accepted |
| P2-G04 | Select legitimate inventory provider with a read-only scope and contract | Named customer/provider consent, tenant ownership, limited connector credentials, negative permission tests | BLOCK until authorized |
| P2-G05 | Validate webhook ingest, delivery state, retry, replay and recovery in private staging | Durable job evidence, fault injection, secrets rotation, incident alerts and downtime drill | BLOCK, in-memory fake jobs not accepted |
| P2-G06 | Implement server-bound per-effect human approval, durable idempotency and external receipts | Distinct authenticated reviewer, verifiable external receipt and independently fetched postcondition | BLOCK, fake approvals/checksums not accepted |
| P2-G07 | Owner authorizes private staging region/host and monthly cost ceiling | Signed operating approval, asset inventory, private egress, identity provider, ingress certificate | No provider provisioning until approved |
| P2-G08 | Security review of migrations 012–015, independent backup and upgrade/restore | Pin reviewed SQL SHAs, test restores on isolated clone, rollback criteria, staging results | NO Kali or live migrations without approval |
| P2-G09 | Execute private-by-design pilot preparation with lawful permission | Owner, contact route, signed consent, notice/privacy/security review, support escalation, breach retention plan | BLOCK customer data intake |
| P2-G10 | Run a strictly bounded real commercial pilot | Measured before/after baseline, real usage, relevant cost, failures, support metrics, operator approval | BLOCK; demo value numbers not evidence |
| P2-G11 | Contract an independent security assessor for staging and recovery acceptance | Findings ledger, remediations, independent retest, key rotation, off-host encrypted restore evidence | BLOCK, self-attestation invalid |
| P2-G12 | Complete F01–F09 and obtain separate owner go/no-go | Reviewed evidence pack and explicitly scoped signed owner approval after independent reviewer acceptance | BLOCK Phase 03 live execution |

Evidence records move from `blocked` to **`evidence-submitted`** only with inspectable external references, SHA-256 and separate owner/reviewer references; the script still reports `EXTERNAL_REVIEW_REQUIRED`, **never** `GO`. Source text cannot authenticate a person, check their independence, prove a GitHub ruleset, or validate external claims. The authorized owner has to establish those facts outside Git.

## Independent security review scope

Reviewers must test not merely that the 692/466 source tests are green but whether the eventual service can actually enforce identity **from verified transport and server sessions**, not client-supplied UUIDs or headers. Review authorization boundaries for each operation, concurrency/idempotency at database level, audit write permissions, tenant RLS bypass paths, key custody/rotation, replay persistence, time skew, credential exfiltration, SSRF, webhook payload framing, timeout exhaustion, rollback, and incident access.

Preserve a finding log with issue, severity, reproducer, affected version, owner, mitigation, retest evidence and resolution. If defects exist, do not approve a merge or production operation until fixed or risk-accepted through a separate documented authority.

## Private GitHub branch enforcement blocker

Current connector has **no branch-protection/ruleset management write action** and cannot verify protection due to API/plan restrictions. The owner must use an eligible **private** account/org enforcement capability or keep the GO gate blocked. A manual two-person checklist can reduce mistakes during source review but **cannot substitute for enforced required checks**. Maintain private repo visibility; upgrading to paid GitHub or purchasing hosting is **not authorized here**.

## Staging and cost — zero new expenditure committed

The `deploy/staging/compose.yaml` file is a source-only profile `owner-approved-staging`, with loopback API ingress and an internal Postgres network. It is not a verified staging environment. Before any provisioning establish region, account owner, real spending limit, service identities, certificate authority, secret store, operations contacts, exit/rollback decision and backup retention. Without a cost ceiling **do not launch a new cloud environment** or enable migrations.

## Migration 012–015 review (source inspection, no application)

| Migration | Intended effect | Verified source restrictions | Required staging review |
|---|---|---|---|
| 012 | OIDC identity links and sessions | Unique issuer/subject hashes, membership FK, RLS, token-vs-OIDC XOR, scoped session verifier | Identity onboarding authorization, existing session compatibility, revoke and rollback on restore |
| 013 | AMBOY M1 dry-run ledger | Model-free unsupported outcome, tenant RLS, append-only events, quota increments | Test privilege limits and genuine user/session binding, no model actions |
| 014 | OneCall identity-test JTI audit | Runtime table/function privileges revoked, identity-test-only purpose, duplicate JTI denial | Trusted signature/fresh revocation **outside SQL**, race conditions, retention |
| 015 | OneCall M2M paired-JTI audit | Two insertions with single transaction semantics, runtime function grants revoked, test-only event trail | Live service-key custody, verified mTLS transport, atomic replay failure and outage handling |

**Source inspection is not an independent security assessment of the SQL**. CI applies migrations 012–015 to disposable PostgreSQL; the existing standalone recovery rehearsal verifies an earlier local upgrade through 011 only. Before real database upgrade, take encrypted recoverable backups of an approved isolated target, rehearse restoration into a **different** isolated database, check sensitive grants and schema invariants, and record DBA/owner approval. Do **not** apply 012–015 to Kali or a customer DB based on this document.

## Operational workflow

1. Keep all outstanding PRs in draft while owners acquire reviewer and protection evidence.
2. Prioritize real identity/staging and independently reviewed read-only provider adapter; controlled write APIs stay disabled.
3. Run negative security and disaster recovery exercises in an explicitly approved isolated environment (not disposable CI or customer production).
4. Only then begin consented pilot onboarding with measurable baselines and bounded budgets.
5. Independent reviewer examines evidence and owner makes a separate GO/NO-GO decision. Source reports are explanatory only; scripts offer no automated GO path.

Run the source status assessor without network, provider tokens, Docker, API or migration operations:

```bash
python scripts/assess_phase02_operational_exit.py
python scripts/assess_phase02_operational_exit.py --require-production-go
```

The first command succeeds if the register is structurally valid and reports `NO_GO`. The second intentionally exits nonzero, including if every external record is merely submitted. Never use exit zero from a source-validation command as permission to operate.

**Release assertion:** NO-GO. Issue #40 remains the operational tracker. No source change authorizes live Phase 03 execution, customer access, secret creation, provider writes, subscriptions, GitHub plan upgrades or deployment.
