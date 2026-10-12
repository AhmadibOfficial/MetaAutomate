# MetaAutomate Engineering Architecture

## Today's product

A single FastAPI service offers a read-only capability registry, non-persisting objective preview, authenticated persistence of a draft objective, generated task DAG, human review and audit events. An HTML/CSS/JavaScript workspace on the same origin presents those operations.

The core execution boundary is intentionally strict: **no draft capability is enabled, no task executor exists, and approving a plan never performs external actions**.

## Components

| Component | Location | Notes |
|---|---|---|
| Browser workspace | apps/web | Frontend UI; local browser sessions and CSRF token |
| API | apps/api/app/main.py | App composition, health/readiness, static files |
| Objective parser/planner | apps/api/app/objectives.py | Deterministic validated preview/graph |
| Objective operations | apps/api/app/objective_ops.py | Tenant-scoped write/read/review and audit |
| Local auth | apps/api/app/authn.py, workspace_auth.py | Restricted runtime role, opaque development key |
| Registry | apps/api/app/registry.py | Read-only DRAFT capability catalog |
| PostgreSQL schema | database/migrations/ | Organizations, memberships, objectives, tasks, review, audit and sessions |
| Registry source | docs/registry/capabilities.csv | 33 draft items; contracts and activation not supplied |
| Existing dev Compose | docker-compose.yml | User development project, port 8000 |
| Contributor demo | examples/oss-demo/compose.yaml | Dedicated project, volume, secrets, port 18000 |
| Cloud/SSO draft | PR #6 (not on main) | Not a deployed service |

## Request lifecycle

1. Local user enters an opaque development token once.
2. The server exchanges it for a revocable HttpOnly browser session and a CSRF token.
3. Browser submits a validated objective, success criteria, constraints and explicitly selected draft capability IDs.
4. The API authenticates within a PostgreSQL transaction with tenant context.
5. The planner creates a deterministic graph of suggested tasks/dependencies.
6. A single database transaction saves the objective, draft workflow, tasks, dependencies, review request, idempotency receipt and audit event.
7. OWNER/ADMIN may approve/reject the plan. This changes the review decision only, not the draft workflow's execution state.
8. Browser can reopen the stored plan and review decisions later.

## Security boundaries

Development bearer tokens and the legacy registry preview exist for local testing. Runtime role restrictions and tenant contexts provide useful checks, but the legacy API still carries privileged DATABASE_URL. PostgreSQL custom GUCs are not a complete defense against compromised SQL sessions. Do not equate development access controls with production multi-tenant security.

No public deployment is in scope for this open-source foundation. The contributor demo does not connect to any cloud infrastructure and binds to loopback only.

## Testing

GitHub Actions runs Python tests, the full PostgreSQL migration/registry suite, tenant authorization checks and Chromium browser tests. The separate Open Source Contributor Journey job starts a fresh isolated demo and verifies sign-in, persistent work graph, review and logout.

## Next architecture decisions

A stable capability/plugin contract, hardened runtime database operations, a reviewed external-action permission system and signed releases are future work. Reference docs/ROADMAP.md.
