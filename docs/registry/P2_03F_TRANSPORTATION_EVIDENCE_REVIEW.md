# P2-03f — Transportation synthetic evidence-refresh proposal

**Status: PROPOSED / EVIDENCE_REVIEW_REQUIRED — NOT ACCEPTED, NOT OPERATIONAL.**

The source-controlled, machine-readable proposal is [P2_03F_TRANSPORTATION_EVIDENCE_REFRESH.v1.json](proposals/P2_03F_TRANSPORTATION_EVIDENCE_REFRESH.v1.json).

## Scope and rationale

The merged transportation PR [#65](https://github.com/AhmadibOfficial/MetaAutomate/pull/65) contains an offline, fixed-fixture prototype with trip-capacity checks, invented quotations, unsent follow-up drafts, unposted finance examples and fail-closed negative tests. [GitHub CI #38850185421](https://github.com/AhmadibOfficial/MetaAutomate/actions/runs/38850185421) completed successfully for the PR head. Its success is **source-test evidence** only and cannot demonstrate real provider authorization or safe public operations.

The engineering manifest currently has **19 entries**, with no transportation-specific entry. Thus this proposal targets **CAP-BUSINESS** (Business Automation) under lifecycle **EVIDENCE_REFRESH**. Its current and proposed maturity are both **LOCAL_SYNTHETIC_DEMO**. It proposes additional pointers, limited scope clarification and limitations; it does not claim a new maturity tier, readiness certification or a new operational feature.

| Artifact or status | Before | Proposed outcome (only after a distinct future approval) |
|---|---|---|
| Engineering registry CAP-BUSINESS | LOCAL_SYNTHETIC_DEMO / NO_GO | Same classification and NO_GO; transportation evidence attached |
| Cross-Sector Contract v1 transportation | DESIGN_MAPPING_ONLY | **Unchanged** |
| Capability Registry database BIZ-004/011/012 | DRAFT / disabled | **Unchanged** |
| Lifecycle ledger | 0 accepted events | **Unchanged in this PR** |
| Foundation Phase 01 | 3/9 verified | **3/9 — F04–F09 blocked** |
| Phase 02 & Phase 03 | Operational NO-GO | **Unchanged** |

## Evidence coverage

- **Positive design/source tests:** `tests/test_synthetic_transportation.py` (invented trips, consistent draft estimates, correct allocation totals), plus `tests/test_cross_functional_synthetic.py` for previous retail/wholesale source bounds.
- **Negative/safety tests:** `tests/test_synthetic_transportation.py` (cumulative overbooking, unknown/duplicate request IDs, real location/contact fields, boolean/nonfinite units and nonexistent side effects); `tests/test_cross_sector_workflow_contract.py` (design-only sector profile cannot declare source verification or enable operations).
- **Source modules:** `apps/api/app/synthetic_transportation.py`, `apps/api/app/synthetic_business_flow.py`, `contracts/domains/v1/cross_sector_workflow_contract.v1.json`. All references point to repository files, not deployed services.
- **Independent source evidence:** GitHub CI run reference is included for manual review, **not cryptographic authorization**. The validator checks URL format and linked path existence, not CI authenticity, reviewer authority or deployability.

The proposal contains current dependency assessments for **SYS-DATA** and **SYS-INTEGRATIONS**, and explicit control assessments for **EXPLICIT_APPROVAL**, **EXTERNAL_ACTION_DENY**, **TENANT_ISOLATION** and **AUDIT_TRAIL**. Only source-level denial is recorded as tested. All tenant/production auditing, transport safety and real-world authorization remain unverified.

## Review workflow — no automatic application

```bash
python scripts/verify_capability_lifecycle.py \
  --proposal docs/registry/proposals/P2_03F_TRANSPORTATION_EVIDENCE_REFRESH.v1.json \
  --report artifacts/validation/p2-03f-transportation-evidence-proposal.json

python -m pytest -q tests/test_transportation_evidence_proposal.py
```

A valid proposal reports **EVIDENCE_REVIEW_REQUIRED**, `real_execution_authorized=false` and `proposal_was_applied=false`. A green result is only a preflight and cannot approve source changes.

**Not part of this PR:** any edit to `docs/registry/engineering-capabilities.v1.json`, `docs/registry/capability-lifecycle-history.v1.json`, `contracts/domains/v1/cross_sector_workflow_contract.v1.json`, domain API, database migrations or Render service.

### Separate future acceptance, if expressly approved

A *new and independently reviewed* PR must pair a proposed CAP-BUSINESS entry change with a complete sequential `SOURCE_REVIEWED_ONLY` lifecycle event and owner approval. It may update **source evidence only**; it may not change operational `NO_GO` or transport profile `DESIGN_MAPPING_ONLY`. Any proposed sector classification shift must be reviewed independently under an explicit versioned contract update. Genuine passenger/vehicle records, payment and external bookings require their own security, consent and transport safety evidence **and all Foundation operational gates**.

No subscriptions, live integrations, customer data or services are needed for this proposal.
