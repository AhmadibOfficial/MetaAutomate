# P2-04t — Unified Image + Video + Voice Creative Studio

## Product goal

**Create an image, narrate a video, or produce both from one original idea.**

The eventual MetaAutomate Creative Studio is designed to support a wide creative range: realistic photography, product advertising, editorial illustrations, animated storyboards, 3D art, educational graphics, documentary visuals, social media, short film, architectural concepts, and more. Free-form visual style and narration direction are retained as creator prompts. The platform **cannot** claim literally every conceivable output is supported, guaranteed safe, legal, or producible by one model.

Users should ultimately receive:
- stand-alone downloadable images in appropriate native sizes/formats;
- short model-generated visual clips, each with disclosed actual native model resolution;
- human-reviewable spoken narration, captions and optional licensed music/SFX;
- Full HD **finished composition**, 1920×1080 at 30 fps, AAC narration and embedded subtitles;
- manifest hashes, rights/consent records and independent output approvals before any distribution.

These are PRODUCT TARGETS. Current acceptance status does **not** certify neural image, video or speech inference or customer availability.

## Engineering increment implemented in draft PR #101 (stacked on PR #94)

1. **Source-only project planner** — \`apps/api/app/creative_multimodal_project_router.py\` takes \`idea\`, visual style, canvas ratio (1:1, 4:5, 9:16, 16:9, 3:2, 2:3, 21:9), output types (\`images\`, \`narrated_video\` or both), counts, scene durations, voice language/style and narration text. It creates bounded jobs for independently authorized image, clip and offline speech workers. Long narration is divided into 700-character jobs without dropping words.
2. **Controlled private composer** — \`apps/api/app/creative_multimodal_studio.py\` accepts 4–24 reviewed PNG stills and/or locally verified silent MP4 clips, 30–120s total, plus one PCM16 WAV voice track (including native Piper 22.05kHz, plus 44.1/48kHz) and one timed SRT subtitle file. Verifies bounded private file paths, exact SHA-256, source dimensions, human rights *declarations*, codec/timing metadata, no unexpected source audio or subtitles, and source/voice permissions. Converts stills and clips to a 1920×1080/30fps silent film with deterministic aspect-fit padding, then muxes voice and subtitles with FFmpeg into a private MP4. Rechecks final dimensions, codec, duration and audio/subtitle streams, writing a SHA-256 receipt with release state **QUARANTINED_PENDING_INDEPENDENT_FINAL_REVIEW**.
3. **Source tests** — source rejection, malformed names, symlinks, tampering, unsupported formats, missing rights/consent and false distribution claims. An explicitly opt-in CPU-intensive 32-second synthetic FFmpeg integration test is included. The fixtures are not AI generated.

There is no external model download or generation in this PR. The existing local Diffusers image/video worker (PR #94) and Piper speech adapter (PR #97, stacked separately on PR #95) remain **independently authorized** and unmerged. This increment cannot import or call the parked Piper model worker yet.

## Important quality limits

- The current native model video worker is constrained to **576×320, 8fps and 2–8s**. 1080p finishing is a composition/transcode, **not native neural 1080p generation**.
- The current native image worker is bounded to <=768px sides; the planner's aspect-ratio vocabulary is a goal. Output size/style is subject to an explicitly approved model's real resolution and limits.
- The composer can make video using static image scenes and/or short MP4 clips; a static shot is **not** a neural animation.
- FFmpeg will contain audio and subtitles when source WAV/SRT are present, but it does not verify that the voice literally pronounces the script, voice consent is authentic, lip movements align, music rights exist, or cinematic quality meets professional standards.
- A checked \`human_rights_reviewed\` flag and a 64-hex evidence reference are **claims**, not cryptographically authenticated records. The final media requires a separately independent signed review bound to its exact SHA-256 using the existing final review architecture.
- Image, video and speech synthesis require independently licensed checkpoints, legal rights to data/likeness/voice, and a verified network-denied, budget-controlled runtime. Do not offer universal voice cloning or unrestricted copyrighted/impersonation output.
- No arbitrary URL downloads, public API, paid AI calls, customer data access, social scheduling or auto-publication.

## Proof ladder

| Step | Actual acceptance requirement | Status |
|---|---|---|
| Source planner for mixed creative idea | Bound and safe multimodal job routing | Added in source |
| Technical offline FFmpeg composition | Verified 1080p H.264/AAC/mov_text media after local conversion | FFmpeg command-only 1s synthetic smoke test passed; actual 32s module test remains unverified |
| Image generation | Real model execution, approved checkpoint and independent output evidence | Not verified |
| AI short-video generation | Real licensed short video clip with source SHA and rights review | Not verified |
| Neural voice generation | Actual Piper inference, model provenance and independent human pronunciation/consent review | Not verified, PR #97 draft |
| End-to-end 30–120s AI production | Genuine source images/clips/voice, final asset integrity, human release approval | Not verified |
| Longer films | Scene consistency, licensed soundtrack, resumable render and measured runtime | Future |

## Test and private source operation

Source-only tests:
\`\`\`bash
PYTHONPATH=apps/api pytest -q \
  tests/test_p2_04t_multimodal_router.py \
  tests/test_p2_04t_multimodal_studio.py
\`\`\`

Optional (CPU-intensive) 32-second all-synthetic Full HD render:
\`\`\`bash
MAT_RUN_SLOW_MULTIMODAL_FFMPEG_TESTS=1 \
PYTHONPATH=apps/api pytest -q \
  tests/test_p2_04t_multimodal_studio.py::test_synthetic_full_hd_video_with_voice_and_captions
\`\`\`

Actual private \`render(manifest,asset_root,quarantine_root)\` requires
\`MAT_CREATIVE_MULTIMODAL_OFFLINE_ENABLED=1\` and
\`MAT_CREATIVE_NETWORK_ISOLATED=1\` inside independently enforced offline media-processing sandbox. **Environment flags do not themselves provide network isolation.**

No user media or external subscriptions were activated. PR #94 and PR #97 remain separate gated dependencies; operational Phase 01 verification 3/9 and Phase 02/03 NO-GO remain in force. GitHub Actions startup issue #100 blocks release evidence.

## Verification note

The actual FFmpeg command pattern (not the full MetaAutomate repository module) was exercised on a separate local synthetic 1-second image/WAV/SRT sample. FFprobe showed one 1920×1080@30fps H.264 stream, one AAC audio stream and one `mov_text` subtitle stream. This verifies technical feasibility of FFmpeg muxing, **not** the full 30–120-second project test and **not** neural image/video/voice generation. The latest targeted PR CI failed, consistent with the unresolved zero-step GitHub Actions runner infrastructure incident #100. No passing exact-commit repository tests can be claimed.

## Current generation-worker compatibility

The project router enforces <=450 characters for an idea and <=120 for the visual-style direction so composed generation prompts fit the currently allowlisted worker's 700-character prompt field. Requested native AI clip jobs are limited to **2–8 integer seconds** (16–64 frames at 8 fps). The video editor can *hold* an already-licensed still or clip in a 2–15-second scene, but that edit is not proof of native 15-second neural video generation. There is no existing universal model registry, so requests for styles, resolutions or modalities unsupported by reviewed local models must remain in a capability/pending state, not be fabricated as generated outputs.
