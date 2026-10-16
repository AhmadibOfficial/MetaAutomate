# P2-03g — CAP-BUSINESS transportation evidence lifecycle acceptance (draft)

**Status: prepared for explicit owner review; no current approval or merge.**

This source-only acceptance change is to carry forward the separately accepted **PR #66 proposal packet**, not authorize customer operations. Once fully prepared, the same PR must pair the complete proposed `CAP-BUSINESS` registry entry with the next sequential `LCE-0001` source event. The lifecycle event is **staged** in this draft branch and only enters the authoritative history if this PR is separately approved and merged. A pending-review marker must **not** be mistaken for an owner signature.

The previous accepted proposal is `docs/registry/proposals/P2_03F_TRANSPORTATION_EVIDENCE_REFRESH.v1.json`, original transport test evidence is from [CI 38850185421](https://github.com/AhmadibOfficial/MetaAutomate/actions/runs/38850185421), and formal proposal preflight passed [CI 38851025674](https://github.com/AhmadibOfficial/MetaAutomate/actions/runs/38851025674).

## Review criteria

- `CAP-BUSINESS` remains `LOCAL_SYNTHETIC_DEMO`, `NO_GO`, and retains its existing 11 catalog IDs, direct dependencies, security requirements and six blocked gates.
- New source paths and test definitions document **synthetic-only** retail, wholesale and transportation modules; a linked passing test definition/CI reference does not attest to live transport safety, tenancy, provider permissions or production auditing.
- Event ID `LCE-0001`, exact current proposal payload, historical source baseline, verified dependency and control assessments, GitHub PR review reference and explicit `NOT_OPERATIONAL_AUTHORIZATION` separation must replay deterministically.
- Transportation remains `DESIGN_MAPPING_ONLY` in Cross-Sector v1; no new sector-level capability ID or enabled feature is introduced.
- The repository's first-party validator and negative tests must reject silent changes, missing reviews, unauthorized promotion, changed status or attempts to waive Phase 01–03 release gates.
- The pending reviewer marker in the staged event is an explicit **review hold**. Following separate owner approval, replace it with truthful sign-off metadata, run CI again, and **only then** consider merging. The source CI currently validates field format, not the actual authority of a human reviewer; branch enforcement is a separate Foundation blocker F04.

## No operational change

Phase 01 Foundation is 3/9 verified (F04–F09 blocked). Phase 02 remains operational NO-GO, and Phase 03 live execution remains NO-GO. No real bookings, fare or payment processing, customer messages, vehicle/passenger data, migrations, external connections, cloud deployments or subscriptions are part of this PR.

**CI success means source inventory consistency and review readiness, not approval to ship services.**
