# P2-04q — Authorized Private Speech Runtime Gate

**Status: source-only engineering. Real neural model inference and human approval NOT demonstrated.**

## Required operating boundary

This milestone cannot run in the current ChatGPT execution environment: no approved ONNX model or Piper engine is present; it runs as UID 0 with a non-loopback \`eth0\` interface and an IPv4 default route. The new gate deliberately rejects this host.

Before attempting actual inference, prepare on an owner-controlled Linux workstation a restricted **non-root, no-network namespace** or container, with:
- the exact pinned private Git commit of draft PR #97 (no tracked edits);
- approved offline Piper executable with exact SHA-256, verified compatible \`--model\`, \`--config\`, and \`--output_file\` command-line options; the engine and dependent binaries/libraries must have been reviewed and pinned (this source currently pins only the primary executable hash);
- privately staged \`voice.onnx\`, matching \`voice.onnx.json\`, and actual licence, contents-rights and speaker-consent records as applicable; record hashes in the signed job;
- private 0600 input files, and 0700 private quarantine directory;
- three distinct independently registered Ed25519 public keys: the owner and **two separate human reviewers**;
- a time-limited authorization JSON signed by all three keys over the exact same immutable model/config/engine/text/evidence payload and with \`signatures\` role order \`OWNER\`, \`REVIEWER_1\`, \`REVIEWER_2\` (expiry no more than 30 minutes);
- a human-validated commercial-use decision covering engine GPL obligations, model rights, speaker rights, attribution and consent. Hashes and signatures authenticate **assertions** but cannot themselves demonstrate that those legal reviews are legitimate.

## Verifiable runtime gate

The \`creative_speech_runtime_preflight.verify_operator_preflight\` rejects the run if any of these occur:
- checked-out Git SHA does not match the explicitly supplied approved commit or tracked files differ;
- the ONNX model hash, executable, config, exact narration script or actual licence/rights/consent evidence hashes differ;
- any of the three keys/signatures/roles is absent, duplicated, tampered or expired;
- the process is not running Linux as an unprivileged user;
- \`/sys/class/net\` contains an interface other than \`lo\`;
- \`/proc/net/route\` has a default route or cannot be inspected;
- the process network namespace cannot be read from \`/proc/self/ns/net\`.

This is evidence of local kernel state, not independently witnessed isolation. It does not prove that a privileged process could not later modify namespace configuration. Operators must enforce network lockdown outside the application, run unprivileged, drop all capabilities, and keep the source/output mounts private. Prefer an offline sandbox with **no network namespace access to external interfaces, no host networking, and no privileged container**. Do not give the process a public server binding or internet access.

## Exact operator entry point (only after all evidence exists)

\`\`\`bash
cd /path/to/private/MetaAutomate
# Replace all paths and key strings with real, owner-controlled material.
# Run INSIDE the non-root offline network sandbox only.
export PYTHONPATH="$PWD/apps/api"
export MAT_SPEECH_OFFLINE_EXECUTION_ENABLED=1
export MAT_SPEECH_NETWORK_ISOLATED=1
export MAT_SPEECH_LICENSE_REVIEWED=1
export MAT_SPEECH_INDEPENDENT_HUMAN_APPROVAL=1
export MAT_SPEECH_OPERATOR_ISOLATION_EVIDENCE_CONFIRMED=1
python -m app.creative_speech_operator_acceptance \
  --repo-root "$PWD" \
  --expected-commit "<REVIEWED_EXACT_PR_HEAD_SHA>" \
  --job /private/job.json \
  --authorization /private/owner-and-two-reviewers.json \
  --text /private/narration.txt \
  --voice-onnx /private/voice.onnx \
  --piper-bin /private/bin/piper \
  --license-evidence /private/evidence/engine-model-license.txt \
  --rights-evidence /private/evidence/voice-rights.txt \
  --quarantine /private/quarantine \
  --owner-public-key "<PRE-REGISTERED_OWNER_PUBLIC_KEY>" \
  --reviewer-public-key "<PRE-REGISTERED_REVIEWER_ONE_PUBLIC_KEY>" \
  --second-reviewer-public-key "<PRE-REGISTERED_REVIEWER_TWO_PUBLIC_KEY>"
\`\`\`

When a consented likeness is involved, also supply \`--consent-evidence /private/evidence/voice-consent.txt\`, and bind its real hash in the signed speech job. **Placeholders in the command are deliberately not valid authorization values.**

A passing preflight returns only \`RUNTIME_PREFLIGHT_CLAIMS_VERIFIED_NO_INFERENCE\`. If the actual pinned model runs, the WAV and technical receipt are quarantined; even then the output status is \`OUTPUT_CREATED_PENDING_INDEPENDENT_POST_REVIEW\`, not verified neural speech.

## After a real WAV exists

1. Independently observe the specific Piper model subprocess in the pinned no-egress namespace, engine/model SHA and logs. Receipt claims alone do not prove neural inference.
2. Inspect exact WAV checksum, PCM characteristics, speech duration, clipping, and the original script.
3. Have an independent human actually **listen**, compare transcript word by word, evaluate intelligibility and pronunciation, and review the real speaker rights, source text and audio safety. Record real evidence files and SHA-256 hashes.
4. Apply the existing \`creative_speech_review_signing\` process with a registered independent reviewer. An automated test-generated signature is not genuine listening evidence.
5. Keep the WAV quarantined. Its authenticated approval is not release authorization, and it does not bypass GitHub required checks.

## CI/local evidence state

MetaAutomate GitHub Actions have repeatedly failed prior to job steps, including a one-command diagnostic (issue #100). Targeted source tests for this change are added to \`.github/workflows/p2-04q-offline-speech-source.yml\` and to \`scripts/verify_p2_04q_local_gate.py\`. They must run on an **actual** pinned private checkout and may provide source-test evidence, but they do not satisfy GitHub required checks or prove a real licensed neural recording.

No new subscriptions, paid cloud instance, credential provisioning, public API, customer data, deployment or publishing is authorized.
