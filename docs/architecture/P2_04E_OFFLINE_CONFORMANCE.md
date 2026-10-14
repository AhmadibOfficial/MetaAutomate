# P2-04e — Offline cross-PR source conformance (no merge, no deployment)

**Status:** SOURCE-ONLY DRAFT. This milestone adds an *ephemeral local test harness* and a pinned source catalog. It **does not merge, cherry-pick, stack, activate, or change** any of the four isolated draft PRs #32–#35. It branches from `main` and only references the reviewed commit IDs as read-only Git objects.

Phase 01 Foundation remains **3/9 verified — NO-GO**, with independent review and enforceable GitHub branch/ruleset controls outstanding. GitHub workflows reporting success do not imply production authorization. Private repo, no paid subscription, no cloud deployment or customer records.

## Why consolidate before another feature?

P2-04a/b/c/d were each tested independently on isolated branches. Four green CI workflows plus local test runs **do not prove** that their Python modules and tests can coexist without import collisions, accidentally shadowing functions, or sharing state. This source-coexistence rehearsal tests the four modules in a shared *throwaway* filesystem, without modifying `main` or any PR.

## Contract

`contracts/engineering/p2_04e_offline_sources.json` explicitly pins:

| Draft PR | Scope | Pinned head SHA |
|---|---|---|
| #32 | In-memory synthetic delivery state machine | `2739ca4f9b4a6cd10ad556933b5f45ecab9a6c91` |
| #33 | Offline synthetic HMAC webhook proof | `bf6ec6d1a7538a3bb23d03961ef7379d89fc87e5` |
| #34 | Synthetic incident observability | `0b9556b84386e783da873f954e572338af3100c1` |
| #35 | Synthetic quota/backpressure/circuit breaker | `30a4608ffed00ce99926064315e657f0e8b581ee` |

The script reads their modules/tests with `git show <SHA>:<path>` from **locally available Git objects** (no fetch), plus the merged `main` commit's `apps/api/app/main.py`. It writes copies into a `TemporaryDirectory` and runs the four focused pytest files together, after validating the manifest's exact SHA/path and fail-closed release flags. It will reject missing local Git objects, mismatched paths, unauthorized new entries, changed lock hashes, unexpected API imports, or oversized files. The temporary directory is removed even after test failures.

This is a test *rehearsal*, not an OS sandbox: only inspect or run trusted PR code. The tests execute in a Python subprocess with your user's OS permissions. No real provider secrets or customer records should ever be added to the fixture code. The harness uses local filesystem and subprocess for the temporary test execution; it does **not** change the repository or run a service.

## Local Kali instructions

Use the existing MetaAutomate clone. The four PRs were already checked out earlier, so their commit objects should be present in the local Git object store. The exact pinned SHA needs to be present; a branch name alone is insufficient.

```bash
cd ~/MetaAutomate
git status --short
gh pr checkout 36
git rev-parse HEAD
source ~/.venvs/metaautomate-p204a/bin/activate

# Validate the four exact commit objects and source paths without pytest:
python scripts/verify_p2_04e_offline_stack.py --check-only

# Copy pinned sources into a throwaway directory and run focused tests jointly:
python scripts/verify_p2_04e_offline_stack.py
```

If an object is missing, fetch that private PR's branch **into the same local repository** with ordinary Git/GitHub authentication (for example `git fetch origin feat/p2-04a-local-delivery-rehearsal-20261014` for PR #32), then re-run `--check-only`. Do not loosen pins to arbitrary branch tip or clone the repository into a public service.

### CI and acceptance boundaries

- GitHub CI for P2-04e runs `tests/test_phase02_offline_stack_contract.py` to validate manifest shape, no-go flags, SHA/path constraints, reader behavior and lack of API wiring against `main`.
- GitHub CI **does not have** these four draft PR commits in its normal `main`-based checkout, so it cannot claim that it ran the cross-PR rehearsal unless the objects were explicitly supplied. The combined rehearsal is **local Kali evidence** only.
- Passing four-source pytest in a single temporary directory establishes **coexistence smoke-test evidence**. It does not verify functional coordination, a real delivery pipeline, production isolation, durable retry/replay state, real provider signatures, or any release gate.
- If any draft PR changes, the manifest pins and all compatibility tests must be reviewed and updated. Old green results do not apply to new SHAs.

## Deferred requirements — NOT WAIVED

Independent review, private-repo branch protection, secure private staging and all unfinished Phase 01 gates remain blockers for merging and production. No PR is authorized to merge or mark ready because of this rehearsal; all P2-04 draft PRs stay draft. No new subscriptions, cloud resources, customer/provider effects, Kali DB migrations, OneCall federation, Render deployment or production enablement.
