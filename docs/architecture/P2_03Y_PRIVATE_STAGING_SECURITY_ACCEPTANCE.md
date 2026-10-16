# P2-03y — Private-Staging Security Acceptance

**Engineering classification: source-only acceptance preparation. Operational status: NO-GO.**

Public website [metaautomate.onrender.com](https://metaautomate.onrender.com) is separate from these controls. No protected API, real staff login, production agent runtime, private hosting, model API or customer data is activated by this source PR.

## Scope built in this milestone

1. **Real-IdP integration primitive, *not* a real login:** `apps/api/app/p2_03y_oidc_verification.py` has an explicit HTTPS issuer/audience/JWKS/private callback contract, out-of-band RSA key pinning, an RS256 ID-token signature verifier, a session-bound random nonce, freshness rules, a signed `amr` MFA claim requirement, and a separate trusted local staff/tenant/role roster. The API does **not** discover IdPs, fetch JWKS, accept arbitrary issuer keys, run an authorization-code/PKCE flow, create browser sessions, verify an actual MFA challenge, or validate real staff employment. There is **no configured provider or login**. CI creates ephemeral keys and fictional subjects. Integration must use an independently authorized operator-supplied trust root, session nonce lifecycle, issuer discovery security checks, cookie/CSRF defenses, short sessions, key rotation, real directory membership and revocation.
2. **Actual operational evidence matrix:** `contracts/domains/v1/policies/p2_03y_private_staging_acceptance.v1.json` has the Foundation F04–F09 and six Intelligence control proof classes: OIDC, isolated agent runtime, task-specific model safety/cost, provider/tool scope, data/consent, and externally witnessed recovery. All flags remain **false**. `apps/api/app/p2_03y_security_acceptance.py` validates the policy and original Foundation register; a source-only result cannot set an operational flag.
3. **Model admission:** A strict pre-authorization validator accepts four provider-documented model names and four synthetic task categories only for a **zero-cost, zero-provider-token, synthetic preview**. It rejects every request that claims actual authorization, a paid invocation, credentials or unknown user data. This is not a model evaluation or a provider adapter.
4. **Network and agent isolation:** The existing `deploy/staging/compose.yaml` passes its source-only template checks but connects the API to an unrestricted `egress` network. That does **not** prove that arbitrary model calls or tools cannot leave the network. The new CI job starts a **temporary throwaway container** with `--network none`, readonly root, nonroot user, dropped capabilities, no Docker socket or credentials, memory and PID limits; it verifies outbound connection failure. This does **not** prove that the actual MetaAutomate agent, IdP or provider is isolated in a live private environment.
5. **Independent recovery contract:** A typed backup/restore receipt checks SHA-256 format, encryption flags, off-host/separate failure-domain claims, witness reference and observed RPO/RTO values. It does **not** verify the referenced backup, restore, external signing, independent witness, or an immutable audit anchor. All such submissions remain **F07 unverified**, even when their structure is correct.
6. **Security acceptance reports:** `scripts/verify_p2_03y_acceptance.py` generates `artifacts/validation/p2-03y-private-staging-security.json` with explicit missing gates and uncovered API egress. `--require-operational-go` intentionally fails. Neither script deploys, updates accounts, enables customers, purchases subscriptions, executes migrations or changes the official Phase 01 evidence register.

## Required evidence before authentic private-staging security acceptance

| Gate | Independently demonstrated evidence | Current state |
| --- | --- | --- |
| **F04** | Protected private `main`, required failing-check merge denial, independent reviewer signoff | **Blocked** |
| **F05** | Approved host, region, cost ceiling, isolated database and private ingress, machine-validated outbound firewall and network-denial test | **Blocked** |
| **F06** | Live IdP authorization-code + PKCE, callback state/nonce, registered MFA factors, issuer JWKS refresh/rotation, tenant membership and genuine session revocation | **Blocked** |
| **F07** | Encrypted backup stored off host, separate restore operator, verifiable restore data, RPO/RTO and independent trusted audit checkpoint | **Blocked** |
| **F08** | Two-tenant isolation, provenance/privacy review, tool/model permission testing, red-team negative cases, monitoring, kill switch and rollback | **Blocked** |
| **F09** | Consent-backed pilot, baseline, measured outcomes, retention policy and independent result review | **Blocked** |

The **additional six Intelligence gates** must be satisfied inside F05–F08 using real evidence: IdP, agent isolation, model benchmark/cost/safety, restricted provider/tool grants, real-data consent, recovery/audit continuity. They may not be waived by signed synthetic test actors or passing offline project simulations.

## Reproducible free source-level checks

```sh
python -m pip install 'pytest>=8,<10' 'cryptography>=43,<48' 'PyYAML>=6,<7'
python -m pytest -q tests/test_p2_03y_oidc_verification.py
python -m pytest -q tests/test_p2_03y_security_acceptance.py
python scripts/verify_p2_03y_acceptance.py
# Must exit nonzero (release prohibited):
python scripts/verify_p2_03y_acceptance.py --require-operational-go
```

A separate GitHub Actions job executes the disposable no-network container test. It consumes CI runner resources only; this is not provisioning an approved staging subscription, guaranteed zero cost for all future operations, or a live service deployment.

## Next practical dependency

First resolve **F04** private GitHub merge enforcement without exposing the business repository. Obtain approved and independently secured F05 staging hosting/access/cost and real IdP selection. Then implement IdP authorization-code/PKCE, secure callback, staff directory binding and revocation **in that approved environment**, while keeping live model calls and tools off until a witnessed F06–F08 negative-acceptance run is complete. No real data until F09 and all required gates.

**As of this P2-03y source milestone:** Phase 01 remains 3/9 verified; Phase 02/03 operational NO-GO; no new DigitalOcean/Render work, production API, live model, subscription purchase, source migrations, real client workflows, or website deployment.
