# P2-04q — Verified AI Speech Generation: offline adapter (source increment)

**Status:** implementation and synthetic negative tests only. No licensed voice checkpoint, executable, genuine synthesis, voice-quality evidence, signed approval, or legal assessment was supplied or run. Do **not** call this capability genuinely verified.

## Integration
The optional `apps/api/app/creative_speech_offline.py` adapter consumes the P2-04p job contract with exact authorized text, a local ONNX voice checkpoint/config pair, and a pinned local Piper-compatible executable. It refuses execution unless four operator attestation flags are present; those flags are **not** independent proof of host egress isolation, rights or signatures. It checks the checkpoint digest, local paths, private file modes and blocks model downloads. It creates private quarantined WAV and a separate evidence record with model/config/engine/text/output digests, never publishing.

It calls the local Piper CLI using an argument array with stdin and bounded runtime. **A model may emit a different WAV sample rate or duration than a requested target, in which case downstream validation blocks it.** Fake runner fixtures are marked `TEST_ONLY_FAKE_RUNNER_NOT_AI`.

## Licensing gate

Piper's archived `rhasspy/piper` project lists MIT software licensing, while maintained `OHF-Voice/piper1-gpl` uses GPLv3. Voice models have **separate licenses** and may restrict commercial use. Check exact engine dependencies, executable distribution, model card, trained-voice consent and phonemizer license for the specific pinned versions. Do not infer that MIT on an old repository makes a newer packaged binary permissive or that any model is commercial-use cleared.

References:
- https://github.com/rhasspy/piper/blob/master/LICENSE.md
- https://github.com/OHF-Voice/piper1-gpl
- https://github.com/OHF-Voice/piper1-gpl/discussions/30

## Acceptance (not yet achieved)

1. Approved private host, egress-denied container, executable/engine digest and pinned voice model/config plus a documented commercial-use decision.
2. Independent signed human authorization binding approved text, voice identity, consent records, model/license hashes, intended use and time window; **the adapter does not yet cryptographically verify these signatures**.
3. Actual speech inference recording and independently verified process identity/runtime evidence, output WAV duration/format, SHA-256 receipt and sample integrity.
4. Listener-based language accuracy, intelligibility, prosody, pronunciation, clipping, speaker identity and accessibility review. Transcription or ASR consistency may supplement, not replace listening.
5. Signed independent post-output human safety, rights and voice-consent review bound to exact output hash. Keep output quarantined; release and publishing are separate decisions.
6. Only then connect narration assets to PR #94 cinematic finishing; retain separate CI and operational gates.

This draft is stacked on **PR #95** and must not merge directly into main before its prerequisite passes review. No hosting, subscriptions, customer use, deployment or publishing. Phase 01 (3/9) and Phase 02/03 operational NO-GO remain.

## P2-04q acceptance hardening — 17 October 2026

**Actual result remains HOLD / NOT PROVEN.** In the available execution environment, `ffmpeg` and `ffprobe` are present, but no Piper executable, ONNX runtime, local approved voice checkpoint, or independent human signatures are available. Do not mark this as a genuine generated voice demonstration.

### Engineering source changes

- `creative_speech_authorization.py` checks two distinct Ed25519 signatures (OWNER + REVIEWER), expiration of at most 30 minutes and immutable binding to the job, approved text, ONNX model hash, config, executable, license evidence, rights and consent claims. These must be supplied for any **real** inference. Synthetic injected runners never claim genuine synthesis.
- `creative_speech_offline.py` requires an owner-executable pinned binary (private 0700), rather than impossible non-executable 0600 file permissions; it retains isolated execution and signed-review gating, and stores a private evidence record. A valid operator flag does **not** prove kernel/container egress isolation.
- `creative_audio_assets.py` permits native 22,050 Hz 16-bit PCM for speech and reasonable variation between target duration and synthesized utterance duration; music/SFX retain stricter default length/rate behavior. Output peak and RMS checks cannot establish naturalness or correct pronunciation.
- `creative_speech_final_review.py` checks a separate independent Ed25519 human signature over final audio SHA-256, bound job digest, safety evidence, transcript review, voice-consent/rights declarations, and expiring review. This authenticates a *human claim*, not legal rights, a scanner run, or independent proof a neural model executed. Final media remains privately quarantined.
- Dedicated source and adversarial tests exist; CI status must be assessed for the latest branch head. All synthetic WAV fixtures are non-AI test data.

### Model shortlist — NOT authorized for commercial use yet

The Piper `en_US-libritts-high` model card documents **CC BY 4.0 training data** and training from scratch on LibriTTS train-clean-360. This is a better *candidate for further diligence* than `en_US-lessac-medium`, which references the Blizzard 2013 dataset license. The LibriTTS voice is multi-speaker; assess speaker-specific likeness and provenance. Do not treat a dataset licence alone as proof that the model, voice identity and executable distribution are all commercially cleared.

