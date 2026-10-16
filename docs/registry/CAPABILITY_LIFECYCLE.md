# Capability lifecycle and evidence-upgrade process — v1

**Source-only governance. This process does not unlock any runtime capability.**

## Authorities and boundaries

1. The original **33 DRAFT, disabled** database catalog entries remain unchanged.
2. The merged **19-entry engineering manifest** remains the authoritative source-level inventory (9 technology areas and 10 platform systems).
3. The **Foundation evidence file** determines the operational gates, currently **3/9 verified**. Phase 01 operational NO-GO, Phase 02 operational NO-GO and Phase 03 live-execution NO-GO are independent of this source lifecycle.
4. The lifecycle ledger stores the immutable-*by-process* PR #60 source snapshot and reviewed source-change events. Git review and commit history, not a local JSON flag, are the audit controls. **CI cannot authenticate reviewer identity or prove an external GitHub URL passed.** GitHub branch protection remains an unverified Foundation gate (F04); do not claim tamperproof approval.

## Classification and permitted changes

| From → To | Change type | Measurable evidence |
| --- | --- | --- |
| VISION → SOURCE_CANDIDATE | PROMOTE | Actual linked source module and at least one bounded evidence file; limits and risk review |
| SOURCE_CANDIDATE → SOURCE_TESTED | PROMOTE | Source module, test-definition path, positive and negative test references; passing CI reviewed by human |
| SOURCE_CANDIDATE → LOCAL_SYNTHETIC_DEMO | PROMOTE | Source and tests, explicit synthetic-only scope, external-action deny control, no real customer data |
| SOURCE_TESTED ↔ LOCAL_SYNTHETIC_DEMO | SCOPE_CHANGE | New relevant source evidence and reviewed scope; **not an ordinal promotion** |
| Same classification → same classification | EVIDENCE_REFRESH | Evidence or scope changes, linked tests and human review |
| More-developed → less-developed | DOWNGRADE | Explicit risk rationale and recorded acceptance; operational gating unchanged |

There is **no ACTIVE, GO, DEPLOYED, AUTONOMOUS or PRODUCTION stage** in this lifecycle.
Changing the engineering classification cannot change \`operational_status: NO_GO\`.
A source-tested API module and a synthetic inventory sample are different kinds of evidence,
not proof that all workflows can safely run.

## Evidence-upgrade workflow

1. **Specify scope:** name a stable capability ID, proposed bounded outcome, current and target classification, known limits, risk and catalog links.
2. **Create a proposal JSON:** include a complete proposed entry; positive *and* negative test paths, changed source paths, explicit dependency impact for **every direct dependency**, and security-control reviews for **every declared control**. No private data, secrets or unapproved external URLs.
3. **Preflight offline:** run
   \`\`\`bash
   python scripts/verify_capability_lifecycle.py --proposal docs/registry/examples/lifecycle-proposal.example.json
   \`\`\`
   The result is \`EVIDENCE_REVIEW_REQUIRED\`, never \`APPROVED\` or \`GO\`.
4. **Review evidence:** actually run appropriate tests and check CI, inspect negative cases, verify scopes, dependency limitations and denied effects; record what is genuinely demonstrated. A link to a test **definition** is not a passing test report. A run URL in a JSON file is not cryptographically authenticated.
5. **Separate source acceptance:** only after an explicit owner-approved PR may a change to the engineering manifest be paired with a \`SOURCE_REVIEWED_ONLY\` lifecycle event. The event's PR reference, reviewer identification, rationale, CI run and evidence references are **review metadata**, not trusted signatures.
6. **Source consistency check:** validator replays events from the PR #60 baseline, rejects unexplained changes, unexpected transitions, stale dependency evaluations, missing paths, invalid test coverage, cycles and any operational status changes. It emits a machine-readable report.
7. **Operational release stays separate:** any staging rollout, customer activation, cloud subscription, database migration, AI model, OneCall federation or live external actions require their own independent operational controls, approvals and verified gate evidence.

This first version contains **zero accepted upgrade events**. The example proposal only demonstrates an evidence refresh; it has **not** been approved or applied to the manifest.

## Developer commands

\`\`\`bash
python scripts/verify_engineering_capability_registry.py
python scripts/verify_capability_lifecycle.py --report artifacts/validation/capability-lifecycle.json
python scripts/verify_capability_lifecycle.py --proposal docs/registry/examples/lifecycle-proposal.example.json
python -m pytest -q tests/test_capability_lifecycle.py
\`\`\`

All commands are offline: **no database, network, provider activation, customer data or subscriptions**.

## Event integrity and future versions

A ledger event must capture the full new entry, prior maturity, evidence links,
dependency/control reviews, the approved PR URL, the identified reviewer,
review decision and explicit \`NOT_OPERATIONAL_AUTHORIZATION\` statement.
The validator checks sequential event transitions against the baseline and requires the final state to match the actual manifest. It detects common silent edits, but cannot prevent a malicious contributor from modifying the validator and ledger together. Human review, code ownership rules and independently enforced branch protections are **still required** before treating changes as tamper resistant.

The 19-entry and 33-ID inventory baseline stays fixed under v1. Adding/deleting
capabilities, changing catalog ownership or establishing higher trust statuses
requires a separately reviewed **v2** schema and migration path—not a convenience
edit or a release bypass.
