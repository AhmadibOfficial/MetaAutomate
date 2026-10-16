# Unified MetaAutomate Engineering Capability Registry v1

**Source-only, owner-reviewed engineering evidence inventory. NOT a deployment, feature flag, API executor, or readiness approval.**

This is a **separate evidence overlay** on the existing 33-entry **DRAFT/disabled**
Capability Registry CSV and read-only API. It does not modify migration 008, seed
permissions, organization activation, or execution records.

## Sources of truth

- `docs/registry/engineering-capabilities.v1.json`: 19 engineering entries,
  covering **nine technology areas** (`CAP-*`) and **ten platform systems** (`SYS-*`).
- `docs/registry/capabilities.csv`: the original **33 capability IDs** and
  their unchanged DRAFT status. Each legacy ID maps to exactly one engineering entry
  using `catalog_ids` (mapping does not confer operability).
- `docs/operational-core/FOUNDATION_EXIT_EVIDENCE.json`: the **authoritative
  nine-gate release evidence**. As reviewed: **3/9 verified, six blocked,
  overall operational NO-GO**.
- `docs/registry/engineering-capabilities.v1.schema.json`: machine-readable
  structural schema; the Python validator adds cross-file and graph checks.

## Source-level authority and change control

Once PR #60 is explicitly accepted and merged to `main`, the engineering
manifest is the **authoritative source-controlled map of MetaAutomate's
technology areas, platform subsystems, maturity labels, declared dependencies,
security control expectations and source evidence references**. This authority
does **not** supersede:

- `docs/registry/capabilities.csv` and migration 008 for **legacy DRAFT catalog
  IDs, stored versions and disabled flags**.
- `docs/operational-core/FOUNDATION_EXIT_EVIDENCE.json` for **release gate
  status and operational NO-GO**.
- Real authorization policy, credential review, independent staging acceptance,
  owner signoff or future deployment decisions.

Changes to the engineering inventory require reviewed source commits and green
validation. Its metadata cannot grant permissions, enable integrations,
authorize autonomous workflows or change customer availability.

## Capability lifecycle and evidence upgrades

See [Capability Lifecycle & Evidence-Upgrades v1](CAPABILITY_LIFECYCLE.md)
for source-only transitions, proposal preflight, explicit negative-test evidence,
dependency/security reviews and replay of accepted source changes from the PR #60
baseline. No state here grants operational permission.

## Maturity is never permission

| Maturity | Meaning |
|---|---|
| `VISION` | Future concept; no implementation proof |
| `SOURCE_CANDIDATE` | Related code exists, but not the full capability |
| `SOURCE_TESTED` | Bounded, test-defined source implementation; not operational acceptance |
| `LOCAL_SYNTHETIC_DEMO` | Local fabricated-data demonstrations only |

Every record uses `operational_status: NO_GO` and lists all six blocked
Foundation gates. The inventory has **no operational-ready state** in v1.
The public Render **static marketing website** is not proof of a deployable
private Objective Workspace. Migrations 012–015 remain subject to separate local
change approval. No real business records, AI inference, provider scopes, paid
subscriptions, OneCall federation or autonomous external actions are enabled.

`modules` reference paths in the repository, not necessarily complete working
subsystems. `verification_evidence` points to **source/test definitions**, not
independent proof of a live deployment or a customer pilot. `depends_on` is
engineering architecture, not a database-granted permission or package dependency.
`security_requirements` refer to the manifest's named control dictionary.

## Local validation

Requires Python 3.12, no external library, API, DB connection or subscription.

```bash
python scripts/verify_engineering_capability_registry.py --report artifacts/validation/engineering-capability-registry.json
python -m pytest -q tests/test_engineering_capability_registry.py
```

Validation fails for orphan/duplicate legacy IDs, changes to the 33-entry
baseline, unexpected operational status fields, missing files, invalid controls,
dependency cycles, fake test evidence for vision-only work, or altered NO-GO
release boundaries. CI runs both the dedicated checker and source tests and uploads
a machine-readable report. A PASS means **consistent source metadata only**.

## Updating a capability

1. Keep the established `CAP-*`/`SYS-*` ID stable and edit the existing
   record rather than silently reusing an identifier.
2. Describe **the bounded implemented scope**, link actual source paths and
   available test definitions. Explicitly record what remains unimplemented.
3. Map any new legacy CSV ID exactly once; leave its seed status `DRAFT`
   unless separately authorized through its own security/release workflow.
4. Add dependencies only where meaningful, and link appropriate security controls.
5. Run the offline validator and CI. A higher engineering maturity is not a launch.
6. Require separate independent authorization and a reviewed schema upgrade
   before defining any operational-ready capability or production exposure.

**Current engineering release decision: NO-GO.** Source development is permitted
without weakening the established Foundation, Phase 02 or Phase 03 boundaries.
