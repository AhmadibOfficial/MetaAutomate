# P2-04h — Offline cinematic finishing (30–120 seconds)

## Implemented (source, NOT an operational release)

- \`apps/api/app/creative_cinematic_render.py\` accepts a preflighted P2-04g manifest, a **silent** source MP4 (1920x1080, 30fps, 30–120 seconds), authorized WAV narration/dialogue/music and precisely one SRT subtitles file.
- Fails closed for unsafe file paths, file hashes, group/world readable inputs, incorrect WAV encoding or actual duration, invalid SRT structure/timing, missing human declarations, source-stream mismatch and unapproved publication flags.
- Muxes video with PCM WAV tracks using FFmpeg audio mixing, gain/delay/limiter, AAC and embedded \`mov_text\` subtitles. Keeps the input video bitstream, and never represents an upscaled 1080p source as native AI 1080p.
- Reprobes final resolution/fps/audio/subtitle codec and whole-file duration, writes a receipt with output digest in a randomly named private 0700 quarantine directory; all media 0600.
- Uses argument-array subprocesses, bounded timeouts and locally verified files, without URLs, model downloads, network requests, publishing APIs or automatically authorizing rights. Operator MUST independently enforce network egress denial at host/container boundary. Setting \`MAT_CREATIVE_NETWORK_ISOLATED\` is only an attestation, not actual network isolation.

**Explicit limitations:** render does NOT independently verify licence terms, likeness consent, semantic caption alignment, perceptual audio intelligibility, video flicker, accessible sound mix, true AI inference or independent human approval. Signed approval of the *final film hash* remains a separate outstanding control.

## Operation (private, authorized environment only)

Prerequisites: Python environment supporting P2-04g and P2-04h, local FFmpeg/FFprobe, permissions on private inputs, no-egress GPU/audio isolation, required reviews. Reference assets must not contain confidential content intended for GitHub or CI.

1. Render silent P2-04f video privately (or supply equivalent locally inspected full-HD 30 fps silent MP4) and record actual SHA-256. Copy into a private trusted asset root with mode 0600.
2. Prepare P2-04g JSON manifest containing \`schema_version, project_id, runtime_seconds, tracks, scene_continuity_reviewed=true, final_human_approval=false, publication_authorized=false\`. Each WAV track and SRT asset must carry its digest, human rights-review declarations, evidence hashes, start and duration fields. Human flags remain **claims**, not cryptographic proof.
3. Verify real input file digests and explicit review records separately.
4. In the isolated private runtime, opt in to local render only:
   \`\`\`bash
   export MAT_CREATIVE_CINEMATIC_RENDER_ENABLED=1
   export MAT_CREATIVE_NETWORK_ISOLATED=1
   PYTHONPATH=apps/api python -m app.creative_cinematic_render \
     --manifest /private/film-manifest.json \
     --assets /private/film-assets \
     --quarantine /private/quarantine \
     --video-name silent.mp4 \
     --video-sha256 <64-character-verified-digest>
   \`\`\`
   Example placeholders above are not executable release authorizations.
5. Confirm receipt, output SHA-256 and independent ffprobe output. Human specialist must inspect soundtrack mix, voice clarity, captions, final composition, accessibility, safety and rights. Sign a **separate** final approval binding the exact final SHA-256, then use `app.creative_cinematic_final_review.inspect_final` to verify the reviewer's Ed25519 signature, independent identity, receipt binding, output digest and review expiry. It produces **HUMAN_REVIEW_CLAIM_RECORDED_PENDING_SEPARATE_RELEASE**, not publication clearance. Do not equate the preflight checkboxes or the signature alone with independent rights authentication.
6. Keep final media in private quarantine. Public serving, distribution, customer activations and subscriptions remain blocked.

## Acceptance

| Requirement | Status |
|---|---|
| Source-only timeline/audio/subtitle rendering code | Implemented, pending current CI |
| Synthetic 30s FFmpeg test footage | CI test added; entirely synthetic and not model output |
| Real AI image and 2–8-second video inference | NOT VERIFIED |
| Real 30–120s user-relevant cinematic output | NOT VERIFIED |
| Independently signed final-output review validator | Implemented in source; no authentic signed real-output review conducted |
| Five-minute and feature-film capability | Not implemented |

P2-04g preflight declarations do not by themselves establish that the input assets were licensed or that review occurred. This milestone remains **draft, unmerged, no deployment, no subscriptions, Phase 01 3/9 and Phase 02/03 operational NO-GO**.

## Latest CI limitation

The previous PR #94 head `154466807449b1a719b30c3f0457222940d475bb` passed the main and creative-workbench CI. The subsequent cinematic-render commits triggered multiple GitHub Actions workflow failures whose job records did not include steps, and the job logs could not be retrieved. **Latest source tests and the 30-second synthetic integration fixture are not verified passing in GitHub CI.** Separately, a *2-second local FFmpeg command-only smoke test* (not the repository module) demonstrated muxing video + AAC + mov_text captions successfully. Neither constitutes evidence of genuine model generation, full 30-second pipeline acceptance, or rights clearance.
