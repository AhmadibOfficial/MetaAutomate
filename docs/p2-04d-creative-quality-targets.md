# P2-04d clarity and production-quality targets (not yet implemented as real inference)

MetaAutomate should produce **legible, deliberately composed media** rather than simply maximizing file size. Targets below are future quality acceptance, NOT claims of currently working GPU models or automatic upscaling.

## Image fidelity
- Distinguish **native model resolution** from **final delivery resolution**. Current signed Job schema limits source PNG dimensions to 256–768 px each. This is NOT 1080p, 2K or 4K generation.
- After real inference is evidenced, propose separately reviewed offline super-resolution and anti-aliasing pipelines. For marketing, aim for **2048 px+ final long edge**, with a **native-vs-upscaled** flag and exact input/output SHA-256. Never claim interpolated detail is native model detail.
- Mandatory human checks at 100% zoom: logo geometry, face/hand anatomy, text accuracy (prefer deterministic typography overlay), lighting, sharp edges, color fidelity and absence of severe artifacting. No unapproved brand marks or synthesized real-person likeness.
- Test dimensions, format, successful full decoding, provenance and model checkpoint licence. Computer-vision quality estimates may assist screening but do not replace human inspection.

## Video fidelity
- Current offline worker outputs **576×320, 8 fps, 16–64 frames (2–8 seconds)**. This is a proof-of-inference clip, not a high-definition finished video.
- Next *separate* pipeline target: 1920×1080 composed export, 30 fps and 30–120 seconds, using rights-verified clips, safe offline FFmpeg transitions, original narration with permission and synchronized captions. Upscaling and interpolation must be disclosed in the receipt, never represented as native generation.
- Quality checklist: frame-by-frame consistency, no severe flicker or distortions, readable titles/mobile-safe captions, voice intelligibility and suitable loudness, clear licensed soundtrack at a lower mix level than speech, no unwanted silent stretches, accurate duration and A/V sync.
- Re-run SHA-256, media probe and safety review **on the final rendered deliverable**, not solely on the original short clips. Export is still quarantined until separate human release approval.

## Engineering order
1. Green source CI for PR #94 and verified source tests (not proof of inference).
2. Legitimately licensed offline checkpoints, verifiable isolated GPU, genuine image and video inference, tamper-evident receipts and independent signed reviews.
3. Controlled image enhancement module with before/after evidence and perceptual QA.
4. Offline video composition module with subtitle/narration/music evidence and final output review.
5. Only after complete operational security gating, evaluate customer-facing release. **No automated publishing.**

No subscriptions, public inference API, model downloads in workers, GitHub-uploaded media, or unapproved deployments are introduced by this specification.
