# MetaAutomate Private Cloud + OIDC — Deployment Runbook

**Status:** Infrastructure and identity integration code, NOT a live cloud deployment. User approval is required before purchasing infrastructure or accessing any external account. This package does not publish the MetaAutomate application on the open internet.

## Architecture

- Single Linux cloud VM, provider-agnostic (AWS EC2, Azure VM, DigitalOcean Droplet, or other Linux VM).
- Private HTTPS access through **Tailscale Serve** at a tailnet domain, restricted by tailnet access policy. **Do NOT enable Tailscale Funnel**, public reverse proxies, or cloud ingress rules to the API.
- Docker Compose in deploy/private/compose.yaml. API binds only 127.0.0.1:8080 on the VM; PostgreSQL publishes **no host ports**. The API runs non-root, without write access to its filesystem or Linux capabilities.
- A **separate, on-demand administrator container** initializes the PostgreSQL schema and seeds the disabled draft capabilities. The API container only receives APP_DATABASE_URL for the restricted metaautomate_runtime role. It has no DATABASE_URL.
- OpenID Connect (OIDC) with authorization-code flow, PKCE/nonce/state handling provided by Authlib and a trusted provider. Exact issuer+opaque-subject mappings to ACTIVE organization memberships are approved by a database administrator in advance; no automatic user or tenant creation on sign-in.
- SameSite Strict, Secure, HttpOnly workspace session cookies; separate CSRF token, strict Origin checks, database-side session expiry/revocation. The temporary OIDC transaction/state cookie uses Secure and SameSite Lax to permit the IdP return.

## Identity provider prerequisites

Configure an OIDC application with your chosen corporate IdP, for example Microsoft Entra ID or Keycloak. Use a confidential authorization-code client with an HTTPS redirect URI:

    https://<private-hostname>.<your-tailnet>.ts.net/v1/workspace/oidc/callback

The discovery URL must be at the exact OIDC issuer + /.well-known/openid-configuration. Copy issuer, client ID and client secret into the VM's private deploy/private/.env file (never into GitHub). Configure WORKSPACE_ORIGIN as the same base HTTPS tailnet origin. Generate OIDC_STATE_SECRET with at least 48 unpredictable characters.

Provision the founder's verified OIDC issuer+subject and organization using the administrator-only scripts/provision_oidc_identity.py. The OIDC subject is an opaque user identifier from the IdP (not an email guessed from the login page). Different organizations require separate explicit provisioning. The live IdP handshake and production security review remain required acceptance tests.

## Guarded single-command initial launch

After an approved cloud VM, Tailscale private tailnet, trusted OIDC application, and private `deploy/private/.env` have been configured, run the integrated launcher **on the VM**:

    bash deploy/private/scripts/launch.sh

The script validates the chosen HTTPS tailnet origin, callback, credential separation, OIDC settings, Docker Compose configuration and active Tailscale connection. It requires explicit `PRIVATE-LAUNCH` confirmation, migrates a **new empty database only**, seeds disabled draft capabilities, provisions the verified owner, starts the restricted API, and configures Tailscale **Serve** (never Funnel). It refuses unsafe/placeholder settings and cannot provision a cloud VM or choose an OIDC provider for you.

Supply `META_OWNER_SUBJECT`, `META_OWNER_EMAIL`, and `META_ORG_SLUG` in the ignored env file after verifying the subject with the IdP administrator. Never paste private credentials or IdP subjects into GitHub issues or chat.

The longer steps below describe what the launcher performs and serve as an incident-response reference. **Do not run them a second time after a successful initial launch.**

## One-time VM preparation

