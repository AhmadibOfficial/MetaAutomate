# P2-04p — MetaAutomate Unified AI Creative Studio: audio asset foundation

## Vision and product language

**One creative workflow, from idea to complete production.**
MetaAutomate aspires to support expressive AI-generated speech, original music across genres, immersive sound effects, images, and cinematic video. Intended projects: films, advertisements, brand campaigns, short social videos, audiobooks, podcasts and educational media.

**Do not claim speech/music/SFX inference, commercial availability, voice cloning, unlimited genre support, or film-length generation is implemented.** This PR implements a small source-only contract and local PCM verifier. No voice/music/sound-effects weights, GPUs, provider keys, subscriptions, or real model inference are included.

## New technical boundary

\`apps/api/app/creative_audio_assets.py\` exposes:
- \`validate_job(job)\`: a strict bounded 1–600-second asset specification for speech, music or sound effects, with project/asset identity, intended use, language, genre/style direction, model checkpoint hash, licence evidence references, content rights, authorization digest and explicit publication HOLD.
- Voice-likeness requests require a declared consent evidence digest. Artist-referenced music requires a declared rights digest. **A digest alone is not proof of authenticity or authorization.** Independent review of the actual record is still mandatory.
- \`verify_asset(job, receipt, private_wav)\`: verifies private 16-bit PCM WAV at 44.1/48 kHz, 1–2 channels, actual frame count and duration, raw sample metrics, file SHA-256, request hash and exact receipt binding. This rejects synthetic silence, invalid media, tampering, unauthorized distribution claims and obvious bad permissions.
- The verifier always reports \`model_inference_independently_verified: false\`, \`content_safety_verified: false\`, \`human_final_reviewed: false\`, and \`published: false\`. An operator receipt marked \`OPERATOR_ATTESTED_LOCAL_MODEL\` is not independent evidence.

## User-facing product workflow (future)

1. **Create:** Select Film, Ad, Campaign, Social, Audiobook or Podcast.
2. **Direct:** Describe the idea, audience, language, script, pacing and musical/sound direction.
3. **Produce:** Request stills, clips, speech, background score and effects from *approved* generation workers (not implemented by P2-04p).
4. **Arrange:** Combine assets using the offline short-video composer in draft PR #94 after it is independently validated.
5. **Verify:** Check checkpoint licence, prompts and rights, speaker consent, output hashes, audio metrics, voice intelligibility, subtitle alignment and accessibility with independent human review.
6. **Approve:** Explicit final approval against exact final deliverable hash; retain private quarantine until a separate release decision.

## Roadmap integration

- **P2-04i (existing gate):** Genuine licensed AI image + short-video inference, independently evidenced end-to-end. This remains the prerequisite for truthful AI video claims.
- **P2-04p (this PR):** Offline speech/music/SFX plans and output integrity verification, independent of PR #94, no live generation.
- **Next audio increment:** Separate offline, checkpoint/license allowlisted speech and music/SFX model adapters, explicit signed job approvals, controlled compute/cost ceilings, qualified content/rights screening, real output demonstration and independent human approval.
- **Cinematic finishing:** Later connect reviewed WAV narration/music/SFX to P2-04h, improving actual loudness/ducking, subtitles, continuous multi-scene audio and human-quality checks.
- **Films and subscriptions:** 5-minute, 10–30-minute and 30–120-minute aspirations remain gated by actual film delivery reliability and cost evidence. No subscription may advertise unsupported output durations.

## Operational release boundaries

No model downloads, network execution, deployment, customer data, customer activation, billing, publishing, live product API or migration. No cloud purchase. Existing Phase 01 3/9, Phase 02/03 operational NO-GO and PR #94 draft restrictions remain.

The unit tests use a **synthetic sine-wave PCM fixture**, not AI audio. Their success proves only that the contract and verifier operate in those test conditions.
