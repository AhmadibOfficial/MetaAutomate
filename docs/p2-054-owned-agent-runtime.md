# P2-054 — MetaAutomate-Owned Multi-Agent Execution Runtime

**First-party by design.** The orchestration, agents, bounded working context, durable task queue, leases, retry/dead-letter logic, virtual compute credits, approvals, evidence receipts and local interoperability adapters are implemented in MetaAutomate source code. No paid AI provider subscription, API key, hosted agent SaaS, external model, cloud resource, Redis service or GPU is required to run the deterministic four-agent workflow.

## Run an actual offline workflow

Requires Python 3.12+ and only the standard library. **The input is fictional demo inventory; do not interpret the output as audited customer financial evidence.**

\`\`\`bash
PYTHONPATH=apps/api python -m unittest discover \
  -s tests -p 'test_p2_054_*.py' -v

python scripts/run_owned_multiagent_demo.py \
  --db /tmp/metautomate-p2-054.sqlite3 \
  --output /tmp/metautomate-p2-054-report.json
\`\`\`

The command submits and processes a durable four-agent business task, verifies the evidence chain, checks the final numerical verification receipt, and prints a SHA-256 of the result JSON.

To process a user-authorized **local** JSON inventory document instead of fictional fixture data, use the same schema returned by \`demo_payload()\`, provide the file path, and explicitly declare the data permission:

\`\`\`bash
python scripts/run_owned_multiagent_demo.py \
  --db /private/metautomate/authorized-run.sqlite3 \
  --input-json /private/metautomate/inventory.json \
  --authorized-data \
  --tenant authorized_project \
  --actor authorized_owner \
  --request-key private-demo-20261018-001 \
  --output /private/metautomate/result.json
\`\`\`

The CLI applies an owner-only 0077 process umask for files it creates; this is **not encryption**. Do not process confidential or regulated customer records until encryption, retention, identity and secure hosting are independently reviewed. Use pseudonymous aggregate inventory data first.
 Restarting the process and reusing its request key returns the same workflow ID without duplicate execution.

### Agents that perform real work

1. **Inventory agent**: computes reorder quantities and current stock value from bounded SKU input.
2. **Business agent**: calculates replenishment requirements and prioritizes the top three shortages. All money values are in user-supplied currency **minor units**.
3. **Creative agent**: produces a ready-to-review inventory message for the stated audience, with publishing authorization explicitly false. This is deterministic text, **not neural language generation**.
4. **Verifier agent**: independently recalculates inventory quantities, financial totals and priorities from original inputs, then checks the upstream results and no-publication boundary. A success receipt is meaningful computation evidence, **not evidence that source bookkeeping records are genuine**.

With the sample inventory, the expected shortage for MAIZE25 is 13 units, estimated replenishment is 1,625,000 minor NGN units, and stock-on-hand value is 2,825,000 minor NGN units. No purchase is placed.

### Durable execution behavior

- **Queue:** SQLite WAL with transactional claim and 30-second worker leases. Progress survives process restarts on the same private disk.
- **Retries:** exponentially backed off transient failures, maximum three attempts. Exhausted tasks are marked FAILED/DEAD and cannot silently masquerade as successful.
- **Idempotency:** tenant-scoped unique request keys and canonical SHA-256 input fingerprints; reused keys with changed payload are rejected.
- **Budget:** admission requires at least six local virtual compute units (2 inventory + 1 business + 1 creative + 2 verification). These credits are *not money* and cannot authorize provider spending.
- **Bounded memory:** at most 80 stock records, 25 KB original input, 45 KB per artifact, four fixed specialists and no unbounded prompt or model memory.
- **Evidence:** each step stores result JSON and SHA-256; every event chains to the previous hash. This detects accidental or partial tampering but **is not a signed immutable audit system**; an administrator who can rewrite the entire database could recompute hashes.
- **Tenant scope:** every external read requires a tenant identifier. This is a local internal boundary, **not an authenticated public API**. A production service must derive the tenant from an authenticated OIDC principal.
- **Approval:** publishing or purchasing requests end at WAITING_APPROVAL with distinct reviewer identity and substantive reason. An approval yields APPROVED_NOT_EXECUTED; it **never executes the external side effect**, moves money or publishes social content.

### Standards boundary

MetaAutomate owns the runtime; A2A and MCP are interoperability standards, not commercial dependencies.

- \`apps/api/app/owned_agent_interop.py\`: in-process JSON-RPC-style \`tools/list\` and \`tools/call\` for **two actual read-only tools**. The trusted tenant must be injected by a future authenticated host. Requires MCP 2026-07-28 metadata.
- An A2A-inspired task status/artifact mapping translates internal QUEUED/RUNNING/COMPLETED/APPROVAL/FAILED states to task concepts.
- Current interfaces **are not a full remotely compliant A2A or MCP server**. Network transports, schema negotiation, streaming, authentication, protocol validation and secure remote discovery are not yet implemented. Do not register a public tool URL or claim compliant A2A federation.

Relevant current specifications:
- https://github.com/a2aproject/A2A/blob/main/docs/specification.md
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/server/tools.mdx

## What this intentionally does not claim

- No human-level autonomous intelligence, Theory of Mind, consciousness, open-ended reasoning or training a foundational LLM from scratch.
- No real model inference or media generation from this component; those are separate licensed local engine acceptance tasks.
- No persistent customer chat, user logins, external tool permissions, cloud hosting or private production Postgres queue.
- No backend connected to the public Render static website, no real private OIDC staging, no provider calls or subscriptions.
- No signed independent proof of commercial acceptance or customer outcomes.

## Next private operational gate

1. Resolve GitHub Actions issue #100 so **exact-commit** tests and the four-agent example execute and provide verified evidence. Until then, tests are authored but CI status may be unknown/failing before execution.
2. Validate on local Kali using an isolated disk, Python 3.12, read/write quotas, clean restarts and race/concurrency fault injection. Protect SQLite database permissions; use only demo fixtures until encryption/retention and consent are independently assessed.
3. Rework the persistence adapter for authenticated organization-bound PostgreSQL with RLS, transactionally reserved budgets, signed approvals, encrypted artifact handling and operator-approved migrations; preserve Phase 01 3/9 and Phases 02/03 NO-GO.
4. Add a rights-cleared local small-language-model process behind a **separate bounded agent** only when the model weights/checkpoint are independently verified and an egress-isolated runtime with measurable CPU/GPU capacity is available. The engine may remain useful with deterministic agents if no local model can run.
5. Build an authenticated private queue-worker deployment and instrument failure/replay/latency/cost metrics, signed evidence and cleanup. Deploy only after operator's privacy/security/financial gate—not from this source PR alone.
6. Expand read-only MCP bridge / authenticated A2A protocol compatibility only after transport/auth interoperability acceptance. Never assume A2A agent signatures confer tool authority.

## Release boundary

This branch is stacked on draft P2-052 (PR #110). **Keep draft, do not merge or deploy** until the actual standard-library tests and four-agent demo are run and verified. No paid resources, private migrations, global model services or customer jobs were activated.
