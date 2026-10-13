# MetaAutomate Operational Core — controlled release gates

Date: 2026-10-13. This is a **planning and review artifact only**. It authorizes no local database change, Render deployment, or customer invitation.

## R0: Verify the merge and deployment boundary

- PR #11 is merged, with commit `1a7de2f64953b4152a858d7c0640cb4569e834ef` currently at `main`.
- The PR CI passed on head `b76553c86369edfda1316c36fadf08293edc0d56`.
- The static website deploy specification in `render.yaml` uses `apps/site` and `autoDeployTrigger: 'off'`. The assessment interface is separate, under `apps/web` and FastAPI/PostgreSQL.
- GitHub reports that `main` is unprotected. Configure reviewed merges and required checks before the next engineering cycle.
- Verify the live Render service and deploy history separately; repository settings alone do not establish actual deployment state.

## R1: Back up and upgrade the local database (NOT EXECUTED)

Prerequisites: explicit owner approval for a specified Kali local PostgreSQL instance, verified Docker context, a known repository commit, verified available disk capacity, and a quiescent upgrade window.

1. Create a mode-0600 custom-format PostgreSQL dump in a private local backup directory.
2. Validate that the archive opens and successfully restore it to a disposable database; compare representative row counts. Confirm cleanup of the temporary restore database.
3. Apply only missing migrations 009, 010 and 011, in order. Never replay 001–008 on an existing database and do not use `docker compose down -v`.
4. Check forced row-level security, runtime read/write permissions, existing records, idempotency, per-tenant isolation, append-only audits, and browser sign-in/out.
5. Preserve the original backup and stop on any mismatch. Rehearse rollback into a separately provisioned database; avoid unreviewed in-place overwrites.

The existing `scripts/db_upgrade_local.sh` performs a backup, but **does not yet prove that the backup restores successfully**. Strengthening and testing this script is a prerequisite before owner-authorized execution.

## R2: Secure private staging (NOT DEPLOYED)

Obtain user confirmation of the intended Render workspace. Staging must have its own database, credentials, encryption keys, sanitized sample records, audit logs and monitoring. Use a pinned reviewed commit and manual deployment. Restrict browser access using an authenticated edge or private network; an obscure public URL does not constitute private staging. Preserve the existing public static website.

## R3: Production identity and isolation (EXTERNAL CUSTOMER ACCESS BLOCKED)

Replace local developer tokens and access-key login with reviewed production identity (OIDC with PKCE or equivalent), enforced MFA for privileged users, secure cookies, revocable sessions, strict organization isolation, restricted database roles, limited rate of abusive requests, audit trails, backup/restore tests, secure secrets, monitoring, and security review. Verify cross-organization denials at application and database levels.

## R4: Operational Core v2 — Amboy (DESIGN ONLY)

Business objective → model-assisted proposal → policy and risk check → explicit tenant-scoped authorization → idempotent, least-privilege tool execution → durable receipt → independent evidence check → auditable outcomes.

At first, run AI reasoning in proposal-only mode. Keep all capabilities disabled by default. A report hash is not evidence of revenue, productivity, or other real-world outcome. Record baseline, observation period, source and uncertainty for each business result.

## Stop conditions

Do not proceed on unclear database target, missing operator approval, unsuccessful restore rehearsal, failed tenant-isolation test, public staging without access control, unexpected credential exposure, or failed security checks.

**Current stop point:** PR #11 is merged and tested in GitHub, but the local database upgrade, private staging and customer rollout remain unverified or unexecuted.
