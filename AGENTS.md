# MetaAutomate — AI-Assisted Development Rules

Apply to Claude Code, Codex, all coding assistants, and human reviewers. The AI agent does not have release authority.

1. Work only inside a new reviewed feature branch or isolated worktree, scoped to the requested paths. Never delete, reset, overwrite, or modify unrelated projects and persistent data.
2. Do not give AI tools access to real customer/client records, personal information, clinical information, production credentials, .env files, private keys, cloud secrets, internal network addresses, or proprietary algorithms. Use explicitly synthetic test data.
3. Minimize context: only pass required functions or files. Manually sanitize logs, stack traces, screenshots, hostnames, emails, IPs, and configuration output before sharing them with external AI tools or public PR comments.
4. Verify provider DPA, retention, model-training opt-out, subprocessors, regional storage, and organizational controls before submitting non-public code. Do not assume a zero-retention or zero-training guarantee.
5. Use an OS/container sandbox with no secret mounts, no host home directory and network disabled by default. Claude permission rules and Codex workspace-write policies are defense in depth, not substitutes for host file isolation.
6. Never grant AI production credentials, deployment privileges, tenant database access, live customer communication, cloud mutation rights, paid purchases, or permission to override checks.
7. Treat AI output as untrusted. Check dependency names, exact publishers, provenance, advisories, licenses, and lockfiles before adding a package. Review generated SQL, HTML, auth, file paths, and external effects.
8. Before requesting a PR review run the staged secret scan, changed-source SAST and relevant unit/browser tests. No bypass of failed checks or disabling them for convenience.
9. Require manual review of all AI-authored diffs by a qualified human who is not the author before merge; enforce via GitHub branch protection, not merely CODEOWNERS. Main branch protection was observed as disabled on 2026-11-03.
10. MetaAutomate operational Foundation release remains NO-GO. The public static website is a separate scope and does not authorize backend/agent execution. Leave hourly development automation paused.

Detailed procedure: docs/security/AI_ASSISTED_DEVELOPMENT.md
