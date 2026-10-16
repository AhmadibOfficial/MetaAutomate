# MetaAutomate Capability Registry API v1.0

> **New source-only engineering evidence overlay:** See
> [Unified Engineering Capability Registry](ENGINEERING_CAPABILITY_REGISTRY.md).
> This connects the 33 unchanged DRAFT catalog records to nine technology areas
> and ten platform systems. It records source maturity, dependencies, security
> requirements and traceable evidence, without changing this read-only API,
> seeding, database migrations or operational NO-GO gates.

Scope: **read-only global catalog**. Not a capability executor, tenant API, or production authentication system.

## Stored data

Migration 008 adds six tables:

| Table | Purpose |
| --- | --- |
| `capability_definitions` | Stable global IDs, domains, releases, priority, lifecycle status |
| `capability_versions` | Versioned contract placeholders; drafts cannot be current |
| `capability_dependencies` | Global prerequisite relationships |
| `capability_permissions` | Declared permission requirements |
| `organization_capabilities` | Per-tenant enablement and version pinning, RLS protected |
| `capability_executions` | Idempotent execution ledger, RLS protected; no execute API |

All **33** CSV entries are `DRAFT` and seeded disabled. Each has a **non-current**, null-contract `0.1.0` placeholder. `catalog_ready: false` means nothing can be executed. Adding dependencies or permission requirements requires explicit review and population of the two corresponding tables; the CSV does not supply those details.

## API contract

The API requires an `X-Registry-Key` header matching the environment variable `REGISTRY_READ_API_KEY`. If missing from the environment, requests fail closed with HTTP 503; wrong/missing request keys give HTTP 401. This shared development key is **not suitable for production user/organization authentication**.

- `GET /v1/capabilities` — paginated list (`limit` 1–100, `offset` >= 0), optional `domain` (`CORE`, `BIZ`, `PER`, `CRE`, `SPEC`), `release` (`R1`–`R4`), `status` (`DRAFT`–`RETIRED`). Returns `{items, total, limit, offset}`.
- `GET /v1/capabilities/CORE-001` — metadata plus `dependencies` and `required_permissions`; HTTP 404 for unknown IDs.
- `/health` and `/ready` are unchanged; they are connectivity checks, not a registry-schema migration assertion.

The list/detail API intentionally **does not expose** organization activations, execution records, full internal contracts, or write operations. Production needs per-user authorization, dedicated least-privilege DB role, validated execution contracts, approvals and policy enforcement before any external actions.

## Local integration on Kali Linux / VS Code

This overlay is for your existing branch `feat/vscode-workspace-v1` (or a new branch based on it). **Do not overwrite `README.md`, `LICENSE`, or `.gitignore`.**

1. Apply the files to a clean working tree using the installation commands in the accompanying setup guide.
2. Stop the older Compose project if using ports 8000, 5433 or 6379 (do **not** run `down -v`). The `metaautomate-github` project has its own database volume.
3. Generate a local key in `.env` (ignored by Git): `printf 'REGISTRY_READ_API_KEY=%s\n' "$(openssl rand -hex 32)" >> .env` (only if absent).
4. Start: `docker compose up -d --build`. Do not run `scripts/migrate.sh` on a database already containing those tables.
5. On a **fresh** database run once: `bash scripts/migrate.sh` (001 through 008, in order). For the retained test database which already has migrations 001–007, run **only** 008.
6. Seed from the API Python image, with the repo read-only mounted at `/workspace`:

   ```bash
   docker compose run --rm -T -v "$PWD:/workspace:ro" -w /workspace api python scripts/seed_registry.py
   ```

   Use `--database test_database_name` to target a separate database on the same Compose network if needed.

7. Verify: `curl -H "X-Registry-Key: $(sed -n 's/^REGISTRY_READ_API_KEY=//p' .env | tail -n 1)" 'http://localhost:8000/v1/capabilities?domain=CORE'`.
8. Test Python endpoints: `docker compose exec -T api python -m pytest -q -p no:cacheprovider tests/test_api.py tests/test_registry.py` (inside container `/app/tests`).
9. Test tenant registry RLS **only on a disposable populated test database**, with `docker exec -i "$PG_CONTAINER" psql -X -v ON_ERROR_STOP=1 -U metaautomate -d TEST_DATABASE < tests/sql/registry_integration.sql`; it rolls back its fixtures.

### Release restrictions

The schema and seed deliberately do not activate draft entries or grant permissions. The shared read key is for trusted local use only. Keep Docker ports bound to loopback and never commit `.env`. Your existing `docker-compose.yml` contains a development-only default password; change it before any non-local deployment. Existing system-wide RLS policies do not replace proper principal-to-tenant authorization.
