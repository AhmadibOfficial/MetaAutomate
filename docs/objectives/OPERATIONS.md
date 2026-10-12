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

## Local rollout (opt-in privileged operation)

1. Work in the established repository ~/metaautomate-github and review migration 009.
2. Run make db-upgrade once. It verifies migrations 001-008, takes a backup into ~/metaautomate-db-backups, and transactionally installs only 009. It never replays previous migrations or removes Docker volumes.
3. A trusted administrator must provision PostgreSQL role metaautomate_runtime as LOGIN with a strong private password and configure APP_DATABASE_URL in the ignored .env. The API Compose service already exposes this environment variable.
4. The administrator provisions a development organization, user and ACTIVE membership, then stores a SHA-256 digest of a high-entropy mat_dev_ bearer token in api_access_tokens. The tenant context must be set for membership inserts, even by a privileged database user, because of the existing write trigger.
5. Restart the API to load the new environment; then run make smoke, make validate and make ci-local. Do not share raw bearer tokens or database passwords in Git, screenshots or logs.

Local credential issuance is deliberately not an unauthenticated API or insecure default. It must be securely provisioned before enabling the local objective-write API; GitHub's ephemeral end-to-end CI does not require local credentials. Opening this PR does not migrate or modify the user's main database.

## Execution exclusions

No autonomous LLM interpretation, running/ready transitions, executor, background jobs, outbound messaging, tool calls, self-service login or cloud deployment. Plan review is not an execution authorization. These are deliberate boundaries.
