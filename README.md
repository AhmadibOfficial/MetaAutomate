# MetaAutomate

**Turn Your Vision Into Reality**

**Intelligence · Creation · Automation**

MetaAutomate is an open-source, objective-driven automation project working toward intelligent systems that help people and organizations turn goals into verified outcomes. Its values are **Integrity, Excellence, Innovation, Impact, and Always HALAL**.

Our mission is to build intelligent systems that automate work, create solutions and empower individuals, organizations and societies to achieve more. Our long-term vision is to become a trusted, impact-driven AI automation platform creating opportunities, innovation and positive change.

**Current release: a local Objective Workspace for planning and human review, not an autonomous AI agent or production SaaS.** This project is under active development, and the roadmap intentionally goes beyond what the current code does.

## Current implementation

| Capability | Status |
|---|---|
| Create structured objectives, success criteria and constraints | Implemented (local) |
| Choose capability definitions from the draft catalog | Implemented (33 draft entries) |
| Produce a deterministic proposed dependency graph | Implemented |
| Persist an objective, draft workflow, tasks and dependencies | Implemented |
| Tenant-scoped objective listing and retrieval | Implemented using development authentication |
| Human approve/reject decisions and audit records | Implemented; planning only |
| Browser dashboard and dependency graph | Implemented |
| Reproducible Docker contributor demo | Provided by Open Source Foundation PR |
| Autonomous AI planning and discovery | **Not implemented** |
| Executable AI agents and external tool actions | **Not implemented** |
| Public cloud service, hosted user accounts, production sign-in | **Not implemented on main** |
| Production-grade tenant isolation, identity, and public deployment | **Not complete** |

Approved plans remain in DRAFT state. The platform does **not** automatically execute tasks, spend money, contact customers, or call external services.

## Try MetaAutomate locally

Requirements: Docker Engine with Docker Compose v2, Python 3 and Git. The demo uses port 18000 on localhost only.

    git clone https://github.com/AhmadibOfficial/MetaAutomate.git
    cd MetaAutomate
    make demo-up

Open **http://127.0.0.1:18000/** and use the access key in the private file examples/oss-demo/.workspace-access-key. Do not post the key in public issues or screenshots. The key is created on your computer, is ignored by Git, and expires after seven days.

To validate the demo and shut it down without deleting its data:

    make demo-check
    make demo-down

The demo has a separate Compose project, separate PostgreSQL volume and a different port from the original Kali developer setup. It does not modify the root .env file, call the legacy workspace initializer, or delete Docker volumes. Do not use it on a public server or expose port 18000 beyond localhost.

More: [Open-source onboarding](docs/OPEN_SOURCE.md).

## Architecture

| Path | Purpose |
|---|---|
| apps/api | Python/FastAPI Objective Workspace API |
| apps/web | Responsive HTML, CSS and JavaScript workspace |
| database/migrations | PostgreSQL schema and row-level security policies |
| docs/registry | The 33 draft capability definitions and metadata |
| scripts | Development automation, seeders, tests and smoke checks |
| examples/oss-demo | Isolated public contributor environment |
| tests | Python and SQL contract/security checks |
| workers | Placeholder for future authorized processing; not live |

See [architecture and trust boundaries](docs/architecture/OVERVIEW.md).

## Contribute

Issues, documentation improvements, test cases, UX improvements, code-quality fixes, deterministic planning improvements and security hardening are welcome. Start with [CONTRIBUTING.md](CONTRIBUTING.md). Follow the [Code of Conduct](CODE_OF_CONDUCT.md) and [security disclosure process](SECURITY.md).

Avoid building an external-action executor without an explicit security and authorization design. Do not post credentials, real customer records, private keys, or live vulnerability details.

## Roadmap and mission

MetaAutomate is being developed across personal, creator, business and specialist use cases. Long-term strategic sectors include agriculture, healthcare, food security, Islamic knowledge systems, education and cybersecurity. These are focus areas, **not claims of active integrations**.

The engineering sequence is: open-source planning core → contributor ecosystem → identity/tenant security → controlled private pilot → authorized, verifiable capability execution → responsible scaling.

See [ROADMAP](docs/ROADMAP.md). The separate private-cloud/identity/official-brand integration remains in **draft PR #6**, outside this current stable branch until reviewed.

## License and brand

This repository **currently contains the GNU General Public License, Version 2**; see [LICENSE](LICENSE). Existing code has not been relicensed by this onboarding work. The maintainers will verify provenance and any third-party asset notices before a tagged community release, and should decide explicitly whether GPLv2 remains the intended long-term license.

The MetaAutomate name and logo identify the original project. Open-source code permissions should not be confused with permission to impersonate the project or falsely claim official endorsement; any separate trademark or artwork policy must be consistent with applicable licenses and reviewed before publication.

Open source does not mean the platform is production-safe. The current local auth and PostgreSQL tenant-context design are for development and controlled testing.

---

**Solutions · Convenience · Experiences** — MetaAutomate
