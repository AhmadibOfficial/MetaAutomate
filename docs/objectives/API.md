# Objective Engine v1.0 — Plan Preview (development only)

## Scope

The first increment is a **deterministic, read-only plan preview**, not a general natural-language interpretation engine or AI agent. Existing PostgreSQL tables (`objectives`, `workflows`, `tasks`, `task_dependencies`) remain untouched. **No migration, persistence, third-party action, capability activation, or autonomous execution** is performed.

API: `POST /v1/objectives/preview` with the local-only `X-Registry-Key` header (uses existing `REGISTRY_READ_API_KEY`; this shared key is **not** production authorization). Access only on the locally bound `127.0.0.1:8000` port during development.

Request example:

```json
{
  "title": "Increase qualified customer appointments",
  "description": "Review the sales pipeline for the next month",
  "success_criteria": [
    {"metric": "qualified appointments", "target": "20", "timeframe_days": 30}
  ],
  "constraints": ["Only contact customers who opted in"],
  "requested_capability_ids": ["BIZ-003", "BIZ-005"]
}
```

Selected capability IDs must already exist in `capability_definitions`. The preview looks up these **explicit** IDs; it does not perform semantic matching, automatically activate draft capabilities, or infer approval from the user objective. Declared dependencies are reported; dependencies not in the selected set are flagged as `unselected_dependencies`. Cyclic dependencies within the requested set are rejected, but the graph is a **proposal only** and must not be treated as a schedulable DAG until authorization and dependency readiness checks are added.

Output includes `objective`, `matched_capabilities`, `work_graph`, `warnings`, and the invariant `execution_allowed: false`, `persisted: false`. Selected capabilities always have `execution_ready: false` in this release, even if catalog metadata changes.

Validation: the title must be 8–200 characters; one to eight explicit success criteria; each criterion needs a metric, target and 1–3650 day timeframe; at most 20 constraints and 10 capability IDs. Unknown/invalid IDs return HTTP 422. Missing/wrong key returns HTTP 401, and missing auth configuration returns HTTP 503.

## Local test

From the repo root on Kali Linux, after applying the overlay:

```bash
# Existing containers: the api mounts apps/api, so newly added Python files are visible.
docker compose exec -T api python -m pytest -q -p no:cacheprovider tests/test_objectives.py

# Full validation (includes original suite):
docker compose run --rm -T -v "$PWD:/workspace:ro" -w /workspace \
  -e PYTHONPATH=/workspace/apps/api api python -m pytest -q -p no:cacheprovider \
  --import-mode=importlib apps/api/tests tests/
```

Use a developer test key from the ignored `.env` file for manual requests; do not print/share the real key. Never expose this route publicly as authentication and tenant isolation are not implemented for objectives.

## Next phase

Implement authenticated principal/tenant context and a dedicated least-privilege database role before enabling `POST /v1/objectives` or persisting work graphs. Then validate dependency DAGs, production contracts, approvals and verification. Do not use `execution_allowed` from a client payload; execution eligibility must be server-enforced.
