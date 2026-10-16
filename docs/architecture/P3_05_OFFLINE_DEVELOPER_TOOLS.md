# Phase 03 P3-05 — Developer Tools and Offline SDK

**Development milestone: SOURCE ONLY / NO-GO for real operations.** MetaAutomate keeps moving without cloud subscriptions. Draft P3-01 through P3-04 source branches remain unmerged. All developer tools here are Python-only local simulations, not an exposed API, OpenAPI server, MCP server, production SDK, or tool-calling agent.

## Deliverables

- `apps/api/app/phase03_developer_tools.py` — typed `OfflineToolInvocation` and `OfflineToolResponse` objects; `run_offline_tool` dispatches to **five pre-existing, synthetic, denial-only** functions: capability preview (P3-01), denied plan (P3-02), negative evidence comparison (P3-03), synthetic business KPIs (P3-04), and hypothetical business scenario (P3-04). All outputs remain `decision=DENY`, `executed=false`, `release_authorized=false`. No arbitrary Python imports, HTTP clients, model tools, external provider APIs, shell commands, data imports, or database access.
- `contracts/intelligent/v1/developer_tools.json` — exactly matching **local Python tool** contract: version 1, allowed actions and argument names, operations, no transport, `base_url=null`, all real-world permissions off.
- Source/manifest compatibility check — `validate_source_spec` rejects unknown actions/fields, wrong operation IDs and even **JSON type-confusion** (e.g. `0` masquerading as `false`).
- `offline_developer_doctor` checks **six local versioned source manifests**, including that P3-01–P3-04 external trust and authorization flags remain unapproved. It **does not** inspect real deployments, external identity, independent human review, business ROI or production readiness.
- `scripts/phase03_offline_cli.py` adds `dev-spec`, `dev-doctor`, `sdk-demo`, retaining all previous Phase 03 commands without changing their semantics.
- `tests/test_phase03_developer_tools.py` exercises explicit CLI use, cross-module SDK results, bool/integer confusion, malformed resource/operations, replay-bounded references from earlier milestones, illicit execution arguments, corrupted manifests, local-only boundaries and release-denial defaults.

## Quickstart in a verified P3-05 checkout

```bash
python scripts/phase03_offline_cli.py dev-spec
python scripts/phase03_offline_cli.py dev-doctor

python scripts/phase03_offline_cli.py sdk-demo capability-preview \
  --operation-id business.inventory.stock-preview.v1

python scripts/phase03_offline_cli.py sdk-demo denied-plan \
  --operation-id business.finance.reconciliation-proposal.v1

python scripts/phase03_offline_cli.py sdk-demo negative-proof \
  --operation-id business.inventory.stock-preview.v1 \
  --observed-version 2

python scripts/phase03_offline_cli.py sdk-demo business-metrics
python scripts/phase03_offline_cli.py sdk-demo business-scenario --extra-orders 0
```

These commands accept **only invented DEMO records**, with a fixed synthetic tenant and actor. Business metrics are invented and use `DEMO-UNIT` rather than a real currency. An optimistic `business-scenario` is not a return-on-investment forecast or income guarantee.

### Typed local example for developers (no provider client)

```python
from app.phase03_developer_tools import OfflineToolInvocation, run_offline_tool

request = OfflineToolInvocation(
    action="denied-plan",
    operation_id="business.finance.reconciliation-proposal.v1",
)
report = run_offline_tool(request)
assert report.decision == "DENY"
assert report.executed is False
assert report.payload["human_approval_required"] is True
assert report.payload["execution_authorized"] is False
```

Run Python from the private repository with `PYTHONPATH=apps/api`. No secrets, tokens, provider setup or paid cloud services are required.

## Security and release distinctions

A typed SDK is only a more ergonomic interface; **it is not identity, consent, cryptographic attestation, tenant ownership, or authorization**. The source-generated tool spec is not a public API surface, not proof of live controls and not permission for agents to execute tools. Fixed demo IDs are test fixtures, not grants. The `dev-doctor` preflight checks only local manifest consistency. Its `source_compatible=true` means code and contracts agree, *not* that a provider, customer, staging service, or revenue has been verified.

No operation in P3-05 can grant execution, write to customer accounts, issue payment requests, call providers, deploy workloads, apply migrations or produce authenticated external receipts. All older phase safety gates remain binding.

## P3-06 is a future, explicitly gated implementation

Real authorized effects would require trusted service/actor identity and tenant ownership, scoped provider authority and customer consent, independent signed human approval as applicable, transactional durable replay protection, authentic provider execution evidence, independently authenticated readback, rollback/audit, enforced repo branch protections, operational disaster recovery and formal release authority. **None of these are established by a successful source test.**

**Status:** P3-05 in development. Phase 01 Foundation **3/9 NO-GO**; Phase 02 operational NO-GO [Issue #40](https://github.com/AhmadibOfficial/MetaAutomate/issues/40); Phase 03 real execution **BLOCKED**. This draft preserves repository privacy and does not merge upstream PRs, provision services, or spend money.
