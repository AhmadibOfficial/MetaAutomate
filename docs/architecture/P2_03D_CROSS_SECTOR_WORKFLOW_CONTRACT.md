# P2-03d — Cross-Sector Business Workflow Contract v1

**Status: source-only contract with two synthetic references and five design-only mappings. This is not a sector product launch.**

## Why this exists

The retail and wholesale P2-03c sample connects **stock availability → unissued sales quotation → unsent customer follow-up → unposted finance illustration → verification** using committed fictional records and `DEMO_CREDITS`. Cross-Sector v1 defines common *semantics* so a future team can examine transportation, logistics, tourism, education and healthcare without presenting hypothetical sector adapters as working systems.

**Authoritative design contract:** `contracts/domains/v1/cross_sector_workflow_contract.v1.json`, with structural schema `cross_sector_workflow_contract.v1.schema.json`. Exactly seven sector profiles and exactly five stages. Profiles carry their own capacity, quotation, communication and finance *vocabulary*, privacy exclusions and reviews.

## Stage model

| Stage | Contract meaning | Explicit denial |
|---|---|---|
| AVAILABILITY_PREVIEW | Stock or **hypothetical** capacity feasibility | No inventory mutation, real booking or reservation |
| QUOTATION_DRAFT | Bounded synthetic quote/estimate | No submitted sale, actual invoice or legal commitment |
| CUSTOMER_FOLLOWUP_DRAFT | Review-only communication idea | No personally identifying contact details or messages sent |
| FINANCE_PREVIEW | Unposted example journal/estimate | No payment, ledger posting or claims of recognized revenue |
| VERIFY_INVARIANTS | Trace/provenance, bounded arithmetic and no side effects | Not live acceptance, regulated sector certification or operational GO |

`readiness=SYNTHETIC_REFERENCE_ONLY` is restricted to the exact **retail** and **wholesale** committed P2-03c data and tests. It does not mean customer-ready. All other profiles are `DESIGN_MAPPING_ONLY`; none can select an existing source scenario. This version **does not compute five new sector transactions**.

## Sector-specific adaptation map

| Sector | Availability model | Proposed quotation & follow-up | Important exclusions |
|---|---|---|---|
| Retail (synthetic reference) | Stock units | Draft sale and unsent confirmation | Real stock, customers, payments |
| Wholesale (synthetic reference) | Bulk stock units | Draft bulk order and payment-terms review | Real buyers, trade credit, finance |
| Transportation (design) | Vehicles, route/trip capacity | Unissued trip estimate; rider update draft | Driver/passenger details, geolocation, actual dispatch |
| Logistics (design) | Route/shipment slots | Unissued delivery quote; milestone update draft | Addresses, shipments, custody and live tracking |
| Tourism (design) | Tour/room capacity | Unissued reservation estimate; guest enquiry draft | Travel identities, supplier booking, refunds |
| Education (design) | Classroom/enrolment capacity | Unissued fee estimate; learner enquiry draft | Minors' records, grades, guardians and real fees |
| Healthcare (design) | Administrative appointments only | Unissued admin estimate; admin enquiry draft | **All patient/clinical records, diagnoses, triage, prescriptions, insurance claims** |

The five design profiles cannot borrow retail inventory maths as sector evidence. Each requires separately validated domain models and independent safeguards before any prototype uses additional *synthetic* fixtures.

## Trust boundaries

- Local static JSON, Python standard library and a fixed committed P2-03c fixture. **No new API route, executable adapter, runtime permission, schema migration, external URL, cloud subscription or real customer data.**
- The runtime remains `NO_GO`; BIZ-004, BIZ-011 and BIZ-012 remain DRAFT/disabled. Adding design profiles **does not alter** the 19-entry engineering registry or accepted lifecycle events.
- Profile `required_reviews` are engineering obligations, not completed controls; explicit `excluded_data_categories` prohibit sensitive fields from entering the design scenario.
- Healthcare review includes `clinical_boundary`; education includes `minors_and_learners`; transportation includes `transport_safety`. These controls do not claim regulatory compliance.
- Stable sector IDs and five stages are intentionally pinned in the v1 offline validator. A structural JSON Schema supplements, but does **not replace**, cross-file and fail-closed checks.
- The standard-library validator references the **existing** retail/wholesale preview and checks deterministic fixture SHA-256, order trace and its no-effects assertions. It exposes only a local evidence report; **no service deployment**.
- A JSON checksum is an integrity aid, not a signature, approved customer receipt or external audit attestation.

## Offline acceptance

```bash
python scripts/verify_cross_sector_workflow_contract.py --report artifacts/validation/cross-sector-contract-v1.json
python -m pytest -q tests/test_cross_sector_workflow_contract.py
```

The validator must reject unknown sectors, duplicate profile IDs, altered stage effects, fabricated source claims for the five design-only profiles, missing reviews or exclusions, changed Foundation NO-GO, real currency and foreign capability IDs. A passing result means **consistent source-only design evidence**, not operational acceptance.

## Future discipline

Move **one sector at a time** from `DESIGN_MAPPING_ONLY` toward source-tested synthetic code only through a separately reviewed v2 contract and lifecycle proposal, including its own fabricated fixture, privacy/security review, authorization proof, negative tests and dependency impact. Do not reuse live patient, learner, passenger, tourist, delivery or payment records in demonstrations.

Foundation status remains **3/9 source verified**, gates F04–F09 blocked. Phase 02 operations and Phase 03 live execution remain **NO-GO**.
