# P2 cross-branch offline source conformance — draft, no release authorization

**Status:** Source-only integration rehearsal. Phase 01 Foundation **3/9 NO-GO**. No live Phase 03 execution and no commercial pilot permission.

## Provenance and technique

The isolated branch starts from exact `main` SHA `7144451b0ac37349c3e731bac76d14338280c42e`. It references the **31 original Git blob objects** (modules, original pytest suites, docs, local verification helpers and manifests) at the pinned heads of still-draft PRs #32–#39. It does not merge, modify, approve, or close those source PRs; it does not change `main` or `apps/api/app/main.py`.

The manifest `contracts/engineering/p2_full_offline_integration_lock.json` records exact parent SHA, per-PR head SHA, per-file Git blob SHA and explicit release **DENY**. The integration test recomputes each file's Git blob hash from the actual checkout bytes so silent changes cannot be mistaken for approved source.

## Scope of joined verification

- Original individual regression suites for P2-04a–e, P2-05a–b and P2-05c–f/P2-06 are all copied unchanged into the **same test tree**.
- `tests/test_phase02_cross_branch_integration.py` explicitly instantiates standalone fake resilience reservations, delivery state, demo webhook signature verification and synthetic incident observations for one invented tenant. These actions are **manually orchestrated in pytest**—there is no actual webhook trigger, integrated adapter, database, queue or distributed workflow.
- It also orchestrates invented CRM and financial proposals from two independent toy state machines, fake review labels, preflight denial, synthetic receipt consistency, pilot NO-GO, read-only fake stock and cross-tenant isolation. Two fake endorsements on a financial case still do **not** authorize execution.
- Replays and mismatched tenants are negatively tested. At every stage `executed=false` / `execution_authorized=false`; no customer data, real provider calls or actual approval can be generated.
- GitHub runs full CI on this **single assembled integration head**. Unlike the earlier PR #36 source-overlay check, this candidate puts all reviewed source snapshots in one actual Git tree. It remains an **integration rehearsal**, not final system integration.

## Quick local Kali acceptance after GitHub CI

Do not overwrite changes. Before checkout confirm `git status --porcelain` is empty. Substitute the **exact PR number and final head SHA recorded in GitHub**:

```bash
cd ~/MetaAutomate
git status --short
git -c http.version=HTTP/1.1 fetch --no-tags origin refs/pull/PR_NUMBER/head
test "$(git rev-parse FETCH_HEAD)" = "PINNED_PR_HEAD_SHA"
git switch --detach PINNED_PR_HEAD_SHA
source ~/.venvs/metaautomate-p204a/bin/activate
PYTHONPATH=apps/api python -m pytest -q -p no:cacheprovider --import-mode=importlib \
  tests/test_phase02_cross_branch_integration.py \
  tests/test_phase02_delivery_rehearsal.py \
  tests/test_phase02_synthetic_webhook_proof.py \
  tests/test_phase02_synthetic_incident_observability.py \
  tests/test_phase02_synthetic_delivery_resilience.py \
  tests/test_phase02_synthetic_write_proposals.py \
  tests/test_phase02_synthetic_approval_preflight.py \
  tests/test_phase02_completion_bundle.py \
  tests/test_phase02_offline_stack_contract.py \
  tests/test_phase02_local_gate_helper.py
git rev-parse HEAD
```

The single command `python scripts/verify_phase02_local_gate.py --expect-sha PINNED_PR_HEAD_SHA` also runs every checked-out `tests/test_phase02_*.py` and produces a summary, provided the local worktree is clean. A GitHub CLI GraphQL handshake timeout does not imply failed source tests; the exact PR Git ref can be fetched over Git HTTP/1.1 as above. If checkout fails, report **NO LOCAL ACCEPTANCE**, never a pass.

## Limitations and release boundary

This assembled branch is **not** an actual server-integrated system: identity IDs/tenant UUIDs and reviewer labels are invented, the HMAC uses fake fixture key bytes, timestamps are invented ticks, evidence chains are local unkeyed hashes, receipts are locally fabricated, and there is no authenticated ingress, durable state, provider integration, worker, customer account or real notification.

Passing GitHub CI and Kali tests does not waive any independent code review, private-repository branch protection, controlled source integration plan, off-host recovery proof, production-grade OneCall service identity, tenant isolation, approved staging, read-only provider authorization or commercial pilot gate. PRs #32–#39 must not be marked merged/approved because their blobs were reused for a test candidate.

Operational blockers remain at GitHub issue #40. **Phase 01 3/9 — NO-GO; Phase 02 production — NO-GO; Phase 03 live capability execution — NO-GO.**
