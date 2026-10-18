# P2-050 — Functional Creative Studio Release

## Implemented

- Removed the rejected **Download recent AI conversation** and **one-time private project transfer** controls and deleted their storage module, obsolete tests and documentation.
- Start a Project now offers useful on-device AI text tasks (product description, marketing message, workflow and video script) and **Copy latest answer**. Real Qwen/WebLLM inference is still device-dependent and not verified for all browsers.
- Creative Workbench creates original text-and-shape images at **1080×1080**, **1080×1920**, and **1920×1080** with native Canvas and downloads genuine PNG. No generative image model is claimed.
- Creative Workbench can create WebM video at **1280×720** or **720×1280** with 30–120 seconds of **user-owned WAV/MP3 narration** via CanvasCaptureMediaStream + Web Audio + MediaRecorder. Playback preview and audible-sample threshold precede export. No cloned, neural or server-generated voice is claimed; no upload.
- Advanced video scoping/rights form is collapsed rather than promoted as a primary deliverable. The original rights, consent and review HOLD checks remain intact.
- Homepage and Services link to the **working** image creator instead of advertising only a planning prototype.

## Validation evidence

- Exact branch JavaScript syntax and static DOM consistency checked with V8 tool.
- Canvas builder checked with DOM/canvas stubs: preview dimensions, stale-preview invalidation, and PNG Blob/download event.
- Video builder checked with mocked WebAudio/MediaRecorder: readable 30s digital-audio input, expected audio+video stream connection, blob export and error paths. **Mocked tests are not real video acceptance.**
- Separate *actual* local Chromium 1.1-second technical test with CanvasCaptureMediaStream + WebAudio and MediaRecorder produced a file FFprobe identified as **VP8 video 640×360 and Opus audio**. This proves Chrome audio/video muxing feasibility, **not** that the complete P2-050 web UI passed.
- Targeted source, desktop/mobile PNG, and 30-second browser WebM+audio tests are committed. GitHub Actions issue #100 continues to require independent verification that jobs actually executed; do not claim green CI without logs.
- No actual LLM browser generation, neural image/video/TTS inference, account registration, cloud storage or customer subscription was activated by this website change.

## Limits and release safety

The site is still a public **static** Render service, not a server-hosted AI product. Users must own or hold consent for source narration. The video is a motion graphic, not neural text-to-video. Browser support varies; Chromium with WebM/Opus is currently the tested technical basis. Review voice clarity before sharing. Unknown rights/consent remain HOLD in custom project planning.

Server-hosted AI, customer accounts, cross-device history and genuine neural media require authenticated hosting, legal model clearance, secure persistence, operator tests and resources not present in the Render workspace. Do not merge pending gated source-only model PRs or activate the private backend under the public site in this release.
