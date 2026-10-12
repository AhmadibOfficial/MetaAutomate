# Open Source MetaAutomate — Community Onboarding

## What this open-source release is

MetaAutomate is already a **public GitHub repository with the GNU GPL v2 license text**, not a source-closed proprietary product waiting for publication. This milestone makes it *usable for outside contributors* before attempting cloud scale.

The public product today is a deterministic planning and human-review workspace. It can save objectives, proposed task graphs, approvals and audit records. There is no executing capability, automatic external action, active AI agent or production SaaS on main.

## Run an isolated demo safely

Requirements: Git, Docker Engine, Docker Compose plugin v2, Python 3 and a free localhost port 18000.

    git clone https://github.com/AhmadibOfficial/MetaAutomate.git
    cd MetaAutomate
    make demo-up

Opening the first run creates examples/oss-demo/.env and examples/oss-demo/.workspace-access-key with mode 0600, generates random development secrets, starts a dedicated PostgreSQL volume, runs fresh migrations 001–010, seeds 33 disabled draft capabilities, provisions a sample demo owner and starts the workspace.

Open http://127.0.0.1:18000/ and enter the key read privately from examples/oss-demo/.workspace-access-key. The demo runs on localhost and is **never an internet service**.

    make demo-check
    make demo-down

Stop retains your demo objectives and volume. No command in this quickstart deletes volumes, edits ~/metaautomate-github/.env or contacts a cloud provider. Do **not** use docker compose down -v or manually reset existing databases. The primary developer stack remains on port 8000, with a different Compose project and database.

For isolation, the scripts deliberately refuse to initialize an existing database that looks partially migrated. They refuse to silently reactivate expired or revoked demo access keys. If a token has expired, request guidance for safe rotation of the separate contributor demo credentials. Do not copy production data into the demo.

## Project status and trust boundaries

- Development access key: not a production identity system.
- PostgreSQL tenant contexts: intended for cooperative application access, not proof of protection against compromised arbitrary SQL.
- Human review: updates approval records only.
- All 33 registry capabilities: remain DRAFT and disabled.
- No monetary, email, social-media or other external execution is enabled.

See architecture overview and SECURITY.md. Any change that weakens these boundaries requires explicit maintainer security review and tests.

## How to contribute

Find an issue, reproduce a problem or propose a focused feature. Changes should include tests and document their behavior. New contributors can start with UI accessibility, fixtures, docs, deterministic planner scoring, test reliability and reproducibility. Do not submit real API credentials, organization data or private customer records. Do not test third-party systems without authorization.

GitHub Actions tests Python, PostgreSQL migrations, tenant isolation, and the full Chromium browser journey. The OSS journey additionally validates a new-clone contributor demo and ensures secrets stay untracked.

## Governance and licensing

Current maintainer: GitHub @AhmadibOfficial. Changes land through reviewed pull requests and CI; accepting a contribution does not promise future employment, equity or commercial licensing rights.

The existing LICENSE contains GNU GPL v2. We are not changing it through this onboarding milestone. If the project later seeks a different license, a clear decision and rights from relevant copyright holders will be necessary. Contributors should not submit code they cannot license under the existing project terms.

Brand usage and the original logo require explicit clarification separately from permissions granted for source code. Any future branding policy cannot retroactively revoke rights already granted under a valid applicable license.

## Before a first tagged release

- Verify the existing GPLv2 license choice and copyright ownership/provenance.
- Review third-party dependencies and brand asset rights.
- Enable GitHub private vulnerability reporting and automated dependency/secret scanning where available.
- Audit **Git history** for leaked secrets and rotate anything exposed; the automated repository check only examines the currently tracked tree.
- Secure a reviewer process, issue labels, release notes, changelog and a signed or verified release artifact where feasible.
- Keep private-cloud and autonomous-execution development behind separate reviews until production safety conditions are met.
