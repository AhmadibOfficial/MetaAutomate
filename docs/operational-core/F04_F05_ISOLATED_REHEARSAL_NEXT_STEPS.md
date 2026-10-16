# F04 → F05: current enforcement blocker and sealed two-tenant rehearsal

**Status (16 October 2026): F04 BLOCKED; F05 BLOCKED; Foundation Phase 01 = 3/9 verified.**

The existing Render site is a **public static marketing website** and is not affected by this code. No new subscription, provider account, database instance, customer activation, secret, staging host or paid model connection is authorized.

## 1. F04 live investigation

The connected GitHub API, while the repository remains private, reported:

| Evidence | Current observed result |
| --- | --- |
| `GET /repos/AhmadibOfficial/MetaAutomate/branches/main` | `protected: false`; required checks `off` |
| `GET /repos/AhmadibOfficial/MetaAutomate/rulesets` | HTTP 403: “Upgrade to GitHub Pro or make this repository public to enable this feature” |
| `GET /repos/AhmadibOfficial/MetaAutomate/branches/main/protection` | HTTP 403: “Resource not accessible by integration” |
| `MetaAutomate CI` | Passing; **not enforced on `main`** |

**Do not make the private repository public to bypass F04.** GitHub documents that private-repository protected branches/rulesets require eligible GitHub Pro/Team/Enterprise access and administrator permissions. This connector does not expose a branch-protection write operation; no paid plan has been approved.

Official sources:
- https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule
- https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets

### Exact operator setup, *only after eligible plan and admin authorization*

1. Repository **Settings → Branches → Add branch protection rule** or **Settings → Rules → Rulesets**. Target `main` only.
2. Require pull requests, at least one distinct reviewer, dismissal of stale reviews, resolved conversations, current successful `Release Evidence Gate`, and apply restrictions to admins (no bypass).
3. Forbid force push and deletion; prefer protected production workflows with immutable branch sources. Retain the private repository and all credentials in a dedicated secret store.
4. Conduct a safe negative control using a dedicated unmerged PR with a deliberately failed required status check; separately witness that GitHub **blocks the merge**. Do not actually merge the negative-control PR.
5. Retain authorized reviewer and owner attestations, protected branch settings, failed-check screenshot/time/PR SHA in private evidence storage. The **official Foundation exit register** can only be updated after independently inspected live proof. Existing `scripts/inspect_f04_github_protection.py` can inspect legacy branch protection with an authorized read-only admin token, but passing that script is not independent negative evidence.

**F04 is not complete** until GitHub enforces the exact policy and its failing-check behavior is witnessed. Passing CI and this document never constitute F04.

## 2. F05: what the new code actually tests

`deploy/staging/compose.isolation-rehearsal.yaml` is **not** the already existing owner-approved `deploy/staging/compose.yaml`. It is a distinct opt-in local/CI test that requires `source-rehearsal-only`. It starts only two temporary synthetic containers:

- A PostgreSQL 16 instance on a Docker **internal-only bridge** without published database ports, seeded with two fictional tenants. Their login roles are non-superusers. A source-specified PostgreSQL RLS policy is ENABLED and FORCED, and uses `CURRENT_USER` to prevent one tenant from seeing/writing the other's test row. Roles cannot switch to each other.
- A **nonroot, read-only, capability-dropped, resource-limited** PostgreSQL-client worker on that same isolated bridge; it executes a fixed review script, not arbitrary jobs or LLM inference. It verifies its lack of default IPv4/IPv6 routes, queries each fictional tenant separately, checks role escalation and forbidden insertion, then rejects a connection attempt to a public address.

The job removes its **ephemeral volume and bridge** with `docker compose ... down -v`. All passwords in these fixtures are obvious *dummy CI-only values*. This is not a real customer database or a production secret.

To run locally with Docker and no cloud subscription:

```sh
python -m pip install 'PyYAML>=6,<7' 'pytest>=8,<10'
python -m pytest -q tests/test_f05_isolation_rehearsal.py
python scripts/verify_f05_isolation_rehearsal.py

docker compose -f deploy/staging/compose.isolation-rehearsal.yaml \
  --profile source-rehearsal-only up --abort-on-container-exit --exit-code-from worker
docker compose -f deploy/staging/compose.isolation-rehearsal.yaml \
  --profile source-rehearsal-only down -v --remove-orphans
```

The separate GitHub Actions workflow exercises the same checks and always attempts the destructive cleanup of **only the named ephemeral rehearsal stack**. Nothing touches live production or private staging.

### What F05 rehearsal does *not* prove

- A real approved private site exists, or its host/region/cost/security baseline has been reviewed.
- An API or production agent has a locked-down egress boundary (the existing staging API template still has an unrestricted `egress` network).
- Real staff SSO/MFA, authorization-code PKCE, tenant membership and revocation work across deployed services.
- External signed audit checkpoints, off-host encrypted backup, independent restore, RPO/RTO, operational alerts or release rollback have passed.
- A business model produces financial results, or real customer records and provider/model calls are permitted.

**The report deliberately keeps F04, F05, F06, F07, F08, and F09 blocked and the operating system NO-GO.** This new test is a more concrete safety demonstration than a static blueprint, but still cannot authorize live execution.

## 3. Sequence after this test

1. Owner obtains eligible GitHub branch-rule rights and an independently witnessed negative merge test (**F04**).
2. Owner separately approves a private-stage provider, region, access method, estimated monthly cost ceiling and real independent reviewer (**F05**).
3. Deploy only an isolated staging environment with its own dedicated identity provider configuration and test subjects; enforce real network/worker isolation, restore and operational approval (**F06–F08**).
4. Consider consented, measured external pilot only after operational acceptance (**F09**).

**No GitHub plan purchase, repository visibility change, production deployment, static website deployment, runtime release, subscriptions or source migrations in this milestone.**