1. Provision the VM only after explicit approval of provider, account, region, budget and trusted administrators. Install Docker Engine and Compose, restrict SSH/firewall, enable OS updates and backup destination.
2. Install and sign in to Tailscale on the VM. Enable MagicDNS and HTTPS certificates for the tailnet, and restrict access through Tailscale policy. Verify the hostname chosen for WORKSPACE_ORIGIN. Tailnet users must have Tailscale on their devices.
3. Clone the reviewed MetaAutomate repository release commit to the VM (do not deploy from an unreviewed PR). Create deploy/private/.env from .env.example, with file permissions 0600. Set two **different** random hex passwords (POSTGRES_ADMIN_PASSWORD vs APP_DB_PASSWORD). Set the configured IdP issuer/client/secret/state-secret, WORKSPACE_ORIGIN and OIDC_REDIRECT_URI.
4. Verify Compose locally:

       docker compose --env-file deploy/private/.env -f deploy/private/compose.yaml --profile admin config --quiet

5. Create the PostgreSQL service and initialize **only a new empty database** with the explicit admin-only migrator. The migrator deliberately refuses to run again against an existing schema. Future schema upgrades require a separately reviewed migration/backup.

       docker compose --env-file deploy/private/.env -f deploy/private/compose.yaml up -d postgres
       docker compose --env-file deploy/private/.env -f deploy/private/compose.yaml --profile admin run --rm migrator

6. Seed the 33 disabled draft registry capabilities using the temporary administrator container:

       docker compose --env-file deploy/private/.env -f deploy/private/compose.yaml --profile admin run --rm admin /opt/meta-scripts/seed_registry.py

7. After verifying the real IdP issuer+subject, provision the owner using the temporary administrator container. Do not paste that subject into public logs or this conversation.

       docker compose --env-file deploy/private/.env -f deploy/private/compose.yaml --profile admin run --rm admin /opt/meta-scripts/provision_oidc_identity.py --issuer <trusted-issuer> --subject <verified-oidc-sub> --email <authorized-email> --organization metaautomate-internal --role OWNER --approve

8. Start the restricted API:

       docker compose --env-file deploy/private/.env -f deploy/private/compose.yaml up -d api

9. Only with explicit network-release approval, set up **Tailscale Serve** on the VM. Official private Serve command (never Funnel):

       tailscale serve --bg 8080

   Tailscale Serve enables private HTTPS access under the VM's tailnet DNS hostname. Review tailnet policy grants, server health and IdP callback/issuer settings before inviting users. No public port 443/80 is needed on the VM for the app.

10. Confirm sign-in, tenant authorization, objective save/refresh/review, CSRF enforcement, logout, non-execution, and backups on the actual private URL. Review the logs and audit history. Keep application access limited to the approved pilot group.

## Backups and upgrades

PostgreSQL runs in a named volume. Arrange encrypted, **off-host** backups with restore testing and limited access. Avoid relying solely on local files or host snapshots. Back up before every migration or credential rotation. The initial migrator explicitly refuses an already initialized DB; do not rerun all migrations to upgrade the live database. Never use docker compose down -v.

Rotating OIDC credentials and changing IdP claims requires care: existing revocable workspace sessions expire in one hour, but account disablement at IdP is not guaranteed to revoke already active sessions until the session expires or the mapping is revoked in MetaAutomate. For urgent access removal, revoke the corresponding identity mapping and the session verifier will fail.

## Security and deployment gates

The OIDC login path uses Authlib's OIDC ID-token validation and exact issuer+subject mapping. This is stronger than development bearer keys, but a code-level SSO integration is **not** proof of production security by itself. A live trusted IdP flow, rate limiting, user account lifecycle process, external penetration test, secret storage/rotation and incident recovery plan are needed before broader access.

The existing database row-level-security design uses transaction-local PostgreSQL tenant context. A compromised application connection could modify that setting, so do not claim defense against hostile SQL execution. Further SQL privilege hardening or owner-bound SECURITY DEFINER-only operations is required before exposing the system beyond a controlled internal pilot.

**No autonomous actions**: all registered capabilities remain draft/disabled, approved plans remain non-executable and no external systems are contacted by an objective plan.

## Official brand

Primary mark: apps/web/assets/metaautomate-mark.webp, cropped from the user's approved MetaAutomate brand board. Deep navy, electric blue, silver, gold; tagline **Turn Your Vision Into Reality**; identity **Intelligence · Creation · Automation**; values Integrity, Excellence, Innovation, Impact, **Always HALAL**. See docs/brand/BRAND_SYSTEM.md.
