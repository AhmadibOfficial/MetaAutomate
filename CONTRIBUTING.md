# Contributing to MetaAutomate

Thanks for helping create safe, useful automation infrastructure.

## Before contributing

Read README.md, docs/architecture/OVERVIEW.md, SECURITY.md and CODE_OF_CONDUCT.md. The implementation currently supports local objective planning and human review. **It does not execute actions or integrate active AI agents.**

Do not use real client data, real credentials, or production API keys when developing. Never attack, enumerate or scrape third-party systems without written authorization.

## Get started

You need Git, Python 3, Docker Engine and Docker Compose v2.

    git clone https://github.com/AhmadibOfficial/MetaAutomate.git
    cd MetaAutomate
    make demo-up
    make demo-check

Open http://127.0.0.1:18000/ in your browser. The private development login key is in examples/oss-demo/.workspace-access-key. Never post its content in GitHub, chat, screenshots or logs.

    make demo-down

This is a separate demo stack. It does not modify the original MetaAutomate developer database or delete volumes. The legacy make workspace-init / make migrate scripts are **not** the first-time contributor setup.

## Contribution workflow

1. Open an issue describing a bug, documentation gap or specific proposal, or choose an existing issue.
2. Fork or create a topic branch from main; work on one coherent, testable feature.
3. Include Python/SQL tests and user-facing documentation when behavior changes.
4. Run make demo-up followed by make demo-check and make demo-down, or rely on GitHub's isolated CI when your machine cannot run Docker.
5. Open a pull request with a clear explanation, tests and security implications. Keep secrets, proprietary data and huge generated artifacts out of the diff.
6. Respond to review requests. Merges require passing CI and maintainer approval.

Prefer substantial, complete vertical slices over multiple tiny PRs that cannot be tested independently. For security-sensitive features, explain the threat model and negative tests.

## Coding and design rules

- Python: type annotations where practical, clear boundaries, parameterized SQL, predictable error handling.
- PostgreSQL: no destructive migration, no reset of existing users or volumes, tenant scoping verified with SQL tests.
- Browser: accessible controls, readable content, no unsafe HTML templating, no keys in localStorage/sessionStorage.
- Tests: use isolated fake data, ensure no outbound calls and document expected behavior.
- Capabilities: draft registry items must not be activated or granted execution permission by unreviewed changes.
- Branding: preserve the approved MetaAutomate values and do not imply that all roadmap capabilities are already active.

If your change touches authentication, SQL tenancy, execution permissions, payment, network access or private cloud deployment, seek a dedicated security review.

## License and attribution

This repository includes GNU GPL v2. Submit contributions only if you have the right to distribute them under the repository's current licensing terms. Retain third-party copyright/license notices and credit upstream contributions appropriately.

There is currently no contributor licensing agreement (CLA) requiring you to transfer copyright or grant separate commercial relicensing rights. A future license strategy is a separate maintainer decision and must respect existing contributor rights.

## Review, conduct and disclosure

The maintainer is @AhmadibOfficial. Follow CODE_OF_CONDUCT.md. Report potential vulnerabilities **privately**, as described in SECURITY.md; do not put secrets or exploit details in public issues.
