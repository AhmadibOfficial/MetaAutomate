# Operational Core v1 — local database recovery gate

**Status:** reviewed code candidate, not permission to change a user's database.
Only perform this workflow from the existing Kali workstation after PR review,
an approved change window, and a fresh verified local recovery backup. Never run
this on Render or from a production deployment shell.

## Evidence

GitHub Actions rehearses this exact upgrade on an **ephemeral** PostgreSQL 16
database: migrates 001–008, inserts a disposable record, creates and restores a
custom-format archive in a temporary database, then applies 009–011 and verifies
data preservation, forced RLS, runtime table privileges, and immutable-evidence
triggers. The test runner is not the owner's workstation.

A successful rehearsal is **not** a production disaster-recovery guarantee:
the test database shares a PostgreSQL cluster with its temporary restore.
`pg_dump` excludes cluster-global users and roles. Plan separate role/config
recovery and protected off-host backup storage before production.

## Operator-owned preflight (read-only)

1. Verify your intended checked-out commit and that PR #15 has been reviewed,
   merged and installed locally. Confirm this checkout really points to the
   known local MetaAutomate development compose project. Do not fetch unknown
   scripts directly into a privileged shell.
2. Inspect `docker context show`, `docker compose ps`, disk space and
   the existing local database's health. Do not use remote Docker contexts,
   alternate Compose files or overrides when executing the upgrade.
3. Confirm maintenance window and stop or quiesce application writes. Record
   pre-migration table counts and current schema for later comparison.
4. Ensure `.env` is a local ignored private file. Never paste credentials
   or dump files into GitHub issues, logs or ChatGPT.

## Local upgrade — requires operator's own approval

From the reviewed checkout on the Kali workstation:

```bash
make db-upgrade
```

The operator must type **UPGRADE LOCAL** before any Docker/database command
runs. The upgrade script then:

- checks for baseline schema and missing 009/010/011 prerequisites;
- writes a mode-0600 PostgreSQL archive under
  `~/metaautomate-db-backups`;
- checks archive readability, restores it to a temporary local database and
  compares representative record counts before changes;
- drops the temporary test database, applies only missing 009–011 migrations;
- verifies forced assessment RLS, SELECT/INSERT but no UPDATE/DELETE for the
  runtime role, and immutable evidence triggers.

On any failure, stop, retain the backup and diagnose before another attempt.
A partial migration is not automatically reversed; migrations 009–011 have
transactional SQL boundaries. Do not run `make workspace-init` as a recovery
shortcut: it rotates local credentials.

## Post-upgrade acceptance (required)

- Confirm the original records still exist, including objectives, workflow
  data, capability registry, audit history and prior tenant membership.
- Confirm OWNER/ADMIN/OPERATOR assessment creation and VIEWER read-only access;
  deny cross-tenant reads and writes with distinct organization test accounts.
- Verify browser login/logout, CSRF rejection, token/session revocation,
  idempotency, immutable report retrieval and calculation receipts.
- Confirm all previously disabled global capabilities remain DRAFT/disabled,
  and no model/tool execution is enabled.
- Keep the private API bound to loopback only. Do not publish staging or
  invite customers. Production identity, isolation and observability remain
  separate release gates.

## Rollback preparation

Protect the backup, document its filename, verify disk space and maintain a
separate recovery destination. If a restore is required, stop application writes
and restore to a **new** database or volume first, compare important data, then
perform a reviewed cutover. Never automatically drop or overwrite the only
available working database. A full-disaster recovery exercise must include
roles, configuration, and backup retention outside the affected machine.
