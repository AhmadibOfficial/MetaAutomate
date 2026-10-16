# Phase 02 operational execution and external acceptance runbook

**State:** READINESS PREPARATION ONLY — `NO_GO`. **Phase 01: 3/9 verified.** This is a reviewer and operator packet, not a service deployment or an approval record.

**Primary tracker:** GitHub issue #40. **Source evidence:** PR #41 (GitHub 692 / Kali 466 passes), PR #42 (GitHub 358 passes). **Current runnable source:** PR #43 provides only the unrouted offline inventory response boundary. Approval forms below are intentionally blank.

## 1. Separation of duties

The implementer may author branch code, tests, CI and security design. A *separate qualified human identity* must independently review code and applicable security claims; an authorized repository admin must establish branch enforcement. The business owner must approve real infrastructure spend, staged migration targets, customer contact and each pilot. Provider scopes/approvers must come from server-validated upstream identity, not request JSON.

**Strict no-go:** no automatic PR merge, no changing a private repository public to unlock controls, no plan purchase or staging provisioning from this document, no Kali migrations 012–015, no real customer import, no provider calls, no real writes, no payments and no Phase 03 agent actions.

## 2. Stage 0 — verify source safety and release controls

- Confirm original PRs #32–#39 plus conformance #41 and evidence #42 are still drafts and unmerged; record each exact immutable commit SHA. There is no approval from the original author's own review.
- Ask the qualified independent reviewer to evaluate the combined source tree and cross-PR dependencies, inspect negative tests and mark findings on GitHub. Reviewer must not be the implementer, and must document acceptance or required remediation with exact SHA. Code review cannot by itself authorize a deployment.
- Repository owner checks GitHub private `main` branch protection/ruleset configuration. **Current API observation: 403 `Resource not accessible by integration`**, with a reported private ruleset plan limitation. That observation does not prove enforcement; do not falsely mark the gate passed. Preserve repository privacy.
- Set enforced required checks (source Python/PostgreSQL validation, disposable backup/restore and release-evidence gate), independent approvals, stale-approval dismissal and no unreviewed direct push. Verify merge is rejected if checks or approvals are missing.
- If GitHub plan does not support required private-repository controls, keep merge and deploy **NO-GO** and document alternative protected workflow for independent approval. An alternative manual promise is not equivalent to GitHub-enforced protection; do not tick P2-G02 for it.

## 3. Stage 1 — real service identity and read-only adapter

- Review OneCall PRs #3 (pilot authentication), #4 (identity assertion issuer) and #5 (backend-only M2M issuer) in their dependency order. Their current state is DRAFT/UNMERGED.
- In an explicitly authorized isolated environment only, use distinct product/service credentials and mTLS with current certificate validity, revocation and rotation tests. Bind the OneCall assertion subject to the **authoritative OneCall backend identity** and to tenant/product scope; never link users by matching email.
- Verify separate Ed25519 identity and service proofs, signature context, audience, scope, expiry, fresh revocation/tokenVersion, atomic dual-JTI replay consumption and signed, independently recorded denial events. Test cross-tenant, stolen assertion, invalid SAN, expired cert, blocked account, service outage and credential rotation. Source simulations do not satisfy this evidence.
- Before **any real provider read**, identify an actual provider and secure legal/contractual authority for its API/data. Approve minimal `inventory.read` scope, bind access to a server-established tenant and explicit data-owner consent, restrict egress/DNS/TLS pins or trust requirements, set response-size/rate limits, redact logs and define deletion/retention. Test revocation, pagination abuse, SSRF/path tampering and one customer's attempt to read another's data.
- `apps/api/app/provider_read_boundary.py` accepts **invented fixture bytes only** and never calls a network; it proves parser behavior but **not** a real authorized adapter.

## 4. Stage 2 — private staging and database integrity

