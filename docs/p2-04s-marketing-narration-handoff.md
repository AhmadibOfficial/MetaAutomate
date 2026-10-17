# P2-04s — Private Marketing → Narration → Creative Studio handoff

## What is built

Source-only \`app.marketing_creative_studio_handoff\` composes:
1. A validated eight-category marketing campaign work order from **draft PR #98**.
2. A human-checked script draft with exact SHA-256, work-order ID, source-claim references and review-claim digest.
3. An optional private PCM16 WAV attachment (22.05/44.1/48kHz, max ten minutes) with exact SHA-256, bounded duration and separately referenced speech job and independent review digests.

Output always says \`AUDIO_INTEGRITY_ONLY_INFERENCE_AND_REVIEW_NOT_VERIFIED\`. Claim hashes are **not** signature or genuine AI inference validation. Media remains private and no scheduling, sending or publishing interfaces exist.

**P2-04q speech worker PR #97 is currently stacked on PR #95 and not merged.** This interface therefore does *not* directly import or call the not-yet-merged speech adapter, pretend that Piper produced a voice, or claim the bridge authenticates independent signatures.

## Integration gate after PRs #95, #97 and #98 are source-tested and merged

- Match marketing script hash to the exact authorized job text hash in P2-04q.
- Verify the pre-inference pair of Ed25519 authorizations (owner + independent reviewer), license/consent evidence and pinned Piper executable/model config.
- Observe a real local model subprocess in a network-denied runtime; validate 22.05kHz/native WAV and independently signed post-output review.
- Bind source work order, script, verified WAV, model and license evidence, audience, platform and final publication constraints into an immutable production manifest.
- Attach narration to P2-04h cinematic finishing only after genuine short-video input is separately proven. Include branded subtitles and an accessible mix; do not auto-publish.
- Verify a final render's audio/video/caption quality, rights and reviewer signatures against exact final file SHA.

## GitHub Actions failure diagnosis

Recent private MetaAutomate Actions jobs repeatedly failed **before reporting even one step**. The jobs return no step metadata and GitHub's log storage replies \`BlobNotFound\`. Retries also failed. This is an **execution/provisioning or account-level** blocker, not confirmed source assertion failures.

Investigate without paid subscriptions:
1. Visit repository **Settings → Actions → General** and verify the required actions/runners are enabled and policy allows the expected job type.
2. In GitHub account/org **Billing and licensing → Usage**, inspect remaining private-repository Actions minutes, spending cap, warnings or suspension. **Do not add billing or raise spending limits without a separate cost decision.**
3. Inspect failed-run annotations and GitHub Status for runner incidents; the runner may not have provisioned.
4. If all unrelated workflows still report no steps, raise GitHub Support using the exact workflow and job IDs, including that zero steps and \`BlobNotFound\` occur even after re-run.
5. Until runners work, use a locally authorized test workstation to run the same tests and retain their machine identity, Python/package versions, command, SHA-256 of repository commit and signed logs. Local tests are not equivalent to GitHub required checks.

Acceptance stays **NO-GO** for merged execution and deployment until the exact-commit tests, genuine speech, license review, signed human output evidence and operational security gates are satisfied.

No paid subscriptions, customer media, cloud changes, credentials, public model access, publishing or customer activation.
