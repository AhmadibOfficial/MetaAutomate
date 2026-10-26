# P2-04g cinematic production — gated first increment

This phase adds an **offline manifest preflight**, not a functioning narrator, mixer, synchronizer, film render, or full distribution pipeline.

The validator `apps/api/app/creative_cinematic_preflight.py` accepts a bounded 30–120-second timeline of locally stored narration/dialogue/music WAV tracks and SRT caption assets. It checks exact SHA-256 bytes, filenames, lengths declared in the manifest, evidence-reference presence, human review declarations, and music gain ceiling. **Those declarations are not independently authenticated evidence.** It returns `PREFLIGHT_ONLY_NOT_RENDERED` with publication and final approval false.

Important: It does **not** parse SRT timing, inspect WAV encoding, independently inspect rights/consent, check actual audio duration, verify clipping/loudness, mix audio, render a film or sign a final review. Code/CI tests cannot stand in for a real output.

Next engineering implementation gates:
1. Reverify PR #94 at the latest commit; green CI is necessary but insufficient for real video acceptance.
2. Obtain licensed offline checkpoints and independently observe one real image + 2–8-second video with signed job/rights/safety receipts; do not falsely mark done from fixtures.
3. Implement strict file signature and ffprobe/ffmpeg validation for WAV and SRT files; enforce captions syntax, actual timing, channel layout, duration, loudness, A/V alignment and source licences.
4. Build a separate bounded offline FFmpeg audio/caption composer joining the verified 30–120s *video*, the preflighted tracks, and subtitles. Never use shell invocation or network inputs.
5. Verify the **final** composed media digest, its audio/subtitle tracks, exact duration, continuity, safety/rights evidence and independent human sign-off. Keep it quarantined after review pending separate release authorization.
6. Only then stage five-minute and longer film designs with chapters, character continuity, batch resumability, cost budgets and final-output re-review.

No active subscription or paid inference is authorized. Phase 01 remains 3/9 verified, Phase 02/03 live operation remains NO-GO. PR #94 remains draft, unmerged and not deployed.
