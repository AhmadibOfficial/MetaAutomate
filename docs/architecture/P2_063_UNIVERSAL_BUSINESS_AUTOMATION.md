# P2-063 — Universal Business Intelligence & Automation Architecture

**Status: source-only strategy and extension contract; NOT product activation.** Designed 2026-10-28. This branch is based on frozen P2-062 founder-review commit \`e3311341e9cb2747f5a2bdd51d78b6884adccc4c\`. Existing PR #132, the local Kali founder-review worktree, customer GUI, operational policies, identity/tenant boundaries, repositories, SQL data and paused hourly automation remain unchanged.

## North star

**MetaAutomate is an industry-extensible business intelligence, workflow and governed automation platform.** Its purpose is to help an authorized organization identify a high-cost operational problem, bring together relevant knowledge and systems, propose a controlled process, execute only explicitly permitted work, and verify a measurable outcome.

Five currently visible sectors in the P2-062 founder interface—Sales & Customers, Healthcare, Real Estate, Retail & Stock, Cloud & IT—are **illustrative entry points, not a five-industry limit**. Previously modeled retail, wholesale, transportation, logistics, tourism, education and healthcare remain covered in the separate P2-03d contract. Future sectors do not require a new platform, copied UI, or a change to shared authorization gates.

### Design principle

**One simple work surface; many extensible capabilities; sector-specific adapters and controls; evidence before outcome claims.** Avoid a menu of hundreds of inactive modules or claims that conceptual sector mappings are production features.

## Merge the strongest *experience patterns*, not proprietary software

This is independent product design and engineering. Do not copy code, interfaces, trade dress, proprietary prompts, bundled content or commercial claims from third parties. The products below are design benchmarks, not partnerships or integrations.

| Inspiration | Original MetaAutomate design takeaway | Source |
|---|---|---|
| ServiceNow | Unified intake, case/task coordination, workflow context and governed data connections | https://www.servicenow.com/platform/workflow-data-fabric.html |
| UiPath Maestro | End-to-end orchestration across structured automation, AI agents and **human steps**, with safe retries and audit evidence | https://www.uipath.com/product/maestro |
| Zoho One | Coherent business apps, organization-wide navigation, extensibility and unified search without siloed user experiences | https://www.zoho.com/one/overview.html |
| Microsoft Power Platform | Reusable apps, connectors, workflows, agent design and integrated measurement on one underlying data model | https://learn.microsoft.com/en-us/power-platform/developer/get-started |
| Salesforce Agentforce | CRM context, governed AI actions, customer/industry-specific workflows and reusable integrations | https://www.salesforce.com/platform/agentforce-platform/ |
| Healthcare / property / retail / cloud specialists | Specialized capacity, inquiry, property, inventory and FinOps models offered as versioned domain packs; never infer readiness by adjacency | Existing competitor notes supplied by founder; validate each domain separately |

## One product, six architectural layers

\`\`\`
Business person / team
       |
       v
[1. MetaAutomate Home: "What problem should we solve?"]
       |
[2. Objective & case workspace: intake -> plan -> review -> results]
       |
[3. Shared intelligence: policy-aware retrieval, rules, proposals, forecasting]
       |
[4. Orchestration: tasks -> agents -> human checkpoints -> approved actions]
       |
[5. Enterprise connectors: CRM, ERP, channels, documents, data, cloud APIs]
       |
[6. Evidence and trust: identity, isolation, permissions, trace, costs, outcome]
       |
   Versioned domain packs with sector-specific vocabulary and restrictions
\`\`\`

Every layer is planned as a reusable contract, not an assumption that code presently exists or that external integrations work.

### Horizontal capability families (not industry silos)

1. **Goal and objective intelligence:** understand an operational problem, capture measurable targets and constraints, and prioritize a validated opportunity.
2. **Customer and case intelligence:** CRM, inquiries, queues, ticketing, service recovery and multichannel conversations.
3. **Operational planning:** inventory, scheduling, procurement, asset use, capacity, orders, maintenance and handoffs.
4. **Finance and value intelligence:** cost baselines, cash-flow proposals, spend anomalies, reconciliation and verifiable ROI.
5. **Content, documents and communications:** controlled document preparation, classification, multilingual drafting, media workflows and review.
6. **Decision and process intelligence:** cause analysis, bottleneck detection, what-if scenarios, exceptions and explainable recommendations.
7. **Agentic and deterministic automation:** bounded agent proposals, structured workflow engine, human review, safe retries, compensating actions and connector adapter isolation.
8. **Analytics and measurement:** trusted provenance, baselines, period comparison, experiment evidence, usage and error metrics.
9. **Security, identity and compliance:** tenant isolation, least privilege, approval and authorization gates, audit, policy evaluation, secrets boundary and region-specific requirements.
10. **Platform extension:** versioned capability registry, typed domain packs, integration catalog, APIs, localization (Arabic/English and other languages), accessibility and SDKs.

Existing MetaAutomate plans and modules should be *mapped* to these horizontal families, not deleted or prematurely consolidated. Concrete code reuse demands separate architecture and security review.

## Unlimited sectors via controlled, versioned domain packs

A **domain pack** is a source-reviewed descriptor: a unique sector identifier, customer-facing vocabulary, relevant reusable capabilities, possible workflow use cases, domain risk, privacy exclusions and independent required reviews. A domain pack is **never** a license, authorization token, implementation, integration permission, certification, or readiness approval.

- The platform UI can surface recommended packs, but no fixed enum or hard-coded switch becomes the authority for which industries may exist.
- A new sector is added by a reviewed pack conforming to \`contracts/domains/v2/domain-pack.schema.json\`, not by duplicating the app or backend.
- The \`domain-packs.v1.json\` file contains **example design profiles only** and a \`CUSTOM_ORGANIZATION_WORKFLOW\` extension pattern. It is *not* an exhaustive catalog or production-feature list.
- Do not send user-chosen pack IDs, organization IDs or capabilities to an executor as implicit authorization. All operations require independent server-side identity, scope/role, policy, connector and audit checks; client metadata is untrusted.
- Each pack links to shared capabilities by identifiers (not bespoke copies of CRM/finance/AI logic), while retaining specific safety/approval constraints. Regulated workflows require external specialist acceptance.
- No pack can inherit approval from another pack. Healthcare and financial services are especially sensitive: no patient data, diagnoses, claims, banking actions, financial advice or money movement without dedicated security/legal/regulatory review.

### Examples, not a ceiling

Commerce and services; retail and wholesale; healthcare administration; real estate; finance administration; manufacturing; construction; transportation; logistics; hospitality and tourism; education; agriculture and food supply; telecom; energy and utilities; public services; professional/legal services; media and marketing; nonprofit operations; technology and cloud. **New industries beyond these remain supported by the extension schema.**

## User experience

Keep the already-approved, founder-reviewable four-screen UX:

- **Home:** one goal entry, relevant suggested templates and a discreet future "My industry / custom workflow" path, not dozens of tabs.
- **My Work:** cross-sector cases, tasks, approvals and drafts grouped by user objective.
- **Results:** evidence-based operational metrics, source and confidence (never fabricated improvements or invented savings).
- **Team & Settings:** identity, scope, privacy, language and explicitly enabled integrations; segregate developer gates from customer-facing activity.

No new card, route, or feature toggle is authorized in PR #132 while founder testing is in progress. The custom path is a **next product iteration proposal**, not a live feature or claim of support already shipped.

## Universal workflow contract (future)

\`\`\`text
OBJECTIVE_RECEIVED
  -> CONTEXT_VALIDATED (consent / origin / data classification)
  -> PLAN_PROPOSED (bounded and explainable)
  -> APPROVAL_REQUIRED (named accountable reviewer)
  -> POLICY_ADMITTED (server-side, scoped to exact tenant/action)
  -> EXECUTION_REQUESTED (only approved adapter in accepted environment)
  -> EVIDENCE_CAPTURED (immutable-by-process review, result, provenance)
  -> OUTCOME_MEASURED (baseline, units, attribution, confidence)
\`\`\`

Reject by default. Approval is not an unconditional right to execute. Context must be checked at every boundary. No silent autonomous customer communication, spend, clinical inference, infrastructure mutation or financial transfers. Future execution must include idempotency, retries, deadline, cancellation, rollback/compensation, poison queue, and concurrency strategy.

### Evidence model

Each outcome must specify:
- problem/owner/objective/sector/capability/version and source classification;
- starting baseline and measurement window, meaningful units, sample size and source owner;
- approved versus actually executed operations, telemetry and external authoritative receipts;
- uncertainty, confounders and explicit "not verified" labels;
- measured result and savings only if supported, not inferred from drafts, mock data, or self-scored progress.

## Existing source boundaries

Do **not** overwrite or deprecate these sources of truth:
- \`docs/registry/capabilities.csv\`: 33 DRAFT disabled capability IDs;
- \`docs/registry/engineering-capabilities.v1.json\`: 19 engineering entries and their source evidence;
- \`docs/operational-core/FOUNDATION_EXIT_EVIDENCE.json\`: 3/9 verified, operational **NO-GO**;
- \`contracts/domains/v1/cross_sector_workflow_contract.v1.json\`: legacy P2-03d seven-sector/5-stage design;
- \`docs/p2-062-unified-workspace-ui.md\`: frozen founder review and privacy guardrails;
- individual P2-0x specialized architecture documents, database constraints and tests.

The new descriptor is an **independent source-only extension proposal** and does not change the API registry, real permissions, deployment, domain contracts or data migrations.

## Milestones and acceptance gates

| Milestone | What is accepted | What is NOT accepted |
|---|---|---|
| P2-063A, this branch | Design docs, JSON Schema, representative domain-pack catalog, static validation tests | Production domain-pack loader, generic executor, customer operations |
| P2-063B, after founder review | UX research on custom sector intake, programmatically composed objective templates, accessibility, no server writes | Automatically launched services, arbitrary user-provided code |
| P2-063C | Versioned horizontal service interfaces and tenant-safe server-side discovery; all actions **DENY by default** | Public users, external credential access |
| P2-063D | Local policy-signed, human-approved rehearsal with separate domain pack threat model and synthetic inputs | Live provider automation or unsupported business value |
| P2-063E | Independent security/regulatory sign-off, staged credentials, business pilot permissions, measurement plan and verified results | Any claim of broad sector readiness without each pack's evidence |

### Required verification

- Source-only schema and design catalog test: \`python3 -m pytest -q -p no:cacheprovider tests/test_p2_063_domain_packs.py\`.
- Keep all existing P2-062 developer/source/browser tests and founder sign-off gates.
- Real browser verification and external research remain **pending**, not silently completed.
- GitHub Actions billing blockage, F04–F09 and real OIDC tenant isolation stay unresolved until accepted by an independent authority.

**No merge/deploy/purchases, no cloud provider changes, no recruited users, no outbound messages, no safety bypass, no automatic release and no resumption of the paused hourly development automation.**

## Independent source references
- ServiceNow Workflow Data Fabric: https://www.servicenow.com/platform/workflow-data-fabric.html
- UiPath Maestro orchestration: https://www.uipath.com/product/maestro
- Zoho One: https://www.zoho.com/one/overview.html
- Microsoft Power Platform: https://learn.microsoft.com/en-us/power-platform/developer/get-started
- Microsoft Copilot Studio: https://learn.microsoft.com/en-us/microsoft-copilot-studio/overview
- Salesforce Agentforce: https://www.salesforce.com/platform/agentforce-platform/
