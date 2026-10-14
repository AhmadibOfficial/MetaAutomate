# AMBOY M1 — Authenticated No-Model Gateway (source candidate)

**Status:** Source candidate, disabled by default. No OneCall adapter, cloud deployment, AI provider or customer access is authorized.

## Purpose and behavior

AMBOY M1 reuses MetaAutomate's authenticated organization/user principal. A new POST /v1/amboy/turn route is disabled unless AMBOY_M1_ENABLED=1 is explicitly set. An existing valid session is required. For this dry-run scope, OWNER, ADMIN, and OPERATOR may submit; VIEWER and unauthenticated users may not. In private OIDC mode, legacy bearer login remains disabled.

Only MetaAutomate product identity is supported. The request cannot supply organization/user/product/roles/scopes. OneCall surface hints and business-resource lookup hints are explicitly denied. No conversation history or other record is retrieved. All modes return one fixed non-executing response with status unsupported, a receipt reference, and execution_performed=false.

Migration 013 creates a tenant-and-user-isolated request metadata ledger and a database-backed quota table. The ledger saves a SHA-256 hash of canonical input, a conversation correlation UUID and a unique client request ID, but never the message text. Request receipts are append-only and forced-RLS protected. New requests are bounded to 10 per authenticated user per hour, serialized with a transaction-scoped PostgreSQL advisory lock. Identical retries return the original receipt free; reusing a UUID for different content returns HTTP 409. Each accepted unique request produces one append-only, content-minimized audit event. Over quota returns HTTP 429.

## Scope and known gaps

- There is no external AI inference, autonomous action, booking, billing, advertisement activity, data retrieval or OneCall integration.
- Role-derived dry-run permission is a narrow temporary policy; actual federated OAuth/product scopes and approved service-to-service identity are future work.
- Denied requests are not all persistently audited; denial telemetry and privacy-safe retention need another review.
- Per-user hourly quota is not a production anti-abuse or spend-limit mechanism. Private ingress/rate limits remain mandatory.
- A supplied conversation ID is only a correlation label, never an authorization token or conversation-history lookup.
- No real identity provider, MFA, cloud private perimeter, provider pricing or production recovery has been verified here.

## Database/release safeguards

The owner-approved Kali local database currently has migration 011. OIDC migration 012 and AMBOY migration 013 are source-only and are NOT approved to execute on Kali. The current guarded local database upgrade command only handles 009-011; do not run ad hoc migration loops against real data.

Only CI disposable PostgreSQL receives the new schema during this PR. The M1 integration test explicitly refuses to run outside GitHub Actions. Existing operational assessments, OIDC tests, Chromium browser CI, and disposable backup/restore rehearsal remain required.

Do not merge this PR as permission to deploy staging, enable the gateway, create customers, grant agent permissions or perform external work. Each change requires separate approval.

## Next stages

M1b: verify OneCall backend-to-gateway identity, product-scoped permissions, separate tenant mapping, revocation, denial logs and quotas.

M2: add a metered, grounded model gateway and adversarial safety tests only after private staging and owner authorization.
