# MetaAutomate: Security and Confidentiality for AI-Assisted Engineering

**Status:** Security source proposal; not operational security certification. Production APIs and private data remain NO-GO until approved gates are independently verified. No deployment is authorized.

## Rules

1. **Secrets and credentials:** never expose `.env`, credentials, access tokens, SSH keys, customer data, or cloud settings to AI tooling. Keep them physically outside AI-visible checkouts. Ignore rules prevent untracked commits only; they do not stop tools reading local files or remove previously tracked secrets. Rotate keys immediately after leaks, check historical commits and incident logs.
2. **Prompt and log hygiene:** use task-specific files/functions and synthetic records. Redact PII, emails, client IDs, infrastructure addresses, bearer headers and internal paths before sharing prompts, stack traces or issue reports. Do not index entire proprietary repositories. Never paste real confidential data.
3. **Actual provider privacy terms:** determine model-training, retention, logging, region, subprocessors and data-processing promises from current enterprise contracts and account configuration. A local repository file cannot guarantee zero retention or zero training. Until verified, treat AI tools as unapproved for confidential client data.
4. **Tool confinement:** create a separate minimal source checkout/worktree, unprivileged OS account or container, no host home mount, no production environment variables or Render/GitHub deployment credentials, and deny outbound network unless specifically approved. Codex CLI can be launched read-only with `codex --sandbox read-only --ask-for-approval on-request`; settings may be ignored for untrusted projects. Claude Code project deny patterns must be verified using `/permissions` with the installed CLI. Neither is a proven host-level boundary by itself.
5. **Mandatory manual review:** AI-authored code is untrusted. Require a genuine human reviewer, tests and security assessment for all PRs. Review authorization/tenant boundaries, data paths, file diffs, migration implications, prompt injection, XSS/SQLi and logs. Restrict merge through GitHub admin branch protection and review requirements; this PR cannot enable those settings by itself.
6. **Supply chain:** do not install AI-suggested packages automatically. Validate canonical names/maintainers and release integrity, pins, lockfiles, transitive scripts, vulnerabilities, typosquatting and dependency confusion. Review new Actions and scripts, avoid remote shell pipes, and require separate authorization for network installs.
7. **Environment separation:** CI has read-only GitHub permissions and scans code, not production infrastructure. Do not mount secrets in AI workspaces, write to production, deploy backend changes, or bypass foundation F04-F09. Static website publication is a separate human-approved workflow.
8. **Incident response:** if an AI agent sees a real secret or PII, stop execution, revoke/rotate credentials, scope the exposure, notify authorized owners, and preserve sensitive evidence outside public repository logs/issues.

## Kali local setup (manual owner action)

After switching to the reviewed feature branch and confirming all files:

```bash
cd "$HOME/MetaAutomate"
git status --short --branch
git config core.hooksPath .githooks
chmod +x .githooks/pre-commit
python3 scripts/ai_security_preflight.py --staged
python3 -m pytest -q -p no:cacheprovider tests/test_ai_security_preflight.py
```

The hook must be installed per local clone. The committed `.githooks/pre-commit` does not activate itself, and GitHub API file writes do not run local hooks. Do not let an AI process configure Git hooks or alter GitHub admin rules without explicit review.

## CI checks and honest limits

- `scripts/ai_security_preflight.py --staged` checks staged Git index blobs. CI `--base FULL_SHA` checks files changed between that base commit and HEAD. Both redact findings to path, line number and rule name, without echoing values.
- The scanner blocks disallowed filenames, known token formats, key headers, and non-synthetic credential assignments; it is not Gitleaks/TruffleHog or comprehensive historic/third-party-binary/PII detection.
- GitHub Actions `ai-security.yml` requires changed-file scan, scanner tests and Python Bandit medium/high findings. Bandit does not cover JavaScript, SQL or all runtime threats; add dedicated JS/SQL SAST, SCA, policy and dynamic security tests before executing protected business operations.
- No `zero training`, `zero data retention`, confidential-information isolation, independent manual reviews, GitHub ruleset enforcement, CI success or live-production security may be claimed solely from this source PR.
- Hourly MetaAutomate development automation remains stopped. No new automation schedule, payment or deployment is created.

## Acceptance checklist

- Independent manual PR review and dependency provenance checks completed; author cannot self-approve.
- A deliberately staged dummy secret is blocked locally; no secret value appears in output. Re-run on exact Git commit via CI.
- CI tests run successfully; independently verify all checks and require them through actual branch protection.
- Real Claude Code and Codex negative read/write tests pass inside an OS-enforced isolated checkout.
- Confirm contractual privacy terms before any client/proprietary prompt data.
- No customer data, tenant action, cloud account or production deploy is accessible from the AI environment.
