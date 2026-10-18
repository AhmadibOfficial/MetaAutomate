# P2-052 — Private Real Task Execution Engine

**Delivered:** actual server-side task handlers that take authenticated task input and return downloadable completed output bytes. This is deliberately not another planning prototype.

**Available executable operations in source:**
- \`INVENTORY_REORDER_CSV\` accepts up to 80 SKU stock rows and computes real reorder shortfalls, stock values in the specified currency's minor units, and CSV output. It cannot prove submitted numbers are accurate.
- \`ORIGINAL_BRANDED_SVG\` generates an original 1200 × 675 SVG file entirely on the server, using only XML-escaped user input, controlled colors, no external images or executable SVG. Not neural image generation.
- \`LOCAL_MODEL_TEXT\` accepts a project-scoping prompt, educational post or short video-script request and calls an explicitly pinned **local** OpenAI-compatible language-model runtime for a genuine response. It is **NOT enabled or proven operational** until a legally approved model process and egress-isolated host exist.

This feature does not send external messages, schedule posts, book services, execute arbitrary code, buy subscriptions, generate neural media or bypass existing Objective Operations review.

## Private API contracts

Under independently approved OIDC-only runtime:
- \`POST /v1/private-tasks\` with header \`Idempotency-Key\` (12–100 safe chars); role OWNER/ADMIN/OPERATOR; same actor limit 20 completed tasks/hour. Executes within the request, then atomically saves finished artifact plus digest. Returns 201, artifact link and SHA-256. No untruthful QUEUED claims.
- \`GET /v1/private-tasks/{uuid}\` for metadata from the authenticated actor's own organization and user identity.
- \`GET /v1/private-tasks/{uuid}/artifact\` returns an attachment with independent SHA-256 verification, CSP sandbox and no-store headers. Owner-specific RLS applies; other tenant/users receive 404.

The task job table uses immutable results for the runtime identity (SELECT/INSERT only), enforced tenant and actor RLS, unique idempotency keys, seven-day **access expiry**. Physical deletion is **NOT automatic** merely because a record expires. The independent maintenance script \`scripts/purge_expired_private_tasks.py\` is dry-run-first and requires a separate approved maintenance DB identity; a real purge schedule and encryption/retention assessment remain operational gates.

### Inventory CSV example

\`\`\`http
POST /v1/private-tasks
Idempotency-Key: stock-20261018-001
Content-Type: application/json
Cookie: mat_workspace=<AUTHENTICATED_WORKSPACE_COOKIE>
X-CSRF-Token: <AUTHENTICATED_CSRF_TOKEN>

{
  "task_type": "INVENTORY_REORDER_CSV",
  "inventory": {
    "currency": "NGN",
    "items": [
      {
        "sku": "MAIZE25",
        "label": "Maize bags",
        "on_hand": 7,
        "reorder_at": 20,
        "unit_cost_minor": 125000
      }
    ]
  }
}
\`\`\`

Expected verified computation: reorder quantity 13; stock value 875000 minor units. Response contains an actor-authenticated artifact URL and checksum. Never paste live auth cookies into public documentation.

### SVG graphic example

\`\`\`json
{
  "task_type":"ORIGINAL_BRANDED_SVG",
  "graphic":{
    "brand":"MetaAutomate",
    "headline":"Solve problems that matter",
    "message":"Build systems that create measurable value",
    "theme":"white"
  }
}
\`\`\`

### Private real neural text endpoint

\`\`\`json
{
  "task_type":"LOCAL_MODEL_TEXT",
  "text_job":{
    "prompt":"Write a practical first release scope for a mobile inventory tool for small shops.",
    "output_kind":"PROJECT_SCOPE"
  }
}
\`\`\`

The local model adapter uses only \`127.0.0.1:<port>/v1/chat/completions\`, strict timeout/size limits, pinned configured checkpoint digest, and no model tools or remote URL. A kernel check requires an unprivileged Linux no-egress network namespace containing only \`lo\`, but this check is not an independent cryptographic isolation attestation. An environment-provided digest does not prove the loaded checkpoint is identical; the operator must produce external measured process evidence.

## Admission prerequisites for an actual staging deployment

**DO NOT simply set environment flags to 1.** Required first:
1. Resolve the exact-commit GitHub Actions test startup failure (issue #100) or obtain equivalent independently witnessed exact-commit test evidence. Run the deterministic task tests and real Postgres/OIDC isolation tests.
2. An authorized **private OIDC with MFA**, valid IdP callbacks, HTTPS origin, CSRF, restrictive DB role and proven tenant isolation; no public static-site API enablement.
3. Approved isolated PostgreSQL DB, encrypted-at-rest/backups, specific migration execution plan for **012–017** (012–015 and 016 remain unapproved/unapplied). Do not skip older migrations.
4. Executed migration 017 and verified metadata/bytea retention, actor-level RLS, idempotency under concurrency, role permissions, seven-day access expiry and operator-only purge process.
5. Measured CPU/memory, maximum request concurrency, 20-second model timeouts, server-side quotas and error retry policies; no shared prod credentials or customer traffic.
6. Actual commercially cleared model checkpoint, dependencies, legal rights, hardware sizing, isolated model process, externally attested executable/weight hash, real response and human quality checks for \`LOCAL_MODEL_TEXT\`.
7. Operator deployment authorization with a financial cost ceiling; no Render/DigitalOcean resources provisioned and no subscriptions purchased as part of this source increment.

Private API startup remains OFF by default. Only an operator-approved deployment can set:
\`\`\`text
WORKSPACE_AUTH_MODE=oidc
MAT_PRIVATE_TASKS_ENABLED=1
MAT_TASK_STORAGE_APPROVED=1
\`\`\`

Additional neural model conditions (do NOT set before independently verified):
\`\`\`text
MAT_LOCAL_MODEL_ENABLED=1
MAT_LOCAL_MODEL_LICENSE_REVIEWED=1
MAT_LOCAL_MODEL_POLICY_REVIEWED=1
MAT_LOCAL_MODEL_ISOLATION_APPROVED=1
MAT_LOCAL_MODEL_URL=http://127.0.0.1:11434/v1/chat/completions
MAT_LOCAL_MODEL_ID=<exact-reviewed-identifier>
MAT_LOCAL_MODEL_CHECKPOINT_SHA256=<64-digit-hash>
\`\`\`

No customer accounts, permanent chat history, video/image/speech inference or public API integration are claimed complete by this milestone. The public Render service remains a **static website**; the private task API is an independently gated deployment.

## Tests and evidence

\`\`\`bash
PYTHONPATH=apps/api pytest -q \
  tests/test_p2_052_private_execution.py \
  tests/test_p2_052_local_model_worker.py
\`\`\`

The unit suite covers real inventory/SVG output bytes, spreadsheet formula escaping, XML-safe media, tenant/actor isolation, idempotent replays, digest mismatch, per-hour rate caps, and denial of unsupported model URLs/tool calls. These are source tests; successful isolated unit tests are not substitute evidence for authorized real model execution, operational DB migration or live deployment.
