# MetaAutomate Security Policy

MetaAutomate is a public, early-stage objective-planning project. **Do not expose the local development API, its access-key login, or the isolated contributor demo directly to the internet.**

## Supported for security fixes

| Component | Current status |
|---|---|
| Main-branch Objective Workspace | Development release; security fixes welcome |
| Contributor demo (port 18000) | Localhost-only testing, not production |
| Cloud/SSO work in draft pull requests | Under review, not a supported deployment |
| Automated agents and external execution | Not implemented |

## Report vulnerabilities privately

Use GitHub's repository Security tab and its **Report a vulnerability** flow if private vulnerability reporting is enabled. If the private reporting control is absent, contact the repository maintainer through an appropriate private channel before sharing details. Do not publish exploit steps, valid credentials, database extracts or customer records in issues, pull requests or discussions.

Please include the affected commit, a minimal sanitized reproduction, expected vs actual behavior, impact and a suggested mitigation. Never test against a system you do not own or lack permission to assess.

## Security model and known limitations

- Development accounts use high-entropy opaque keys and server-side revocable sessions. These are **not** production authentication.
- The local API has a privileged DATABASE_URL for legacy registry routes. It must not be used as a publicly accessible SaaS without architectural isolation.
- PostgreSQL tenant scoping uses transaction-local settings and RLS. Arbitrary SQL executed on a compromised application connection can manipulate tenant settings; this is not a hardened defense against SQL injection or malicious database sessions.
- The workflow only builds proposed task graphs. Human approval does not authorize execution. Draft capabilities have no active contracts or outbound capabilities.
- The isolated demo binds only to 127.0.0.1 and uses its own Compose project, PostgreSQL volume and random local credentials.
- Automated repository hygiene scans only the current tracked tree. It is **not a full history secret audit**, dependency security assessment or substitute for GitHub secret scanning and human review.

## Security development expectations

Threat-model new endpoints. Prefer least-privileged database roles. Preserve authorization checks and CSRF defenses. Add negative tests for cross-tenant reads/writes, token expiry/revocation, unsafe origins, replay/idempotency, leakage of secrets and accidental external execution.

Never merge a change that enables outbound operations, charges, messaging or real account access without explicit authorization, review, rollback and audit design.

## Operational responsibility

Developers must secure their own local machines, credentials and test datasets. Rotate any exposed tokens immediately. Do not claim that a green CI run means a hosted instance has been penetration-tested or formally certified.
