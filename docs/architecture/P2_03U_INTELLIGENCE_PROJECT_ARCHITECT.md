# P2-03u — 01 / Intelligence · AI Project Architect

**Source-only, offline, no customer data, no provider connection, no authenticated live agent.** This is a concrete, deterministic AI-readiness and workflow-architecture prototype, not an LLM-backed or production agent product.

## Why this exists

An AI engagement should begin with an explicit business problem, baseline, allowed sources, human owner, security review, and a bounded work graph—not a claim that an agent can autonomously increase profit. P2-03u turns the current MetaAutomate AI Systems & Automation service description into a working demonstration that product stakeholders can interact with and use to define what needs verification.

## Delivered

- **Four representative project architectures:** Lead Qualification; Inventory Resilience; Content Operations; Security Triage. All data and metrics are fictional. Each proposes a success *count* to validate, not verified revenue, avoided loss, CAC, net profit or model quality.
- **Typed workflow graph:** INTAKE -> VALIDATE -> ASSESS -> REVIEW -> EXTERNAL. The internal first three steps can be *simulated*; review stops without authenticated humans, and external calls are permanently blocked. Review cannot be faked by clicking a button.
- **Context-aware design:** Choose data readiness (missing, synthetic or a claimed business-owned source), sensitivity (none, personal, confidential), and whether future external workflow execution is envisioned. The output adapts validation blockers and evidence requirements, but never authorizes production.
- **Strict Python contract:** `synthetic_intelligence_project_architect.py` accepts bounded JSON bytes from a versioned fixture, rejects duplicate keys, unknown scenario IDs and fields, PII-like extra properties, bad booleans, graph cycles/edge rewrites, unauthorized action categories, external nodes without human gates, invalid baselines and false metric units. All project states are deterministic.
- **Side-effect-free graph runner:** `simulate_intelligence_graph` produces a trace for three fictional internal nodes and stops before the two human/external nodes. No model inference, sending, publishing, persistence, payments or network.
- **Static web demonstration:** `apps/site/intelligence/` with a professional accessible white visual layout, four scenarios, dynamic evidence checklist, graph preview, local simulation and JSON export. No freeform sensitive-data input. Explicit CSP blocks `connect` requests. Service page links to the demonstration.
- **Source/client parity:** Browser scenario data is generated from the canonical backend fixture via `scripts/build_intelligence_workbench_contract.py`, with a `--check` test. The separate browser renderer cannot change trusted backend or policy rules.
- **Automated acceptance:** pytest negative security and graph tests, Node script validation, desktop 1440 and mobile 390/360 viewport tests, keyboard focus, JSON export safety, services CTA navigation and no cross-origin requests.

## What this is not

- No OpenAI or other model is connected; rules-based workflow planning is not generative AI inference or a verified AI capability benchmark.
- This is not an authenticated user account, actual AI-agent runtime, a customer orchestration queue, external social publishing, live data ingestion, independent consent verification, AI-generated content or a finished customer engagement.
- The public page does not send project briefs automatically and has no real customer records.
- A browser-exported plan is a proposal for human review, not an authorization token. No ROI or saved costs may be asserted from fictional metrics.
- Do not infer operational readiness from GitHub test success.

## Engineering acceptance

```
python -m pytest -q tests/test_synthetic_intelligence_project_architect.py
python scripts/build_intelligence_workbench_contract.py --check
node --check apps/site/intelligence/workbench.js
python scripts/verify_intelligence_workbench_browser.py
```

GitHub Actions workflow: `.github/workflows/p2-03u-intelligence-workbench.yml` with synthetic screenshots.

## Next identity and integration milestone

**P2-03v — Verifiable Identity & Governed Orchestration**

Integrate real OIDC/MFA identities with pinned rotating issuer keys in an **approved private staging environment**, scoped tenant membership and authorization, a durable reviewed plan state machine, quality-controlled task dispatch, external execution kill switches, replay-safe audit event types, and explicit two-person approvals. Test revocation, cross-tenant escape, key rotation, deadlines, stale/withdrawn consent and staged recovery without accessing real clients or providers. Build AI-model adapters only after sandbox scope, data minimization, cost ceiling and quality/safety evaluation are accepted.

**Release constraints:** Phase 01 remains 3/9 verified; Phases 02–03 operational NO-GO, existing Meta and social integrations are inactive, no new hosting/cloud resources, production data, migrations, token provisioning, subscriptions or external messages. No Render deployment or website publication is authorized by this draft PR alone.
