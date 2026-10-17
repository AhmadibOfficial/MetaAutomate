# P2-04e — Long-form AI Film Studio (future subscribed capability)

**Status: roadmap and architectural contract only — not a shipped feature, subscription product, or evidence of film-length model inference.** This expands the film production objective beyond the currently supported 2–8-second inference proof clips. No payment required for local engineering.

## Intended project classes

| Class | Duration | Intended workflow |
|---|---:|---|
| Short | 30–120 seconds | Ads, reels, explainers |
| Extended | >2–10 minutes | Courses, demonstrations |
| Documentary | >10–30 minutes | Narrated investigations/learning |
| Film Studio | >30–120 minutes | Multi-scene films, serial episodes |

A subscribed plan is a *future commercial entitlement*; do not enable billing, buy GPU capacity, promise unlimited credits, or advertise available film generation before cost/security/product gates and explicit approval.

## Long-form architecture

1. **Story development** — script, treatment, scene breakdown, shot list, character bible, style guide and screenplay revision history. The film must preserve visual continuity, original story rights, and written authorizations.
2. **Storyboard and asset manifest** — each shot has stable scene/shot IDs; source job digest; approved prompt and checkpoint digest; expected in/out timestamps; owned/licensed assets; likeness/voice consents; rights evidence hashes. Input assets must be locally resolved, regular files within a permitted root. No HTTP URLs, file symlinks or implicit media pulls.
3. **Short-shot generation** — independently authorized offline image and short-clip inference using existing P2-04c worker, respecting true native model resolution. Verify each output with P2-04d. Do not invent long native generation.
4. **Continuity and quality review** — sample frames at shot boundaries for characters/wardrobe, camera direction, scene lighting, resolution, pacing, facial anatomy, legible typography, severe flicker and distortion. Human-reviewed re-generation when required.
5. **Audio pipeline** — original or licensed narration/voices/music/foley with explicit voice-likeness consent, transcript, closed captions, language support and per-track licensing records. Reject unauthorized voice cloning.
6. **Deterministic offline timeline composition** — allowlisted FFmpeg/FFprobe binaries in a sandbox without network, safe argument arrays (never shell=True), enforced resource limits, bounded input size/scene count/duration, stable frame rate, transitions, color management and clip interpolation only when documented. Track native vs upscaled detail.
7. **Film delivery outputs** — target 1080p at 24 or 30 fps for accepted composition, with exploratory 4K only after hardware/cost feasibility. Export mp4 plus subtitle track and chapter/timecode manifest; re-probe final actual duration, audio sync, captions and codecs.
8. **Content moderation, rights and release** — separate human approvals for every asset and the *final film hash* after rendering. Cryptographically bind production manifest, model attestations, final media hash and reviewer decision. Leave output in a private quarantine until a separate verified publish authorization exists.
9. **Resumability** — incremental per-shot retries and atomic checkpoints, deterministic assembly manifests, quota accounting and retry cost caps. Design for hours-long export without promising a single model can synthesize a 120-minute film in one pass.

## Future subscription policy

- **No active subscriptions** in this development milestone. Distinguish preview tools, local source tests and actual deployed film-making capabilities.
- Future film-length tiers need compute quotas, queue limits, maximum length, licensed voice/music policies, storage retention, fair-use controls, customer data protections, refund/cost rules and explicit opt-in.
- Do not use 'unlimited AI film generation' claims without sustainable cost/performance evidence.
- Financial forecasts must use measured per-shot GPU seconds, redo frequency, storage and transcoding minutes rather than unsupported promises.

## Acceptance sequence and boundaries

- [x] PR #94 source CI passed at commit `152e1e661f3830558ad4424c07d962c449353c78` (verify any subsequent edits again)
- [ ] Prove one genuine image and one 2–8-second short video with licensed checkpoints, isolated runtime, independent review and real signed receipts.
- [ ] Validate high-fidelity image enhancement and honest native/upscale metadata.
- [ ] Complete a **30–120-second** composed video with multiple approved shots, narrated audio, captions, and final-manifest integrity.
- [ ] Produce a **5-minute** test film with continuity review, license evidence, safety review and measured real costs.
- [ ] Gradually test 10, 30 and 120 minutes under separately approved operational/cost thresholds.

**Never** treat these roadmap targets as completed outputs or available customer subscriptions. Phase 01 remains 3/9; Phase 02/03 operational NO-GO. No new cloud deployments, migrations, subscriptions, public publishing or customer activation.
