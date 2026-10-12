# MetaAutomate Objective Operations v1.0

**Status:** integrated engineering milestone; local/development identity model, not production authentication. No autonomous execution.

## Architecture

- POST /v1/objectives/preview remains the original read-only, non-persisting development preview.
- Migration 009_objective_operations.sql adds SHA-256-based token metadata, restricted metaautomate_runtime database role and app.authenticate_api_token() context helper.
- New operations are under /v1/objective-operations and require an opaque Authorization: Bearer mat_dev_... token associated with an ACTIVE user membership in an ACTIVE organization.
- POST /v1/objective-operations accepts the existing PreviewRequest contract and requires Idempotency-Key (12-100 safe characters). It reuses deterministic capability validation and DAG construction, then atomically persists the draft objective, workflow, tasks, task dependencies, pending review, idempotency receipt, and append-only audit event.
- GET /v1/objective-operations lists that tenant's objectives; GET /v1/objective-operations/{uuid} retrieves the persisted objective, graph, and review.
- POST /v1/objective-operations/{uuid}/review takes decision APPROVED or REJECTED and a reason. Only OWNER and ADMIN may decide; OPERATOR may create, VIEWER may read.
- A reviewed plan remains DRAFT. Approval does not grant execution, enable capability definitions, enqueue work, or contact external systems.

## Security boundaries

This release separates APP_DATABASE_URL (restricted SQL role) from DATABASE_URL (migration/seeding administrator). The API refuses objective operations with HTTP 503 when APP_DATABASE_URL is absent. The runtime role cannot query the token table. Only hashed token digests are stored in PostgreSQL. Expired/revoked tokens, suspended memberships and inactive organizations fail closed.

Each request authenticates inside a transaction and establishes transaction-local tenant/user context before touching RLS-protected rows. Tenant IDs are never accepted from request headers or bodies. PostgreSQL tenant GUCs remain editable by a compromised SQL session; production still requires independently enforced identity authorization, stronger permissions boundaries, secret management, abuse controls and secure onboarding. Do not expose these development endpoints on a public network.

## Validation

GitHub Actions applies migrations 001-009 to ephemeral PostgreSQL, seeds 33 disabled DRAFT capabilities, runs Registry RLS checks, activates a CI-only restricted login, and runs scripts/verify_objective_ops.py. It tests unauthorized access, role restrictions, atomic persistence, same-key replay, conflicting-key rejection, cross-organization 404, review permissions, duplicate-review conflict, revocation, audit, and absence of capability executions.

Local make ci-local creates a disposable database. Objective operations integration there requires a separately provisioned APP_DATABASE_URL. Credentials are not embedded in the GitHub repository.

## Browser workspace and local setup

This PR includes a usable, responsive browser workspace under apps/web. The Objective Workspace supports local access-key sign-in, revocable HttpOnly sessions, CSRF protection, objective creation, persistent DAG visualization, approval/rejection, an overview dashboard, and sign-out.

See docs/workspace/README.md for the complete local rollout, security boundaries and browser acceptance tests.

On the established Kali checkout, the one-time setup is a single command:

    make workspace-init

The command asks for explicit INIT approval, creates a pre-migration database backup, installs only missing migrations 009-010, provisions restricted runtime credentials and a seven-day development access key, then restarts the API. The ignored access key is saved in .workspace-access-key with permissions 0600. The database connection credentials remain in the ignored .env file with permissions 0600. Neither value is printed or committed. The workspace opens at http://127.0.0.1:8000/.

**Do not run this setup before reviewing the PR and deciding to modify the local development database.** Opening, testing or merging this PR does not automatically change the Kali database or credentials. The Docker port remains bound to 127.0.0.1; this is not a public cloud deployment.

## Security review boundary

The browser now uses revocable server-side sessions with separate CSRF verification; sessions and API access keys are stored as hashes. Original development API bearer authentication remains available for automated tests. The API process still carries the migration administrator DATABASE_URL for legacy health/registry endpoints, and PostgreSQL GUC-based tenant context is not hardened against compromised SQL; production requires role segregation, identity-provider integration, stronger tenant enforcement, rate limiting and deployment review. The local access-key flow is NOT general customer sign-in.

## Execution exclusions

No autonomous LLM interpretation, running/ready transitions, executor, background jobs, outbound messaging, tool calls, self-service login or cloud deployment. Plan review is not an execution authorization. These are deliberate boundaries.
