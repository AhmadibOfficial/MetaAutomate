# MetaAutomate Operational Core v1 — First Executable Capability

**Engineering status:** private code release candidate. No cloud deployment, autonomous agent or customer rollout is included.

## First genuine objective-to-outcome capability

**Business Digital Transformation Assessment and Action Planning** accepts a real user's organizational objective and 15 structured self-reported answers across five domains:

1. Strategy and leadership
2. Business operations
3. Data and decisions
4. Customer experience
5. Security and resilience

It produces an actual, reproducible result: overall score, five domain scores, evidence-linked gap prioritization, measurable suggested actions, immutable report, and verification receipt. It is **not** an LLM assessment, company profit predictor, external security audit or a completed operational improvement. Source inputs are explicitly self-reported.

**Objective → validate evidence → compute plan and maturity → explicit permission → persist report → independently recompute scoring → retrieve audit receipt.** The user authorizes generating this report, not arbitrary external actions. The report is independently recomputed against stored answers each time it is requested, to check arithmetic and accidental record mismatch. It does not prove reported facts or outcomes independently.

### API contract (local development application only)

All routes require the same authenticated tenant context as Objective Operations (local dev token or revocable browser session). No user-provided organization or role fields are accepted.

| Route | Role | Operation |
| --- | --- | --- |
| \`GET /v1/assessments/questions\` | All members | Read fixed questionnaire and rating rubric |
| \`POST /v1/assessments\` | OWNER / ADMIN / OPERATOR | Explicit, idempotent report generation |
| \`GET /v1/assessments\` | All members | List that organization's reports |
| \`GET /v1/assessments/{uuid}\` | All members | Recompute and verify saved report |

The POST needs \`Idempotency-Key\` (12–100 safe characters) and \`X-Assessment-Consent: generate-report\`. Same-key/same-body retries return the **same** stored report and do not duplicate audit events. Same-key/different-content requests are rejected (409). A unique key in another organization is isolated.

Validation requires exactly one integer 0–4 score for each of the 15 fixed question IDs, a business label (3–120 characters) and a plain-language objective (15–300 characters). Unknown/missing/duplicate answers, extra identity fields and non-integer values fail with HTTP 422.

### Output and receipt

- Scoring version 1.0.0; 15 equally weighted 0–4 statements (60 points maximum).
- Five domain scores 0–100 and equally weighted total 0–100.
- Each recommended action cites the weakest scored question in its domain, with a suggested monitoring metric.
- Reports are stored in tenant-scoped \`digital_assessments\` (migration 011) under forced RLS and a least-privilege runtime role.
- SHA-256 fingerprints for canonical inputs and report; each fetch verifies the current saved report against a fresh calculation.
- Append-only \`audit_events\` records assessment creation once per idempotency key.
- Runtime cannot update/delete saved receipts. No tool calls, agent runs, external effects or changes to the 33 DRAFT registry capabilities.

**Limitation:** a hash stored alongside its own data is not a digitally signed, tamper-proof attestation against a fully privileged database administrator. Independent business outcome verification is a later milestone. No security-sensitive personal information should be entered in the assessment.

### Authenticated browser workflow

Under the existing local Objective Workspace, sign in as OWNER/ADMIN/OPERATOR and select **Digital assessment**. Enter an objective, complete each question, and explicitly authorize report generation. Inspect domain scores and ordered actions; download the JSON receipt, navigate to report history and reload saved details. VIEWER may read reports but not generate them. Cookies, CSRF, tenant isolation and role checks continue to be server-enforced.

The public Render site under \`apps/site\` is **unchanged**. It does not connect to this API. The Operational Core assessment requires the private development application's PostgreSQL database and local service.

### Quality gates

CI applies migrations 001–011 to an **ephemeral** PostgreSQL instance. It runs pure scoring tests, owner/viewer/two-organization API integration, receipt integrity and idempotency checks, no-agent/no-tool checks, and Chromium sign-in → assessment → report → download → reload → history → logout. All existing Objective Workspace tests also run.

The operational code has no LLM model connector and no cloud service. Do not label it as autonomous AI execution, real-world transformation or verified ROI.

### Explicit local installation (approval required before altering an existing DB)

The branch **does not** automatically migrate any user's Kali development database. Once the feature is reviewed, backed up and approved for local installation, from the existing secure Kali checkout:

    # Make sure the repo is on a reviewed revision and Docker PostgreSQL is healthy
    make db-upgrade

The \`db-upgrade\` script verifies prior migrations, creates a separate local \`pg_dump\` backup, and only applies missing migrations 009, 010 and 011. Do not replay 001–008 against an existing database. Do not use \`docker compose down -v\`; that deletes local database volumes.

If your existing local Objective Workspace is initialized, after approved migration restart only the API. Avoid rerunning \`make workspace-init\` merely to install migration 011: that initializer **rotates development credentials**. If the runtime role does not exist, stop and investigate instead of attempting a partial schema change.

### Operational Core v2 readiness

Before production/private staging: replace local developer access-key login with reviewed production organizational identity (the OIDC proposal in PR #6 remains **unmerged**), eliminate privileged database credentials from the API container, assess tenant-context SQL trust, enforce abuse rate limits, protected hosting, backup/restore, observability, secrets management and a professional security review. These have not been completed by v1.

Next evidence milestone: compare proposed actions to **actual measured results over time**, with authoritatively sourced tool receipts where permitted, not just self-report arithmetic. Follow with Amboy's guarded intelligence interface only after identity and risk boundaries are in place.
