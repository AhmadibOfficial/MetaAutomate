# MetaAutomate Phase 01 — Foundation exit and go/no-go register

**Reviewed:** 14 October 2026. **Source status:** 3 of 9 confirmed, 6 not operationally verified. **Release:** NO-GO.

## Why this register exists

A green GitHub CI build is evidence of passing controlled source tests, not a claim of cloud infrastructure, MFA, customers or business value. Until the six remaining criteria are verified in their real target environments, MetaAutomate must continue describing Phase 01 as **IN DEVELOPMENT**.

Machine-readable source: FOUNDATION_EXIT_EVIDENCE.json. Local one-command status: make foundation-status. The command writes an ignored JSON report and never contacts cloud providers or alters PostgreSQL.

Even a future 9/9 source declaration only creates a RELEASE_REVIEW_REQUIRED state. Separate independent source validation, live controls and explicit owner decision are required. There is deliberately no automatic release token or publish step.

## Confirmed foundation (source and CI)

- F01 — Architecture and human-reviewed Objective Workspace planning. Evidence: docs/objectives/OPERATIONS.md, Chromium browser acceptance and current green main CI.
- F02 — 15-question deterministic digital maturity assessment, immutable input/report checksums, customer-authorized report generation and existing automated CI.
- F03 — Source-reviewed RLS, tenant-and-user isolation, role authorization, append-only audit and negative tests using disposable organizations and restricted PostgreSQL roles.

These pass as **development foundation**, not as a statement of cloud readiness.

## Operational exit requirements and minimum evidence

| ID | Required outcome | Evidence to collect and independently check | Stop condition |
|---|---|---|---|
| F04 | Enforced merge protection on private main | Live GitHub screenshot/API confirmation of active branch rule requiring Release Evidence Gate, PR review and no unilateral bypass; negative demonstration that failing check blocks merge | Repo is private and main currently unprotected; integration cannot administer rules |
| F05 | Approved, isolated, cost-controlled staging | Named host/region, written owner-approved monthly ceiling, account eligibility, provider invoice/limit, private-only staging compute, segregated staging DB/volume, secrets scope and public-port scan | Only a source template exists; no approved host, cloud resource or spend |
| F06 | Real OIDC, MFA, trusted ingress | Real issuer and client configuration, exact callback HTTPS, verified PKCE/nonce/issuer/audience/JWKS, privileged-user MFA, verified deny-by-default edge, session logout/revocation and private reachability test | Unit tests do not establish live identity or private ingress |
| F07 | Staging-specific backup/restore | Encrypted off-host backup identifier, retention policy, restore on independent clean environment, role/grant/RLS checks, record-count/checksum comparisons, recovery time, named operator and evidence | Existing GitHub disposable recovery and owner Kali restore are not an independent staging DR drill |
| F08 | External end-to-end security/operations acceptance | Threat model, security test report and remediations, two-tenant role matrix, XSS/CSRF/session tests, restricted runtime SQL, rate limits, alerts, vulnerability scan, secret checks, rollback exercise and explicit go/no-go approval | Local tests alone are insufficient |
| F09 | Consented pilot, measured usefulness | Documented eligible pilot organization(s), informed consent and scope, pre-defined primary success metric, dated baseline, authorized user journey, post-use measurement, reproducible evidence, user feedback, retention and a credible causal interpretation | No verified customer usage or measurable value yet |

### Pilot measurement protocol for F09

Use a small invited pilot, not an open launch. Avoid receiving customers' confidential credentials or business-sensitive data through social channels.

Primary pilot process:
1. Obtain pilot permission and a customer problem statement (e.g. follow-up delays or reporting backlog); define a single observable metric, baseline period, verification method and minimum worthwhile change **before** using the system.
2. Invite authenticated pilot staff into an isolated tenant after F04-F08 and data privacy safeguards pass.
3. Have staff enter a legitimate business objective, complete a self-reported maturity assessment and approve or reject recommended draft steps.
4. Measure usability (task completion and time to usable plan), assessment correctness, absence of permission violations and optionally actual process KPIs over the agreed observation window.
5. Record blinded/consented evidence, limitations and repeat tests. Do not claim revenue or cost savings unless independent financial evidence supports attribution.

**Example pilot acceptance thresholds (proposals, not achieved results):** all critical authorization tests pass; at least 80% of invited pilot users finish the objective-plus-assessment workflow without engineering intervention; no unexplained cross-tenant leakage; at least one measured process metric is reported against its baseline. Adjust these thresholds with the owner *before* starting any pilot.

## Deployment and migration lock

- Private GitHub main has no enforced required checks. Do not change repository visibility to public just to bypass account limitations.
- Source migrations 012 OIDC and 013 AMBOY exist and pass disposable CI but have **not been approved/applied on Kali**.
- Do not run make workspace-init on the existing Kali workspace: it rotates the development access key.
- An approved isolated staging host is required before running the source-only deploy/staging/compose.yaml opt-in profile. Port loopback and a compose profile are safeguards, not proof of a live zero-trust perimeter.
- Render static marketing remains separate from the private API. Keep Auto-Deploy and PR Previews Off and require explicit website deployment approval.
- AMBOY M1 is default-disabled. No external AI model, booking, billing or tool action is enabled by Foundation acceptance.

## Decision record and accountability

For each F04-F09, attach independently inspectable evidence and review references in the JSON register only **after** the control exists and has been tested. Record owner and independent reviewer attestations. Secrets, full database dumps, customer PII and private tokens must never be stored as evidence.

Owner release approval must be distinct from source-code merge and from operational infrastructure provisioning. Source code can be reviewed and merged safely while deployment remains NO-GO. Independent review of external evidence cannot be replaced by a text field in this repository.

## Current provider-account constraint

An existing connected DigitalOcean account was readable but showed an account warning and empty droplet inventory. This is not evidence of a usable existing private staging server, approved budget or available capacity. Resolve the account discrepancy or select a provider with acceptable signup/payment verification before considering F05 complete.

**Next owner decisions required:** select an eligible provider and monthly staging budget, nominate a real enterprise OIDC/MFA provider, obtain any GitHub plan/account upgrade required to enforce private main branch protection, and authorize a bounded pilot only after live security gates pass.
