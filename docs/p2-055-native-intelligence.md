# P2-055 — Native Intelligence Engine

**MetaAutomate-owned** retrieval, memory and agent control: standard-library Python, SQLite FTS5 and the P2-054 task executor. No paid inference APIs, SaaS orchestration, model API keys, external vector database, cloud subscriptions or automatic publication.

## Execute right now

Run from a checkout of PR #113 (stacked on PR #112):

```bash
PYTHONPATH=apps/api python -m unittest discover -s tests -p 'test_p2_054_*.py' -v
PYTHONPATH=apps/api python -m unittest discover -s tests -p 'test_p2_055_*.py' -v
mkdir -p /tmp/metautomate-private-demo
chmod 700 /tmp/metautomate-private-demo
python scripts/run_native_intelligence_demo.py   --workdir /tmp/metautomate-private-demo   --out /tmp/metautomate-private-demo/native-result.json
```

The demo uses **fictional stock records** and a locally stored procedure. It should return one retrieval hit and four completed specialist stages with a verified evidence chain. It can also process **user-authorized non-sensitive inventory JSON** with `--input-json ... --authorized-data`; no HTTP endpoints or third-party systems are contacted. Input access controls and full private OIDC authorization are not implied by a CLI argument.

The new code in `apps/api/app/native_intelligence.py` provides:
- Tenant-filtered SQLite FTS5 search, owner-private DB permissions, SHA-256 receipts and bounded document ingestion.
- Non-executable retrieved snippets, explicit ingest consent, no arbitrary URL retrieval and safe parametrized FTS queries.
- Opt-in session context only in Python RAM (six turns per conversation, up to 128 in-memory sessions, one-hour expiry).
- Deterministic evidence-based discovery replies labeled *not neural*.
- A bridge into the four P2-054 owned specialist agents that rejects missing verification evidence.
- An optional `LOCAL_MODEL` mode calling P2-052's already-gated local-only GGUF adapter. It never launches a model automatically or calls a paid provider.

## Enable genuine local neural inference (NOT achieved by this PR)

`llama.cpp` is an open-source inference server capable of locally hosting GGUF models through `/v1/chat/completions`. Candidate model: Qwen3-0.6B (Apache-2.0 base weights; validate the specific **GGUF distribution and its licence** independently). Sources:
- https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
- https://huggingface.co/Qwen/Qwen3-0.6B

Do not automatically download a model or install an unreviewed checkpoint. The operator must supply a specific GGUF with file-owner-restricted permissions, an audited pinned llama-server executable, matching SHA-256 digests, and a private Linux network namespace with only loopback. The first-party launcher `scripts/start_native_model.py` rejects missing approvals, root execution, tampered files, non-loopback/remote URLs and over-limit threads:

```bash
# These are named placeholders; do NOT set approvals true without reviews.
export WORKSPACE_AUTH_MODE=oidc
export MAT_LOCAL_MODEL_ENABLED=1
export MAT_LOCAL_MODEL_LICENSE_REVIEWED=1
export MAT_LOCAL_MODEL_POLICY_REVIEWED=1
export MAT_LOCAL_MODEL_ISOLATION_APPROVED=1
export MAT_LOCAL_MODEL_CHECKPOINT_FILE=/private/models/approved.gguf
export MAT_LOCAL_MODEL_CHECKPOINT_SHA256=<actual-measured-sha256>
export MAT_NATIVE_LLAMA_SERVER_BINARY=/private/bin/llama-server
export MAT_NATIVE_LLAMA_SERVER_SHA256=<actual-measured-binary-sha256>
export MAT_LOCAL_MODEL_URL=http://127.0.0.1:11434/v1/chat/completions
python scripts/start_native_model.py --check-only
# Only after genuine independent approval:
python scripts/start_native_model.py
```

The existing P2-052 `configured_model()` also checks the owner-only GGUF hash and the unprivileged isolated process. A hash match is **not** a guarantee that a particular model process loaded those bytes; inspect the actual running process and record an independent real inference response. No device, memory, latency or accuracy claims have been accepted.

## Acceptance and release boundary

- **Locally executed this turn:** P2-055 knowledge/admission tests: **12/12 passed** on Python 3.13.5 using a temporary SQLite DB, synthetic documents, mock P2-054 runtime and fake model binaries. The mock agent bridge is a **contract test**, not evidence that the separate P2-054 four-agent suite executed here. No genuine neural model was loaded.
- The new GitHub workflow runs **both** P2-054 and P2-055 suites and a true integrated 4-agent demo when a runner is available. Until its jobs actually execute, neither exact-commit CI nor integrated GPU output may be claimed verified.
- P2-054 draft PR #112 and P2-052 draft PR #110 remain unmerged; P2-055 is a stacked draft. GitHub Actions issue #100 is a known pre-step runner failure; it is NOT a passing test.
- No Render/DigitalOcean provisioning, staging DB migrations, OIDC customer activation, production credentials, persistent customer chat, web deployments or paid subscriptions authorized by this source-only milestone.
- Document source authenticity is **not** inferred from its SHA-256. SQLite lacks encryption at rest; do not load regulated or confidential customer data without independently approved encryption, retention/deletion, backup and secure OIDC service controls.
- MCP/A2A interoperability in P2-054 is in-process concept mapping, not an authenticated standards-compliant network service. Tool execution is restricted to verified first-party agents and externally consequential actions still require approval **and separate audited execution authorization**.

Next proof required: **exact P2-054 + P2-055 end-to-end run on Kali with real SQLite, first licensed GGUF model generation under measured no-egress isolation, and signed operator acceptance before private staging.**
