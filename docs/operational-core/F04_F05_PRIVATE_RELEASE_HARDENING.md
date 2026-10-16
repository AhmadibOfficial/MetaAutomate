# F04 → F05: Private Release Protection and Subscription-Free Staging Design

**Decision:** operational NO-GO. Source-only hardening does not change Foundation 3/9, Phase 02/03 operational NO-GO, or permit paid subscriptions, real customer data, social publishing or agent execution.

## 1. Live GitHub F04 findings (16 October 2026)

The connected GitHub repository API returned:

- `GET /repos/AhmadibOfficial/MetaAutomate/branches/main`: `protected: false`; `required_status_checks.enforcement_level: off`; `contexts: []`.
- `GET /repos/AhmadibOfficial/MetaAutomate/rulesets`: **HTTP 403** — “Upgrade to GitHub Pro or make this repository public to enable this feature”.
- `GET /repos/AhmadibOfficial/MetaAutomate/branches/main/protection`: **HTTP 403** — “Resource not accessible by integration”.
- `MetaAutomate CI` already contains the source-only `Release Evidence Gate` job requiring core test and disposable recovery. **A passing check does not enforce a branch rule.**

**Do not make the private business repository public.** A GitHub Pro or other eligible plan *may* be required to enforce private-branch protection; **no upgrade/subscription is authorized by this task**.

As of this audit, PR #83 (P2-03u), PR #84 (P2-03v) and PR #85 (P2-03w) remain **draft and unmerged**, with bases `main → #83 → #84 → #85`. Do not collapse or merge their branches until explicit owner action, independently inspected checks, and code approval. GitHub API connectivity does not grant the connector repository administration access.

## 2. Exact administrative F04 procedure — after plan and account eligibility

1. Open the private repository's **Settings → Branches → Add branch protection rule** (or Settings → Rules → Rulesets), target **`main`**.
2. Require a pull request and **at least one independent approving reviewer**; dismiss stale approvals when new commits are pushed.
3. Require passing check **`Release Evidence Gate`** from the existing `MetaAutomate CI` workflow. Require branches to be up to date with `main`. Check the required status context is unambiguous. Also require conversation resolution.
4. Apply restrictions to **repository administrators** and forbid bypass by the owner/automation unless a separately reviewed emergency exception is documented. Disable force pushes and branch deletion. Avoid direct pushes to `main`.
5. Verify live rule via GitHub UI and admin-authorized read-only API. Example, from your own protected terminal (no tokens pasted into chat):

   ```sh
   export F04_GITHUB_READ_TOKEN='YOUR_READ_ONLY_TOKEN_FROM_A_SECURE_STORE'
   python3 scripts/inspect_f04_github_protection.py --live \
     --report artifacts/validation/f04-live-inspection.json
   unset F04_GITHUB_READ_TOKEN
   ```

   The script **never changes GitHub**; it checks active branch-rule settings only. A result `CONFIGURATION_CONFIRMED_INDEPENDENT_PROOF_PENDING` is *not* F04 VERIFIED.

6. Safely demonstrate the **negative security property** in a nonproduction review PR: a deliberately failed required check is shown to prevent merge on `main`. Do not actually merge that PR. An authorized independent observer records the rule URL/status, time, PR SHA, protected-branch block and the distinct owner/reviewer evidence **without secrets**.
7. The existing Foundation evidence register may only be changed after independent verification and two distinct signoffs in accordance with `docs/operational-core/FOUNDATION_EXIT_RUNBOOK.md`. GitHub-integrated code/CI alone cannot attest this. F04 currently remains BLOCKED.

Github documentation: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches and https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets.

## 3. F05 no-subscription design — what is and is not accomplished

`deploy/staging/subscription_free_design.v1.json` is a machine-readable **NON_DEPLOYABLE** blueprint with an enforced static test:

| Stage | Activity | Real customer records | Subscription | Operational F05 evidence |
| --- | --- | --- | --- | --- |
| S0 | Existing source security and release-contract checks | Never | No | No |
| S1 | Disposable CI runner with synthetic Postgres and browsers | Never | No additional subscription | No |
| S2 | Owner-reviewed private-hosting, region, identity and cost plan | None (not provisioned) | Not authorized | No |

The existing `deploy/staging/compose.yaml` is **opt-in** using `owner-approved-staging` profile, separated volume, no published database port, loopback API bind and OIDC-required settings. It is a **source template, not an activated private environment**. The blueprint checker refuses a purported live environment, payments, external AI/model calls, real customers, public ingress, live migrations and missing release gates. It also verifies source safety invariants on the existing compose file, without launching Docker.

**Zero additional subscription expense is a design constraint, not evidence that private hosting, enterprise MFA, backups, network protection or independent review are free or provisioned.** Do not label an unprotected home computer or a public tunnel “private staging”. Do not use a personal-use-only free networking plan for a commercial business unless its license explicitly permits it.

## 4. Test and evidence commands

```sh
python -m pytest -q tests/test_f04_github_protection_audit.py
python -m pytest -q tests/test_f05_subscription_free_staging_design.py
python scripts/inspect_f04_github_protection.py
python scripts/verify_f05_subscription_free_design.py
python scripts/verify_foundation_readiness.py
```

New source-only GitHub Actions: `.github/workflows/f04-f05-source-release-hold.yml`; two negative-security CI jobs with artifact reports. CI is non-deploying and uses no write administrative token.

## 5. Actual next release dependencies

**F04:** Enforced rule + witnessed failed-check merge rejection + independently recorded evidence. **F05:** Owner-approved real private staging provider/host, region, monthly cost ceiling, isolated runtime, separate DB, secrets, private authenticated ingress. **F06:** Real OIDC and MFA. **F07:** Encrypted independently restored backups. **F08:** Security and operational acceptance. **F09:** Consented pilot with baseline and useful measured outcome.

**No automatic approval, no customer activation, no deployment, no billing, no GitHub upgrade, no Render change, no real AI calls.**
