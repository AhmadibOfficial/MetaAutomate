# MetaAutomate Automated Validation & Release Gate

## Purpose

Routine validation runs automatically in GitHub Actions. Local developers can run a single **read-only** readiness command. A successful test report is *evidence*, not permission to deploy, change credentials, or expose customers.

## Local Kali one-command gate

From the approved, up-to-date checkout, with the existing PostgreSQL and API already running:

    make verify-local

It checks the Docker endpoint and existing GitHub workspace volume, PostgreSQL migration 011 and assessment table security, API health and readiness, anonymous access denial, and stable business-record counts. It does **not** start/rebuild containers, run migrations, create an organization, rotate keys, perform test writes or connect to Render.

A private JSON result is written to the ignored path:

    .buildlog/validation/local-gate.json

The result intentionally contains no passwords, access keys, SQL rows or connection strings. Failures have a nonzero process exit code. If the API is stopped, the gate fails rather than silently starting it. Browser-based full functional testing is reserved for an isolated CI database.

## Automated CI release evidence

On pull requests into main and pushes to main, the existing MetaAutomate CI workflow executes:

1. Python unit tests, SQL migrations and capability registry integration.
2. Objective Operations authentication, tenant isolation, audit and revocation.
3. Assessment creation, scoring, idempotency, consent, cross-tenant denial, report evidence and restricted runtime grants.
4. Real Chromium browser login, objective review, assessment report and download, persistence, logout, desktop/mobile.
5. PostgreSQL recovery rehearsal against a disposable database and Docker volume.

The new **Release Evidence Gate** waits for both the functional job and disposable recovery job, runs even when a prerequisite fails, and fails closed unless both jobs succeed and render.yaml still describes one static website with auto-deploy off and no API or database services.

Its build summary and JSON artifact (release-evidence-gate) explain which gate blocked the release. CI test accounts and credentials belong only to the disposable CI runner; they are not imported into the local or production database.

## Administrative release lock still required

A passing Actions job **does not independently block a GitHub merge** on a repository without an enabled branch protection/ruleset. A repository administrator must configure protection for the private main branch, require the status check **Release Evidence Gate**, require the branch to be up to date, and disallow bypasses according to the owner's policy. Do not set or claim this automatically without administrative authority.

The Render dashboard's Auto-Deploy and PR Previews settings must remain Off; render.yaml validation cannot read live Render settings. Deployment, applying migrations, rotating credentials and enabling outside customer access each remain separate explicit owner-approval actions. There is no deploy job in this release gate.

## Interpretation of results

- **CI gate PASS** means the repository's automated acceptance and disposable recovery jobs passed and the reviewed blueprint stayed static-only. It is not a completed production acceptance test or a security audit.
- **Local gate PASS** means the owner's currently running local API and existing database passed a read-only readiness snapshot. It does not create a new assessment, validate every user journey, or enable any capability execution.
- **FAIL** means stop the release, follow the named failure in Actions or the private local JSON report, fix through a reviewed pull request, and rerun the gate. Do not repeatedly run migrations or reset workspaces to force a green status.

Both gates preserve the existing safeguards: local-only API access, immutable assessment evidence, tenant RLS, explicit consent, and execution disabled by default.
