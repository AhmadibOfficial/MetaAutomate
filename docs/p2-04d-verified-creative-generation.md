# P2-04d — Verified Creative Generation acceptance

Status: **source implementation only; no genuine local model output has been produced or inspected in this PR.** Do not claim this milestone complete from CI fixture tests.

## Evidence requirements

1. Secure an appropriately licensed, locally stored safetensors model; independently inspect and record model terms and permitted commercial use, source and exact model-tree SHA-256. Do not download models in the worker.
2. Run `app.creative_local_generation` separately for image and short video using two human Ed25519 signatures, expiring authorization and distinct requester/reviewer identities. Confirm a network-blocked isolated GPU runtime **outside** the Python environment flags. Never execute on public Render.
3. Record exact command, runtime versions, CUDA/device, no-egress network test, checkpoint tree digest, actual successful generation logs and model/operator attestations. Job receipt alone is not independent proof that real inference occurred.
4. Run `python -m app.creative_acceptance --quarantine-folder /absolute/private/quarantine/<receipt-id> --kind image` and similarly `--kind video`. Requires Pillow for PNG; ffprobe for MP4. Media and its receipt must be owner-only (0600), within a private 0700 directory. The check validates receipt integrity, SHA-256, PNG/MP4 stream metadata and dimensions, but cannot attest neural inference or review safety.
5. Produce **separate** signed output reviews using `app.creative_output_review`, with independent human inspection, lawful rights/likeness evidence and *real* applicable safety-scanner outputs. Preserve scanner version, configuration and its immutable report hash. A checked box or a signed claim is not automated rights verification.
6. Maintain a private acceptance register with image/video job SHA, checkpoint tree SHA, media SHA, receipt SHA, local host/driver/runtime versions, reviewer IDs, signed authorization and signed output review digest, operator-inference proof and explicit HOLD/NO-GO.
7. Do not expose private outputs, credentials, personally identifying consent records, or generated media through GitHub artifacts, CI, Render, marketing website or public downloads.

## 30–120-second educational videos

Existing worker produces only 16–64 frames at 8 fps (2–8 seconds), not full 30–120-second videos. A **future separate** composition pipeline must validate rights for every scene/music/narration source, enforce constrained FFmpeg input manifests (no remote URLs/protocols), inspect audio/subtitle synchronisation, record hashes for intermediate and final assets, and demand new human approval of the composed final hash. None of that is implemented by this evidence verifier.

## Acceptance table

| Gate | Required evidence | Current |
|---|---|---|
| Genuine image | Independently observed GPU inference, privately quarantined PNG and integrity receipt | NOT VERIFIED |
| Genuine short video | Independently observed GPU inference, privately quarantined MP4 and integrity receipt | NOT VERIFIED |
| Media metadata | P2-04d verifier reports PASS for both media types | NOT RUN on real outputs |
| Safety and rights | Actual reports, authenticated licence/consent and signed independent human decision | NOT VERIFIED |
| Distribution | Separate publication security/release gate | NO-GO |

Operational Phase 01 (3/9), Phase 02 and Phase 03 NO-GO remain unchanged. No subscriptions, external customers, hosted inference or publishing are authorized by this work.
