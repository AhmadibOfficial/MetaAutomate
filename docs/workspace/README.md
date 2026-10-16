# MetaAutomate Objective Workspace v1.0

## What works

MetaAutomate now offers a browser-based local planning workspace under apps/web, served by the existing FastAPI service on the same origin. Open http://127.0.0.1:8000/ on the Kali workstation after explicitly initializing the local environment.

A signed-in organization owner can:

1. Sign in using a pre-provisioned, high-entropy local access key.
2. See objectives saved for their organization.
3. Create objectives with title, context, measurable target, deadline, constraints, and draft capability selections.
4. Save an atomic draft objective, workflow, proposed task DAG and pending review in PostgreSQL.
5. Open the objective's visual dependency graph, leave and return without losing the plan.
6. Approve or reject the proposal with a reason; review decisions are audited.
7. Sign out and revoke the current browser session.

Roles: OWNER/ADMIN may create, list, read and review; OPERATOR may create, list and read; VIEWER may only list and read. A plan marked APPROVED remains DRAFT and non-executable. No draft capability is enabled.

## Authentication model

This is deliberately a **local developer access-key login, not production registration or email/password authentication**. The browser exchanges a high-entropy developer token once for a revocable session. The session ID is in an HttpOnly, SameSite=Strict cookie, with a separate CSRF cookie verified on every browser-origin write. The database stores irreversible SHA-256 digests for both secrets. Session lifetime is up to eight hours; development access tokens expire after seven days; revoking a token also invalidates its browser sessions.

The browser never stores the access key in localStorage or sessionStorage. Client-supplied tenant identifiers are never trusted. Database transactions use the restricted runtime role and server-established organization context. This is a local-only security model and not sufficient for public customer deployment. Production work must remove privileged DATABASE_URL access from the API, strengthen tenant enforcement against compromised SQL sessions, adopt an identity provider and hardened session handling, add abuse protection/rate limiting and comprehensive security assessment.

Do not expose this development server to the public internet. The Docker Compose API and PostgreSQL ports are bound to 127.0.0.1. WORKSPACE_COOKIE_SECURE=0 is only for the loopback HTTP development origin. HTTPS deployments require WORKSPACE_COOKIE_SECURE=1, an explicit trusted origin and a separate deployment/security review.

## Initializing the existing Kali workspace — once, with approval

From the existing ~/metaautomate-github checkout of this feature branch, run:

    make workspace-init

Read the prompt and type INIT to authorize changes. The script takes a pg_dump backup under ~/metaautomate-db-backups, applies only missing migrations 009 and 010 (never replays 001–008), builds the API container, provisions an example organization and owner with a randomly generated restricted SQL password, and restarts the API.

The script stores the access key only in the ignored, mode-0600 ~/metaautomate-github/.workspace-access-key and writes the restricted APP_DATABASE_URL only into the ignored, mode-0600 .env. It deliberately does not print credentials or submit them to GitHub. Read the access key privately in VS Code, open http://127.0.0.1:8000/, and enter it in the form. Re-running initialization rotates credentials and invalidates older local access keys.

Existing database records remain intact. Do not run docker compose down -v. If an existing DB upgrade fails, keep the backup and review the error; do not repeatedly reapply already completed migrations.

After initialization, users interact only with the browser. No terminal or manual HTTP requests are needed to submit, retrieve, or review objectives.

## Independent acceptance checks

- GitHub CI validates Python tests, PostgreSQL migrations 001-010 and tenant-RLS integration.
- Objective Operations integration verifies two organizations, role restrictions, idempotent saves, work-graph persistence, audit, review transitions, token revocation, and no agent/capability execution.
- A real Chromium browser test signs in, creates a plan through the form, visualizes the DAG, approves it, reloads the page, verifies persistence, checks overview counts, and signs out; a screenshot is attached to the CI job.

No public cloud URL, hosted authentication, external execution engine, AI planning, job scheduling, third-party connections or production authorization is included in this release.


## Operational Core v1 extension

The authenticated workspace now includes the Digital Transformation Assessment. See `docs/operational-core/ASSESSMENT_V1.md` for the precise self-report scoring, receipt verification boundary, safe schema upgrade and testing instructions. Report creation is the first **local** deterministic executed analytical capability; it does not enable outside agent actions.

## Business Autopilot demonstration

The separate [Business Autopilot demo](../product/BUSINESS_AUTOPILOT_DEMO.md) reuses this workspace's pure planner, assessment rubric and synthetic inventory parser to demonstrate assess → plan → approve → simulate → verify. Run `python3 scripts/business_autopilot_demo.py serve` with the API dependencies installed, then open http://127.0.0.1:8090. No database or workspace initialization is needed. It has no real sign-in, tenant data or execution authority, and does not change the authenticated workspace on port 8000.
