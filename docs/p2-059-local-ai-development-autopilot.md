# P2-059 — MetaAutomate Local AI Development Autopilot

## Purpose

Introduce a **real, optional local language-model coding loop** for a developer-owned checkout. It is not an already-running daemon, production AI feature, cloud model, or claim of full autonomous software engineering.

The initial bounded workflow is:

`scoped task -> local Ollama request -> strict single-file JSON source proposal -> diff -> optional new Git branch + commit -> optional draft PR -> existing GitHub CI and independent review`

The coding model runs on the developer's own machine. It requires an installed, rights-cleared model and enough RAM/compute, but **no paid inference API**. The model itself is never invoked in GitHub Actions or Render.

## Setup on Kali / developer computer

Install Ollama using its official instructions, then obtain an appropriately licensed local coding model:

```bash
ollama serve
# In another terminal:
ollama pull qwen2.5-coder:7b

cd ~/MetaAutomate
git switch main
git pull --ff-only
git status --short
```

The repository must be **clean**, on `main`, with `origin` pointing exactly at `AhmadibOfficial/MetaAutomate`. If Ollama is not running on `127.0.0.1:11434`, the command fails closed. Do not paste secrets or customer information into task descriptions or files processed by the model.

### Preview (no repository writes)

```bash
python3 scripts/ai_dev_autopilot.py \
  --task "Improve the keyboard focus styling while retaining our four brand colors" \
  --file apps/site/assets/project-workspace-brand.css \
  --model qwen2.5-coder:7b
```

### Create an isolated local change

```bash
python3 scripts/ai_dev_autopilot.py \
  --task "Improve the keyboard focus styling while retaining our four brand colors" \
  --file apps/site/assets/project-workspace-brand.css \
  --model qwen2.5-coder:7b \
  --apply
```

This generates a *new* proposal (which may differ from the preview), creates an `ai-dev/...` branch and commits **only the requested source file**. Review its complete diff. It never merges.

### Automatically prepare a draft pull request

Authenticate the official GitHub CLI (`gh auth login`) before explicitly opting in:

```bash
python3 scripts/ai_dev_autopilot.py \
  --task "Improve the keyboard focus styling while retaining our four brand colors" \
  --file apps/site/assets/project-workspace-brand.css \
  --model qwen2.5-coder:7b \
  --apply --draft-pr
```

For this first milestone, **automatic draft PR publishing is permitted only for CSS files**. Python, JavaScript and HTML changes can be previewed or committed locally, but publishing them requires separate human review and verified isolated CI. The command publishes an allowed CSS branch and opens a **draft** PR. Running this command is an explicit developer authorization to send the proposed code to GitHub. It must *not* be used for unattended high-risk code, confidential source, or generated code which has not been assessed for CI execution risk.

## Scope and guardrails

- **Allowlisted existing files only:** `apps/site/assets/`, `apps/site/engage/`, `apps/api/app/`, extensions `.css`, `.html`, `.js`, `.py`. No new files, arbitrary filesystem paths or symlinks.
- **No executable-code auto-publication:** generated Python, JavaScript and HTML cannot use `--draft-pr` until isolated CI and independent security review are established.
- **Never touches:** `.github/`, migrations, deployments, secrets, registry gates, cloud resources, CI configuration or security policies. Model output cannot choose command arguments or paths.
- **Local inference:** fixed loopback Ollama endpoint, proxies disabled, JSON response with only `summary` and `content`, bounded input/output sizes, explicit file hash consistency.
- **Safe defaults:** preview only. A clean `main` checkout and authorized remote are required, and `--draft-pr` additionally requires `--apply`.
- **Execution:** the model cannot execute tools/commands; **Python output is parsed, not run**, by this script. However GitHub CI may execute imported generated Python/JS after PR publication, so treat it as untrusted and require isolated CI and human review before publishing such branches.
- **Release:** no auto-merge, auto-deploy, database migration, remote AI provider, account access, production operations, or bypass of existing NO-GO evidence. Draft PRs are proposed code, **not proof of functional tests or deployment readiness**.
- **Limitations:** one file/task at a time, no automated issue intake, test-fixing loop, dependency installation, autonomous scheduling, multi-file refactoring, or protected runtime. These need dedicated engineering work before expanding autonomy.

## Acceptance

Run:

```bash
python3 -m pytest -q tests/test_ai_dev_autopilot.py
python3 -m py_compile scripts/ai_dev_autopilot.py
python3 scripts/ai_dev_autopilot.py --help
```

Tests check path traversal/symlink rejection, strict model JSON, no-change rejection, Python syntax parsing, clean Git state, wrong origin rejection, local-only inference, stale-hash rejection and preview purity.

Model availability, end-to-end PR creation on a developer workstation, CI success, code quality and browser acceptance **must be verified separately**. Existing CI failures must not be waived.

## Future milestones

P2-060: bounded issue queue, code-generation provenance and reviewer attribution. P2-061: ephemeral, isolated no-secret evaluation of model-generated source and narrow automatic revision proposals. P2-062: multi-file tasks only after authenticated ownership, review, dependency gates and audit history. All releases remain separately approved.
