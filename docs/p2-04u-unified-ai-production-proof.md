# P2-04u — Unified AI Image, Short-Video and Neural Narration Proof Chain

## Goal and truthful position

Prove one **genuine** image, one **genuine short AI video**, and one **genuine neural voice narration** from specifically licensed, pinned offline model runtimes, then assemble a reviewed 30–120-second narrated film in the existing P2-04t Full HD editor.

**Current status: source-level adapter and verification tests only. No real model checkpoint was installed or executed, no signed independent human review was supplied, and no finished production may be called genuinely AI-generated.**

The new \`creative_multimodal_provenance.py\` coordinates independent worker evidence. It requires a local PNG image, an MP4 short clip, and a WAV voice sample, each identified in the existing production manifest. For each input it requires:
1. A source worker receipt with a constrained mode and private/quarantined state:
   - Images/video: \`LOCAL_DIFFUSERS_REAL_INFERENCE\`, \`QUARANTINED_PENDING_INDEPENDENT_SAFETY_REVIEW\`, matching \`output_kind\`, \`output_sha256\`, \`job_sha256\`, \`model_tree_sha256\`, and signed authorization digest.
   - Speech: \`OPERATOR_ATTESTED_LOCAL_MODEL\`, \`QUARANTINED_PENDING_INDEPENDENT_REVIEW\`, matching WAV digest, job and model checkpoint hash. **A Piper receipt by itself has not cryptographically proved the owner's earlier authorization:** PR #97 and #95 remain dependencies.
2. An independently registered Ed25519 reviewer's signed record bound to the source receipt SHA-256, exact media SHA-256, job/model/authorization digests and an externally obtained observed-execution log SHA-256.
3. Review declarations for source-model execution observation, technical quality, licence, rights and consent, each explicitly true before **technical composition**, and a bounded 24-hour signature validity window.
4. No released or publicly distributed source artifacts.

**The signed human statements are authenticated claims.** A model can be spoofed if a signer lies or its signing key is compromised. This module does not independently reproduce an observed process, validate the legal meaning of a model licence, authenticate a person's real-world identity, inspect actual consent documents, detect false provenance, or verify that narration says the exact words. Therefore **\`inference_independently_verified_by_code\` remains false even after every signature passes**. Real source proof must involve a separate trusted observer and review of actual execution records.

The optional \`render_with_source_proofs\` calls P2-04t's quarantined FFmpeg composer only if all source receipt/signature checks pass. The composer emits a Full HD 1920×1080 MP4 with AAC narration and timed \`mov_text\` subtitles, but **not** a public or already approved film. P2-04h's separate final-signature and media-review process is still required.

## Operating sequence — when a licensed local runtime exists

1. Use a **private, unprivileged network-denied** Linux host/container; pin the exact source revision and dependency versions; never download models at execution time.
2. **Image:** review and stage safetensors checkpoint, licence and any recognizable likeness rights; run existing P2-04c local image worker with an independently signed job. Verify output in P2-04d and retain receipt.
3. **Short video:** review and stage separately licensed short-video model; run 16–64 frames at 576×320 and 8 fps (2–8 seconds) under the real allowlisted worker. Repeat per shot. Review native detail, flicker, continuity, faces and artifacts; retain receipts and logs. Do not claim native Full HD AI motion.
4. **Speech:** stage approved Piper engine, ONNX checkpoint and configuration; use PR #97's three-party signed preflight with owner + two independently registered reviewers and actual no-egress isolation. Generate WAV, verify its PCM16/audio hash and document accurate transcript, pronunciation, language and consent. A 22.05kHz voice can be upsampled at finishing but that is not evidence of superior native audio.
5. **Review:** registered independent human witnesses each source execution and reviews actual model cards, licence/voice consents and media. Hash the actual execution logs and record an Ed25519-signed review bound to the source receipt/model/job/output.
6. **Compose:** stage reviewed PNG/MP4/WAV and SRT in owner-only directories. Use P2-04u operator gate to validate exact Git SHA, source manifest, signed reviews and media files. The gate can run in verify-only mode; **render mode** additionally requires the offline output flags and actual isolated FFmpeg sandbox.
7. **Final production:** visually/audibly review the entire 30–120 second film for scene continuity, narration accuracy, subtitle sync, intelligibility and safety. Sign its final exact SHA-256 using P2-04h independent final-review workflow. Customer release requires a **separate** authorization.

### Operator source evidence command (example)

\`\`\`bash
cd /private/MetaAutomate
export PYTHONPATH="$PWD/apps/api"
python -m app.creative_multimodal_operator \
  --repo-root "$PWD" \
  --expected-commit "<EXACT_REVIEWED_PR_SHA>" \
  --manifest /private/creative-assets/production-manifest.json \
  --source-evidence /private/creative-assets/source-proofs.json \
  --trusted-reviewer-keys /private/trust/registered-reviewers.json \
  --assets /private/creative-assets \
  --quarantine /private/production-quarantine
\`\`\`

Only after it succeeds, in an approved network-isolated media processing runtime, add \`--render\` and the existing \`MAT_CREATIVE_MULTIMODAL_OFFLINE_ENABLED=1\` / \`MAT_CREATIVE_NETWORK_ISOLATED=1\` flags. Environment flags do not create network isolation.

The key registry must have been maintained outside the producer's control. Evidence files need owner-only (0600) mode. **Do not create reviewer private keys in scripts, upload them to GitHub or use fake signers as actual proof.**

## Candidate checkpoint research (not a clearance decision)

- Image: [Stability AI SDXL base 1.0](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0), with CreativeML Open RAIL++-M licence and usage restrictions; need exact version, rights, third-party weights and GPU suitability review.
- Video: **no model selected or legally approved**. The present \`TextToVideoSDPipeline\` implementation is fixed to 576×320, 8fps and 16–64 frames. Model availability and licences need independently checked per selected checkpoint.
- Speech: [Piper LibriTTS high](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/libritts/high/MODEL_CARD) cites LibriTTS train-clean-360 under CC BY 4.0, 22.05 kHz and many speakers. Rights per identifiable speaker, required attribution, precise checkpoint and Piper binary/dependency licence are *not* commercially approved merely because the model card shows that dataset licence.

## Acceptance table

| Stage | Evidence required | Current status |
|---|---|---|
| Signed unified image+video+voice source chain | Real source receipt, output SHA-256 and registered human witnessed execution signature for every source | Contract source written; tests not verified passing |
| Actual image GPU inference | Authorized installed checkpoint, genuine image and observed process | Not demonstrated |
| Actual short-video GPU inference | Authorized installed checkpoint, genuine video and observed process | Not demonstrated |
| Actual Piper voice inference | Approved ONNX, spoken WAV, consent and three-party signed preflight | Not demonstrated |
| Complete narrated 30–120s composition | Full HD asset with synchronized audio/subtitles, native source provenance and final signed quality review | Not demonstrated |
| Github CI | Green required checks at exact reviewed head | Blocked: issue #100, runners failing without executed steps |
| Publishing and billing | Separate security and production authorization | Disabled |

## Dependencies and boundaries

This PR is stacked on **draft PR #101**, itself stacked on **draft PR #94**. Speech source dependency **draft PR #97** is stacked on **draft PR #95**, which remains separate and unmerged. This proof gate consumes the externally generated speech receipt rather than importing the unmerged speech module. Do not merge only this stacked integration to main while its prerequisites are unverified.

No DigitalOcean/Render changes, installed checkpoints, subscription payments, social publishing, network downloads, customer activation, production customer data or deployment.


## Independent 32-second **non-neural** technical media sample — 17 Oct 2026

A separate local FFmpeg + Pillow + eSpeak command-only smoke production
created a 32.000-second MP4 from **four manually designed static image
storyboards**, four eSpeak speech clips and four SRT cues.

- Filename: \`metaautomate_32s_technical_production_demo.mp4\`
- SHA-256: \`9d79a127e9fd30a0fe6d6682664ddcad42df46495ca967d733420823169856a0\`
- File bytes: \`925023\`
- Verified by local ffprobe: H.264 1920×1080 30/1 fps, AAC stereo 48 kHz,
  and one \`mov_text\` subtitle stream.
- The visual frames explicitly state **TECHNICAL DEMO • SYNTHETIC VISUALS •
  ESPEAK NON-NEURAL VOICE**.
- The rendered file and JSON technical receipt were delivered privately to
  the requester as conversation artifacts; not committed as a public
  portfolio/video release.

**This was NOT a run of the full P2-04u repository module.** It does not
satisfy image Diffusers checkpoint inference, short video model inference,
Piper neural synthesis, model licensing, independent human voice listening,
real process proof or final media signed review. It demonstrates a working
offline multi-track video/audio/subtitle command pattern only.

The P2-04u GitHub Actions source workflow run \`39005461061\` failed **with
\`steps: null\`**, consistent with infrastructure issue #100; it did not
establish failing Python assertions or a successful test run. All source
milestones therefore remain review-only, not releasable.


### Video checkpoint licensing blocker found during research

The commonly referenced \`ali-vilab/text-to-video-ms-1.7b\`
(\`TextToVideoSDPipeline\`) model card describes its use as research-oriented
and its model-details section lists **CC BY-NC-ND**. Its YAML header displays
\`cc-by-nc-4.0\`, which is inconsistent but also **noncommercial**. Neither
version establishes permission to use the model weights in a paid or
customer-facing MetaAutomate creative generation product. The Apache-2.0
licence of the *ModelScope code library* is a different licence and does
not override the model checkpoint's terms.

Do **not** automatically select or download this model as MetaAutomate's
commercial film-generation engine. A separate checkpoint with demonstrated
commercial rights, safety obligations and a compatible offline pipeline must
be reviewed before authentic AI video acceptance.

Source: https://huggingface.co/ali-vilab/text-to-video-ms-1.7b
