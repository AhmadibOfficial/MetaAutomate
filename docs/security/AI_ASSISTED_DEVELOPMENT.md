# SEC-DEV-001 — Confidentiality in AI-Assisted Engineering

Status: repository-only security proposal, 2026-11-03. NOT merged, not production-deployed, and not yet an enforced organizational policy. Foundation operational release remains NO-GO.

## What must stay outside model context

Restricted: credentials, API keys, environment files, SSH keys, client identities, patient/financial records, proprietary business algorithms, customer exports, internal IP addresses and incident logs. Do not mount these into the AI workspace or paste them into chat.
Internal source files: use only those necessary for the task, after classifying them and checking the AI provider agreement. Approved synthetic test data is preferred. Mask identifiers, URLs and stack traces before sharing.

## External provider and retention review

Verify the exact enterprise provider agreement before submitting internal source: DPA, training settings, data retention, subprocessors, data geography, deletion and audit. Zero data retention and no model training are NOT universal defaults. If no suitable contract exists, keep non-public and regulated data offline.

## Local tools and permissions

- Git ignore blocks future accidental commits of common secret paths but cannot block AI reads or remove secrets from Git history.
- .claude/settings.json requests human approval for shell use, denies common secret paths and enables Claude sandbox. Confirm active Claude permissions and enforce centrally when possible; shell subprocesses or other IDE tools may circumvent a project-level setting.
- Codex should run in a disposable container/worktree with only reviewed source mounted and zero production secrets. Suggested CLI: codex -C /path/to/isolated-worktree --sandbox workspace-write --ask-for-approval on-request. Codex can still read host files outside its write root unless the host/container filesystem restricts them. Never use danger-full-access for confidential code.
- Limit network access and environment variables, never mount Docker socket, SSH agent, cloud configuration or parent home directory into the AI workspace.

## Git hooks and CI

Local setup is opt-in and needs validated packages: install pre-commit and the official Gitleaks CLI from approved sources. Then run python3 -m pre_commit install in the isolated worktree.
Pre-commit checks: staged sensitive-path guard plus Gitleaks staged scan with redaction. A local hook can be bypassed, so CI performs independent scans.
CI workflow security-ai-assisted.yml runs on PRs and main pushes, checks committed secret paths, runs pinned Gitleaks v3.0.0 (commit SHA pinned), Python Bandit 1.9.4 on changed Python, and conservative JavaScript injection checks on changed application files.
Secret-scan findings require local inspection, invalidation and rotation of exposed credentials; removing a secret from HEAD does not erase Git history.
Dependencies must be independently vetted (package name/publisher, pinned version, advisories, licenses, transitive tree, lockfile and integrity). Static scanners cannot guarantee supply-chain safety.

## Mandatory manual review and branch protection

All AI-authored code is untrusted. An independent human reviewer must examine security boundaries, business logic, SQL injection, XSS, prompt injection, data provenance, third-party code and permissions before any merge.
CODEOWNERS is an ownership hint, not an enforcement mechanism. Verified 2026-11-03: GitHub reported main branch protection=false. Manual review is currently NOT ENFORCED by GitHub, regardless of documentation.
Repository admin must enable GitHub rules: require PRs, one independent approving reviewer, require code-owner review, dismiss stale approvals on new commits, resolve comments, block force push/deletion/direct push, require the new security checks and existing CI, and remove bypass privileges. Verify enforcement through a real negative test.

## Deployment isolation

The current Render deployment remains a website-only static site on main with manual deployment; keep API servers, databases, cloud production write credentials, customer messaging and AI execution disconnected from assistant sandboxes. No agent can authorize release, change CI, activate real financial or medical workflows, or restart paused automations.
F04–F09, OIDC, MFA, tenant isolation, recovery, regulatory and independent review gates remain NO-GO until independently accepted. This security branch changes no website files and needs no Render deployment.

## Acceptance

Review this PR, validate the security tests, ensure Gitleaks and changed-code Bandit run successfully on the exact head, inspect any scanner alerts privately, activate and independently verify branch rules, and only then consider a separately authorized merge.

Documentation references: https://code.claude.com/docs/en/settings ; https://learn.chatgpt.com/docs/agent-approvals-security ; https://github.com/gitleaks/gitleaks-action ; https://pypi.org/project/bandit/1.9.4/

Dependency change control: docs/security/approved-api-python-packages.json records current direct API dependency identities, including the verified httpx2 package. scripts/security/dependency_review.py blocks unreviewed additions, direct URLs, alternate indexes, VCS links, and renames. This is NOT a version lock and NOT a transitive vulnerability audit; independent artifact integrity and advisory checks are still required before any new installation.
