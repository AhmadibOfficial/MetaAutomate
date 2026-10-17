# P2-04q — Verified AI Speech Generation (offline Piper adapter)

**Status: proposed, source-only. Genuine neural speech has NOT been demonstrated.**
P2-04q is stacked on P2-04p PR #95, which itself remains draft. PR #94 video remains draft. None of this activates subscribers, public generation, customers or publishing.

## Engine and licensing gate

The optional offline adapter in \`apps/api/app/creative_offline_speech.py\` executes an **operator-installed Piper** ONNX binary against **preinstalled local voice files**, taking text from a signed speech job on stdin, and generating a private WAV. No Piper binary, voice/model weights, onnxruntime or hosted vendor are distributed or installed by this repository.

- Reference implementation: Open Home Foundation Piper, https://github.com/OHF-Voice/piper1-gpl . The current maintained Piper engine identifies as **GPL-3.0**; licensing obligations for use, modifications and any redistribution must be reviewed before commercial deployment. Running a separate local executable is not a substitute for legal clearance.
- Each voice checkpoint and source dataset has **its own model card and licensing conditions**, independently of the Piper software licence. A model repository-wide label does not clear every voice.
- A *possible candidate for manual licence review*, **NOT yet approved or installed**, is Piper's \`en_US-libritts-high\` voice: https://huggingface.co/rhasspy/piper-voices/tree/v1.0.0/en/en_US/libritts/high . Its model card reports CC BY 4.0 training dataset and from-scratch training on train-clean-360; confirm upstream/derivative rights and attribution before any paid usage.
- Do not download voices during execution. An administrator must separately obtain, inventory and approve the exact \`.onnx\`, matching \`.onnx.json\`, \`MODEL_CARD\`, rights evidence, Piper executable and their SHA-256 hashes. Keep executable/model in a read-only offline mounted environment; run unprivileged, without network access and with bounded CPU, memory and time. An environment flag alone does NOT enforce egress blocking.
- Run only on first-party/sample text that is owned or independently authorized. No recognizable voice imitation without verifiable voice-owner permission.

## Contract and flags

\`apps/api/app/creative_audio_assets.py\` specifies a bounded job (speech, prompt text, \`target_seconds\`, language, voice/style direction, rights/authorization document hashes, \`voice_likeness=none|consented\`). Model SHA-256 and model card SHA-256 must match actual files.

\`apps/api/app/creative_offline_speech.py\` requires a second JSON authorization with an exact job, config and binary SHA, a 1–30-minute validity window, explicit human licence/rights/consent/offline review declarations and **two independent Ed25519 signatures** (OWNER and INDEPENDENT_REVIEWER). Public signing keys are supplied from protected operator settings. Generate and approve these records out-of-band with actual accountable human signers, never automatically.

The worker has no API entrypoint and is **OFF by default**. Only within an independently enforced no-network runtime, an operator may set:

\`\`\`bash
export MAT_CREATIVE_SPEECH_OFFLINE_ENABLED=1
export MAT_CREATIVE_NETWORK_ISOLATED=1
export MAT_CREATIVE_OWNER_VERIFY_KEY='<approved owner public key, base64url>'
export MAT_CREATIVE_REVIEWER_VERIFY_KEY='<independent reviewer public key, base64url>'
PYTHONPATH=apps/api python -m app.creative_offline_speech \
  --job /private/speech/job.json \
  --approval /private/speech/signed-approval.json \
  --model /private/voices/voice.onnx \
  --config /private/voices/voice.onnx.json \
  --model-card /private/voices/MODEL_CARD \
  --rights /private/speech/rights.txt \
  --binary /private/bin/piper \
  --quarantine /private/quarantine
\`\`\`

Use \`--consent /private/speech/voice-consent.txt\` only for an explicitly consented identifiable voice. The owner and reviewer keys are PUBLIC verification keys; private signing keys must remain outside source and outside this runtime. The binary is pinned by its hash and must have basename \`piper\` or \`piper.exe\`.

The actual Piper CLI is invoked only after authorization. Successful invocation creates a private 0700 directory containing 0600 \`generated.wav\`, \`receipt.json\` and \`operator-run.json\`. WAV checks include PCM framing/sample rate, duration tolerance, nonzero samples, sample statistics, exact job and model/output digest binding. Some Piper voices produce 16 or 22.05 kHz PCM; do not pretend the source waveform is 48 kHz.

## Independent final review

A real language-capable human reviewer must listen to the entire final voice clip, check transcript fidelity, pronunciation and language quality, possible hateful/deceptive content, model/output rights, any likeness/consent, and the actual audio including distortions. Record hashes of underlying transcript/quality/rights/safety evidence, sign a review bound to **the exact WAV SHA-256** and expiry.

A second independent review verifier is available:

\`\`\`bash
export MAT_CREATIVE_SPEECH_FINAL_REVIEW_VERIFY_KEY='<approved final-review public key, base64url>'
PYTHONPATH=apps/api python -m app.creative_speech_review \
  --job /private/speech/job.json \
  --receipt /private/quarantine/<run-id>/receipt.json \
  --review /private/speech/signed-final-review.json \
  --audio /private/quarantine/<run-id>/generated.wav
\`\`\`

An authentic human-review signature means only that the claims were signed. The software cannot independently certify the truth of licence claims, safety-scanner execution or speech comprehensibility. Even a passing human review **never authorizes public distribution**.

## Exact acceptance gates (all outstanding for a real demonstration)

1. Local operator records actual Piper executable/version, checksum, OS/container isolation verification and real voice checkpoint/config/model-card SHA-256.
2. Model terms and content/voice consent are independently examined, accepted and preserved, along with attribution where required.
3. Two distinct human approvers sign the exact bounded speech job with current expiry and model/binary fingerprints.
4. Piper runs *without network access* on an original, authorized short narration; actual process completion and waveform, sample-rate and duration are independently witnessed and stored privately.
5. PCM verifier passes on the exact artifact; record SHA-256 receipt, model version, sample-rate, duration, clipping/quality measurements and runtime costs.
6. A separate qualified human reviews language/pronunciation/transcript fidelity, safety and rights; signs final SHA-bound review. Demonstrate that changes, expired reviews and different voices fail closed.
7. Evidence owner explicitly approves any later customer/release milestone after all Phase 01/02/03 operational gates; this milestone itself **does not publish**.

**CI tests contain fake model bytes and a monkeypatched Piper process that writes synthetic PCM. They are security regression fixtures, not neural voice evidence.** The current execution environment has no local Piper or ONNX engine/voice weights installed, so no actual model execution was performed as part of this development.

Next: once genuine speech output is evidenced, expand to voice quality benchmarks, multilingual voice packs with independently inspected model cards, then licensed music/SFX and cinematic mixing. No subscription, hosted inference or automatic publishing is enabled.
