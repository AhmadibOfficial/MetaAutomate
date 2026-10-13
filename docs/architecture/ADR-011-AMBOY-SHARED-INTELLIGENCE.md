# ADR-011: AMBOY shared intelligence

Status: proposed architecture, awaiting implementation review.
Date: 13 October 2026.
Owner: MetaAutomate. Connected product: OneCall.

## Decision
Amboy is a MetaAutomate-owned conversational intelligence service. MetaAutomate uses Amboy natively; OneCall connects through a separately authorized, product-scoped adapter. Amboy should have a distinct product identity and an excellent conversational interface, while execution is always governed by verifiable permissions, not merely generated text.

The core service is shared. User accounts, conversation history, organization records, credentials, bookings, service data and authorization **are not shared** across products. An OneCall customer has no implicit MetaAutomate account. Identity must be established separately in each product, never inferred from matching email or an untrusted client-supplied product or tenant ID.

## Boundaries

- Amboy Gateway: product authentication, scopes, quota, audit, requests.
- Conversation service: isolation by authenticated product, tenant and subject.
- Provider-agnostic model gateway: future model integration and spend limits.
- Policy engine: server-side allowlisted capability definitions, input validation and permission checks.
- Product adapters: MetaAutomate Objective Workspace / OneCall service API.
- Future action workers: approval, idempotency, execution and authoritative result verification.

MetaAutomate functionality starts with assisting objective discovery and drafting or explaining plans. Current Objective Workspace has deterministic proposed plans, not agent execution.

OneCall functionality starts with reading its actual provider/service catalog and preparing a booking proposal. The backend alone confirms available services, booking policy and final status. Amboy must not claim a booking was completed unless the OneCall backend supplies a confirmed receipt. No simulated ad views or invisible booking/charge actions.

## Trust and privacy
Each invocation derives actor, product, tenant and scopes from server-validated identity. A model response is untrusted until a specific capability adapter validates it. Read tools do not imply write access. Customer approval is explicit, scoped and time-limited, and does not substitute for backend business policy. Reject cross-product data access, prompt injection through untrusted service descriptions, arbitrary code execution and unaudited tool calls.

Retain customer data only under product-specific approved policies. No cross-product personalization or training without separate authorization. Log correlations and safe evidence, not credentials or private message contents. Model usage must be metered and budget-limited per product.

## Milestones
M0: Architecture contracts, threats and owner review.
M1: Secure product identity, tenant mapping, quotas, no-model deterministic test gateway.
M2: Model integration with grounded answers and bounded costs.
M3: MetaAutomate read-only objective assistant and safe draft-plan creation.
M4: OneCall authorized service discovery and booking proposals.
M5: Explicit-approval tool execution and evidence-based verification.
M6: Reliability, observability and secure staging/production review.

This ADR is a design decision only. It does not deploy Amboy, implement AI inference, grant agent permissions, change production websites or provision external resources. Existing draft capabilities remain disabled.