- Obtain business-owner written approval of hosting provider, data region, dedicated private service boundaries, exact monthly **cost ceiling**, maximum resource types, owner of bills, alerts and stop mechanism. Budget is **not yet authorized**.
- Before provisioning, agree ingress policy (private only), real user identity provider with MFA, segregated PostgreSQL/Redis access, certificate and key lifecycle, secrets rotation, audit retention, encrypted backup location, privacy ownership and rollbacks.
- Independently review migrations 012–015 against current production-like schema, lock behavior, DDL permissions, transactional recovery and application compatibility. Obtain **target-specific authorization** before applying them to Kali or any non-disposable environment. Review which changes are additive and which require data migration.
- Rehearse backups and restore on a separately authorized staging instance; verify restore correctness, tenant isolation, key rotation, loss-of-service, bad migration rollback and RPO/RTO from recorded timestamps. Passing disposable CI is insufficient.

## 5. Stage 3 — durable delivery and controlled effects

- For P2-04, run a worker/queue with durable job IDs, per-tenant limits, read permissions and authenticated callback origin. Require signed webhook bytes and transport identity, replay-safe deduplication, poison-message dead letter, bounded exponential backoff, explicit operator recovery approvals and operational monitoring. Test double-delivery and provider outage.
- For P2-05, verified business approvers must be separate from implementers and operators where appropriate. Bind each approval to exact tenant, principal, effect, target, amount/diff, expiry and version, with audit retention and transaction-safe idempotency.
- Finance writes need stronger approvals than CRM proposals. Do not grant execution based on `SIM_ENDORSE`, fake checksums, self-reported booleans, a green CI badge or an AI-generated authorization decision.
- Upon *later separately authorized real execution*, require an authentic provider-issued receipt and an independently authenticated readback/postcondition check. Model inference and automation must remain out of the real action path until release authority grants it. A provider receipt must not be invented to make tests green.

## 6. Stage 4 — privacy, pilot and objective value

- Obtain customer permission, permitted processing purpose, responsible party, provider terms, access control, retention/deletion schedule and incident notification runbook. Do not import real customer data into CI or fictional demos.
- Pilot operator records baseline and a limited set of audited authorized tenants, exact requested actions, reliability, incident rates, support response times and service spend. Distinguish observed savings/revenue from hypothetical or claimed results.
- Use conservative unit economics: `net_value = independently verified financial benefit - operating costs`. If evidence is missing, report `NOT_MEASURED` rather than `0`, and do not promise income generation.
- Execute an independent attack simulation: IDOR/BOLA, CSRF/session, multi-tenant reads, expired credential, key rotation, replay, malformed JSON, webhook spoof, queue race, fault injection, backup/restore rollback and privilege escalation. Each finding needs remediation and independent retest or written risk-owner acceptance.

## 7. Mandatory evidence record (human-filled only)

For **each** gate in `contracts/engineering/phase02_external_acceptance_tasks.json`, record:

| Field | Required human/operational value |
|---|---|
| Gate ID and exact code/head revision | P2-Gxx, commit SHA and deployed release revision |
| Environment and tenant class | Approved environment, synthetic/authorized pilot classification |
| Decision maker | Real authorized owner identity and independent reviewer identity |
| Evidence | Immutable CI link, independently authenticated provider/IdP/network record or signed report |
| Negative result | Reproducible attacker/rollback test outcome and remediation evidence |
| Costs and permissions | Written approved budget ceiling, provider scope and customer consent if applicable |
| Decision | ACCEPT / REJECT / RISK-ACCEPT, signed by competent human authority |
| Timestamp and review expiry | Actual timestamp and when evidence must be revalidated |

A field left blank is **not approved**. The accompanying machine-readable checklist is intentionally all `blocked`; editing its flags is not proof of operational execution or approval.

## 8. Completion rule

Release authority must obtain independently verifiable evidence for **all 12 Phase 02 gates** and separately complete **all nine Phase 01 gates**, approve customer/privacy and budget boundaries and sign an explicit GO for the named exact deployment version. Do not use this runbook as standing permission for future effects.

**Result today:** engineering and operational handoff preparation, not deployed Phase 02. **Phase 03 live execution remains blocked.**
