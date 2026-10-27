# MetaAutomate — ten-stage product roadmap and release gates

Status: **Founder-approved strategic direction; planning specification, NOT release acceptance.**  
Scope: Product delivery stages **S01–S10**, distinct from repository engineering phases **P1/P2/P3**.  
Last reviewed: 2026-10-26. Owner: founder; release/security reviewers **not yet assigned**.

## Non-negotiable decision policy

- **Production and external operations: NO-GO.** Existing Foundation `docs/operational-core/FOUNDATION_EXIT_EVIDENCE.json` policy `NO_GO_UNTIL_ALL_NINE_VERIFIED` governs. Previously recorded count: **3/9**. Do not promote this historical count without reviewing current committed evidence and independent acceptance.
- A file's presence, a source-only test, mock data, a developer-local pass, GitHub “mergeable” status or a PR description **does not** establish deployment readiness.
- GitHub Actions runners are currently billing/spending-limit blocked. Record results as **NOT_RUN/BLOCKED**, never PASSED. Human-approved independent CI-equivalent evidence must be bound to an exact commit and test environment.
- No merges, deployment, database migrations, real customer data, external AI, real social publishing, payments, funding submission or spend without **separate explicit authorization** and the appropriate release gates.
- No invented customers, revenue, Qatar interviews, contracts, legal approvals or ROI. Distinguish **VERIFIED**, **SELF_DECLARED**, **PLANNED**, **UNKNOWN**, and **BLOCKED**.
- Each stage exit requires evidence links/commits, test commands and results, threat-model review, accessibility, privacy/data-handling review, rollback/recovery plan, named human approver and timestamp. Missing evidence = **BLOCKED**. Stage-number completion does not override operational controls.

## Stage sequencing and required outcomes

| Stage | Scope | Minimum exit evidence (not yet accepted) |
| --- | --- | --- |
| S01 Secure Foundation | Identity, organization isolation, RBAC, logs, privacy, testing, backups and recovery | Nine Foundation controls independently accepted, tenant cross-access negative tests, account lifecycle / MFA evidence, redacted audit logs, tested restore, responsible human release sign-off |
| S02 Inventory-to-Growth MVP | CSV import, reconciliation, stock priority, campaign drafts, internal approvals, evidence analytics | Exact-commit browser demonstration with synthetic fixtures, malformed-file and injection regression, stock conservation checks, no auto-posting, accessible flows and authorization tests |
| S03 Qatar Validation & START Readiness | Buyer research, pilot protocol, source proof, pricing hypotheses, team and eligibility | Consent-based interview notes, competitor alternatives, reproducible demonstration, pricing research, QDB requirements rechecked from official source and founder-reviewed dossier; no claim of acceptance |
| S04 Sales, Orders & CRM | Customer records, orders, pipeline, support, quotes, sales reports | Tenant-scoped CRUD/E2E, consent and retention controls, reversible import/export, audit evidence, role-specific workflow tests |
| S05 Finance, Purchasing & Supply Chain | Books, expenses, purchase orders, suppliers, movements and accounting adapters | Reconciliation/invariant checks, permission boundaries, financial disclaimer, durable audit and integration test doubles before live integrations |
| S06 AI Automation & AMBOY | Governed assistance, workflows, recommendations, forecasting | Evaluation dataset, prompt-injection tests, least-privilege tool grants, human-approved sensitive actions, model/cost audit and disable switch |
| S07 Marketing & Omnichannel | Segments, shops, analytics and publishing connectors | Explicit per-provider authorization, scope limits, consent/opt-out, sandbox or synthetic provider tests, human publication approval |
| S08 HR, Payroll & Enterprise | Personnel, attendance, payroll interfaces, enterprise policy | Sensitive-data minimization, jurisdiction review, segregation-of-duties, payroll dry runs, tenant and audit controls |
| S09 Marketplace & Multi-Industry | APIs, extensions, partner adapters and sector templates | Versioned contracts, integration isolation, quotas, permission review, partner security and failure recovery |
| S10 Academy & International | Training, partners, languages, regional resilience | Curriculum quality, accessibility/localization review, jurisdiction-by-jurisdiction compliance, support and disaster recovery proof |

S03 research proceeds **in parallel** with S01/S02; S04+ expansion is conditional on validated earlier exits and market evidence.

## Existing draft dependencies (NOT production evidence)

- [#119 — P2-060 workbench](https://github.com/AhmadibOfficial/MetaAutomate/pull/119) — draft; first MVP scope.
- [#120 — P2-061 secure inventory](https://github.com/AhmadibOfficial/MetaAutomate/pull/120) — draft, stacked on #119.
- [#121 — QDB evidence gate](https://github.com/AhmadibOfficial/MetaAutomate/pull/121) — draft, stacked on #120; this specification belongs here.
- [#129 — reconciliation](https://github.com/AhmadibOfficial/MetaAutomate/pull/129) and [#130 — source-byte binding](https://github.com/AhmadibOfficial/MetaAutomate/pull/130) — draft, separate stacked MVP chain. Review latest branches before changing.
- Newer PRs may exist: review fresh source and branches at each run; do not infer absence from this static index.

## Daily evidence template

Record date (Africa/Lagos), commit SHA and working tree, PR URLs and base/head relationships; stage scope; the one bounded change; exact executed commands and PASS/FAIL/BLOCKED/NOT_RUN counts; browser and security proof; externally validated Qatar interviews and source URLs; commercial assumptions vs actual sales; team responsibilities; Foundation control-by-control status; next safe step; NO-GO/GO decision and named human approval.

## Immediate next gate

S01: read the nine current Foundation entries and link each **blocked** control to concrete source and independent acceptance commands. Do **not** toggle a control to verified based on this document. Separately, S02 must execute #130's new exact-head regression and real Chromium acceptance; S03 must collect consent-based buyer evidence. No application submission or production activation is authorized.
