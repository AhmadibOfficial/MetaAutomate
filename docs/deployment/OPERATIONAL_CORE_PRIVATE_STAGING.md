# Operational Core v1: release safety and private staging

**Code release:** PR #11 merged to the private MetaAutomate \`main\` branch at \`1a7de2f64953b4152a858d7c0640cb4569e834ef\`.  
**Owner Kali database:** not upgraded remotely or otherwise accessed.  
**Public website:** unchanged; Render hosts only \`apps/site\`.  
**Private staging:** not created; requires additional access, identity configuration and security approval.

## Controlled local database upgrade

CI has proven migrations 001–011 and browser workflows on an **ephemeral** database, not the owner's development data. A local upgrade must happen with the operator's direct approval on the machine hosting the intended PostgreSQL database.

Before proceeding, review the local Git checkout, Docker context, available disk space and current database state. Confirm no concurrent writes and decide on a maintenance window. Example *inspection* commands (adjust checkout path if needed):

\`\`\`bash
cd ~/metaautomate-github
git status --short
git fetch origin main
git pull --ff-only origin main
git log -1 --oneline
docker context show
docker compose ps
\`\`\`

**Stop** if this is not the intended local database, the source checkout has unreviewed changes, or the Docker context is a production/remote host.

After the safety-patch PR is reviewed and merged, the explicit operator-approved action is:

\`\`\`bash
make db-upgrade
\`\`\`

That command uses the reviewed \`scripts/db_upgrade_local.sh\`. It checks schema prerequisites, refuses unexpected missing runtime roles, writes a restricted \`pg_dump -Fc\` backup to \`$HOME/metaautomate-db-backups\` (not inside the repository), confirms \`pg_restore --list\` can parse it, and **only then** applies missing migrations 009, 010, 011. Earlier schema migrations are not replayed, Docker volumes are not deleted, and development login credentials are not rotated. Failed migrations require investigation before retry; do not automatically restore.

After the migration, the local operator should confirm the assessment table:

\`\`\`bash
docker compose exec -T postgres psql -X -v ON_ERROR_STOP=1 \
 -U metaautomate -d metaautomate \
 -c "SELECT to_regclass('public.digital_assessments') AS table_name;"
\`\`\`

Then restart only the application process, if needed, and test the authenticated assessment path under the existing localhost workspace. The \`workspace-init\` command rotates existing developer access keys: do not rerun it solely to upgrade schema 011.

**Restore drill:** the ability to list a dump is not proof that data is restorable. Perform a full \`pg_restore\` and post-restore integrity check against a *disposable* database, never the live development database. Record recovery time and secure/encrypt the backup according to an approved retention policy.

## Private staging release gates — NO-GO until all requirements pass

| Gate | Required evidence |
| --- | --- |
| Network perimeter | Real private service or **network-level** access controls / trusted authenticated proxy. A hidden public URL is **not** private. |
| Identity | Real **OIDC** authentication, issuer/audience checks, MFA for administrators and allowlisted HTTPS callbacks. No dev access keys as internet login. |
| Authorization | Server-side tenant identity; OWNER/ADMIN/OPERATOR/VIEWER permissions; two-tenant negative tests and role-denial checks. |
| Database | Separate staging PostgreSQL and least-privilege runtime, forced RLS, encrypted backups, completed Restore drill. |
| Secrets | Managed secrets, no real customer data, credentials or tokens in repository, logs or browser artifacts. |
| HTTP | HTTPS, secure cookies, CSRF, trusted hosts and limited CORS. |
| Operations | Rate limits, cost controls, alerting, incident/rollback runbook and observed health checks. |
| Product safety | All unrelated capabilities remain DRAFT/disabled. No AI or external action is implicitly authorized by a report review. |

**No external customer access** before those controls have been independently checked and approved. Staging should use **synthetic** records.

The currently connected Render creation action provisions **public** web services, not a verified private network/identity-proxy arrangement. Do not deploy FastAPI using it simply to obtain a URL. PR #6 contains earlier OIDC and hosting experiments, but should not be merged or deployed without review for compatibility, commercial costs and security.

## Scope and rollback

Operational Core v1 verifies **self-assessment calculation integrity**, not actual financial improvements or externally executed work. It is not an autonomous AI platform, and does not activate the 33 draft registry capabilities.

Git rollback does not reverse a database schema change. Record schema state, backup path, migration result and tests. Restores must be planned and tested separately; never run destructive cleanup such as \`docker compose down -v\`.
