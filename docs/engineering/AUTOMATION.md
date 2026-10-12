# MetaAutomate Engineering Automation v1.0

Development-only automation for the established workspace at ~/metaautomate-github.

- make validate: existing Python test suite via Docker Compose (all API and repository tests).
- make smoke: verify locally running API /health, /ready, CORE catalog, and a non-executing Objective Plan Preview. Uses the ignored local .env key, does not print it, and requires the API to be running on 127.0.0.1:8000.
- make ci-local: run Python tests, then create a uniquely named disposable PostgreSQL test database, apply migrations 001-008, seed the 33 DRAFT capabilities, execute Registry tenant-RLS SQL tests, and drop the disposable database on exit. Does not migrate or seed the main metaautomate database.
- make pr: require a feature branch and clean working tree, run Python regression tests, ask explicit confirmation, then push the already committed branch and create a PR against main. It never stages, commits, merges, or deploys automatically.

Typical workflow:

1. git fetch origin && git switch -c feat/your-feature origin/main
2. Edit, review, and commit the intended files.
3. make smoke (if the local API is running and seeded).
4. make ci-local (requires working Docker Compose).
5. make pr (prompts before push).

Safety: This is local development convenience, not production CI/CD or production authentication. Do not run scripts/migrate.sh on an already initialized database. No production secrets or access approvals are managed by these targets. GitHub Actions remains the independent PR gate.
