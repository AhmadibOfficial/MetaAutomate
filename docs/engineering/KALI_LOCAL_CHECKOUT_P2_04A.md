# Kali local checkout and P2-04a acceptance runbook

**Purpose:** reproduce the P2-04a source tests on the owner's Kali Linux machine **before merge**. GitHub-hosted CI is not evidence of local execution. Phase 01 remains **3/9 verified, NO-GO**. Do not deploy, migrate the existing Kali database, run workspace-init, enable cloud access or use real business data.

## A. Find the existing repository before cloning

```bash
find "$HOME" -maxdepth 5 -name .git -print 2>/dev/null
```

If MetaAutomate is already checked out, use its actual path and run `git remote -v` there. Do not change another checkout with uncommitted work. If no checkout exists, use GitHub CLI with authenticated access to the **private** repository:

```bash
cd "$HOME"
gh auth status
gh repo clone AhmadibOfficial/MetaAutomate MetaAutomate
cd MetaAutomate
git remote -v
git status --short
```

If `gh auth status` fails, complete `gh auth login` interactively first. Never paste credentials, PATs, private SSH keys, development bearer tokens, or `.env` into logs or chat. If `gh` is not installed, configure approved Git SSH/HTTPS auth and clone `https://github.com/AhmadibOfficial/MetaAutomate.git` instead.

## B. Verify the exact branch and isolate Python dependencies

Only proceed after reviewing any existing uncommitted changes. With a clean checkout:

```bash
cd "$HOME/MetaAutomate"
git switch main
git pull --ff-only origin main
gh pr checkout 32
git status --short
git rev-parse HEAD
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r apps/api/requirements.txt 'PyYAML>=6,<7'
```

Match the PR's **current** head SHA, not the old pre-review SHA. Python 3.12 is the GitHub CI reference environment; note your local Python version. Do not run `make workspace-init`: that can rotate development access keys. No PostgreSQL migrations or `docker compose up` are required for the targeted pure simulation.

## C. Acceptance checks — no database or network required at test runtime

```bash
cd "$HOME/MetaAutomate"
source .venv/bin/activate
export PYTHONPATH=apps/api
python -m pytest -q -p no:cacheprovider --import-mode=importlib \
  tests/test_phase02_delivery_rehearsal.py \
  tests/test_phase02_synthetic_import.py \
  tests/test_phase02_synthetic_inventory.py
```

These tests include invented cross-tenant contexts, idempotency and concurrency, retry budgets, receipt/snapshot consistency, and synthetic import security. `pip install` may download packages; testing itself does not require a provider or production service.

## D. Evidence required before approving merge

Provide the **non-sensitive** result of `git rev-parse HEAD`, `python --version`, `git status --short`, the pytest summary, and any error trace with passwords/tokens/identifiers redacted. Confirm the PR branch remains isolated from `main`. Local acceptance must cover the final reviewed commit.

**No-go remains** until Kali checks pass and the review is closed. Even after a source PR merge, no live worker, provider integration, customer data, cloud subscription, OneCall federation or Phase 01 release gate is enabled.