- Model card: https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/libritts/high/MODEL_CARD
- Alternative lessac voice model card: https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/lessac/medium/MODEL_CARD
- Maintained Piper engine: https://github.com/OHF-Voice/piper1-gpl (GPL-3.0; separate runtime redistribution and model-card review)

### Exact acceptance package required

1. License approval for the **specific** model, dataset, selected speaker and pinned engine binary/dependencies, including attribution/redistribution requirements.
2. Real private local ONNX model and JSON configuration, pinned executable hash and container/host no-egress evidence.
3. Time-limited, independent cryptographically signed pre-generation authorization, with consent/rights records bound to text and model hashes.
4. Observed actual Piper model process and successful private WAV file, with trusted console/runtime attestation, model/config hashes, output SHA-256 and `verify_asset` technical report.
5. Independent listener report showing the exact prompt spoken understandably, language/accent/pronunciation quality, no unexpected words or artifacts, and checked safety/voice consent.
6. Independent signed output review bound to the final WAV and transcript evidence, with **NO** distribution authorization.

**Acceptance decision: NOT VERIFIED** until all six records exist. No live API, customer activation, subscriptions or publication; Phase 01 remains 3/9 and Phase 02/03 remain operational NO-GO.

## Engine compatibility blocker (verified from upstream release notes)

The maintained `OHF-Voice/piper1-gpl` v1.3.0 changed the Python synthesis API and command-line interface. The P2-04q adapter currently assumes an older executable calling convention (`--model`, `--config`, `--output_file` plus stdin). It must NOT be pointed at an arbitrary current Piper binary or deployed based on the `piper` filename alone. An approved, exact version/binary SHA and offline CLI smoke test are prerequisites. A future implementation should select a versioned adapter, verify a CLI invocation under actual pinned runtime and record GPL compliance plus model/voice-specific permission before any genuine voice proof is marked accepted.

Official engine release notes: https://github.com/OHF-Voice/piper1-gpl/releases


## Reproducible local source-test evidence (GitHub Actions blocked)

A new **source-only** executable recipe is included at
\`scripts/verify_p2_04q_local_gate.py\`. It is appropriate for an authorized
developer checkout (such as the Kali workstation), and does **not** run Piper,
download any model, sign a review, override release requirements or replace
GitHub's required branch-protection checks.

Example (replace the expected SHA with the precise reviewed GitHub PR #97 head,
not an arbitrary local HEAD):

\`\`\`bash
cd ~/MetaAutomate
git fetch origin feature/p2-04q-offline-speech-worker
git checkout feature/p2-04q-offline-speech-worker
mkdir -m 700 -p "$HOME/.local/share/metaautomate/speech-evidence"
PYTHONPATH=apps/api python scripts/verify_p2_04q_local_gate.py \
  --repo-root "$PWD" \
  --expected-sha "<EXACT_REVIEWED_40_CHARACTER_COMMIT_SHA>" \
  --evidence-dir "$HOME/.local/share/metaautomate/speech-evidence"
\`\`\`

Prerequisites: locally installed pytest, cryptography and standard Python.
The gate enforces a matching exact clean Git checkout; invokes only the seven
source-test files with speech-gate activation environment variables stripped;
stores 0600 log/JSON evidence in a 0700 directory; captures test-file hashes,
Python version and platform; and always reports
\`real_piper_inference_verified: false\`,
\`signed_human_review_observed: false\`, and
\`github_required_checks_satisfied: false\`.
Any missing test or failed assertion returns exit code 2. The runner harness
was separately exercised on a disposable test-fixture Git repository; this
does **not** mean the real private MetaAutomate source suite has passed.

A separate local eSpeak smoke WAV may confirm 22.05kHz/PCM writing without
demonstrating neural inference. Do not call an eSpeak sample Piper evidence or
use it to clear a voice model's separate licensing gate.

### GitHub Actions incident record

Repository issue #100 contains direct evidence: even the dedicated one-line
\`echo RUNNER_STEP_EXECUTED\` Actions job failed with no steps on two attempts.
Recent P2-04q runs likewise failed with no steps and unavailable log blobs.
Root cause remains unknown; private-repo Actions quota, account trust controls,
runner provisioning and GitHub incident status require owner-side
verification. Do not add payment information or override branch protection
automatically.

### Neural voice model stage — still pending

The specific \`en_US-libritts-high\` candidate is a ~137MB ONNX model hosted
under the rhasspy/piper-voices catalogue; download only when its speaker and
dataset rights, model card, required attribution, engine license and execution
environment have been independently reviewed. Stage the model in a private
offline host, pin exact version/SHA and run one short original narration.
Ensure the reviewed Piper CLI version matches the adapter's
\`--model/--config/--output_file\` invocation. A model directory listing or
software license does not alone certify voice identity or commercial usage.

**Acceptance remains HOLD** until the real neural WAV, observed process,
independent signature, waveform and listener-quality review all exist.
