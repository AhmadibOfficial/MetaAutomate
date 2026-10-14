# P2-03b — Local synthetic CSV/JSON inventory preview

**Source-only, subscription-free Phase 02 engineering. Not a real customer-data import. Foundation 3/9 NO-GO.**

## Implementation

Two file-content streaming endpoints are added under the development-only sandbox:

- POST /v1/domain-integrations/sandbox/inventory/import/csv
- POST /v1/domain-integrations/sandbox/inventory/import/json

Each receives **raw UTF-8 file bytes** (not a multipart upload), limits the request to 16 KiB and at most 20 synthetic SKUs, parses the content in memory, computes inventory reorder indicators and returns a checksum of the uploaded bytes. No client filename or path is opened; no file is persisted, no database writes occur and no external API is called.

The endpoint is registered only for the existing dev-key authentication mode, requires DOMAIN_SANDBOX_MODE=local_synthetic (OFF by default), a loopback workspace origin, direct loopback peer and an authenticated OWNER/ADMIN/OPERATOR principal. Browser-session POSTs inherit the existing CSRF and origin controls. Client-supplied organization/user IDs, arbitrary query keys, URLs, file paths, and provider keys are rejected. The organization-specific demo partition is derived from the **server-side authenticated principal**.

**Security caveat:** Loopback peer metadata is not proof of a real network boundary when a reverse proxy can overwrite client addresses. Never publish this route through a proxy or use it as an external integration.

## Required file formats and safeguards

CSV header, precisely: sku,label,on_hand_units,reorder_threshold_units,target_units

JSON object: exactly schema_version = 1, classification = SYNTHETIC_DEMO_ONLY and items containing those five row fields.

Both formats require header X-MetaAutomate-Demo-Data: SYNTHETIC_ONLY, DEMO- prefixed SKUs and Synthetic-prefixed labels, 1–20 rows, numeric unit limits and unique SKU IDs. JSON rejects duplicate keys, unexpected properties and boolean/non-finite quantities. CSV rejects unexpected/reordered columns, noncanonical/negative numbers and spreadsheet formula labels.

**Synthetic declarations cannot establish that an operator did not copy actual business figures. Do not submit real customer data, private inventory, identifiers or sensitive information to this sandbox.** It is an educational file-format demo only.

## Example local file commands

Use these only with an already-configured *loopback-bound* dev server and privately provisioned development bearer token. Do not paste or commit the token. Environment values: DOMAIN_SANDBOX_MODE=local_synthetic, WORKSPACE_AUTH_MODE=dev_key, WORKSPACE_ORIGIN=http://127.0.0.1:8000.

CSV:

    curl --fail-with-body -X POST http://127.0.0.1:8000/v1/domain-integrations/sandbox/inventory/import/csv -H "Authorization: Bearer $MAT_DEV_TOKEN" -H "X-MetaAutomate-Demo-Data: SYNTHETIC_ONLY" -H "Content-Type: text/csv" --data-binary @contracts/domains/v1/fixtures/synthetic_inventory_import.csv

JSON:

    curl --fail-with-body -X POST http://127.0.0.1:8000/v1/domain-integrations/sandbox/inventory/import/json -H "Authorization: Bearer $MAT_DEV_TOKEN" -H "X-MetaAutomate-Demo-Data: SYNTHETIC_ONLY" -H "Content-Type: application/json" --data-binary @contracts/domains/v1/fixtures/synthetic_inventory_import.json

Test without a server or cloud account:

    PYTHONPATH=apps/api python -m pytest -q tests/test_phase02_synthetic_import.py

Do not rerun make workspace-init on an existing Kali workspace for this test; it rotates a development access key.

## Release boundaries

The existing real BIZ-011 inventory contract stays DRAFT/DENY/unbound, with no provider scope issued. JSON/CSV preview is not a customer import system or storage tenancy. A future real importer requires business consent, validated privacy and PII handling, correct per-tenant storage with RLS, deletion/retention controls, error receipts and independently verified staging authorization. No Phase 01 gate closes as a result of a green source test. No Kali migration, DigitalOcean or Render deployment, paid subscription, external AI action, or OneCall federation is included.
