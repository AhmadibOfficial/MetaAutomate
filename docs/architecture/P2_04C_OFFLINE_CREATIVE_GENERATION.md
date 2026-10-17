# P2-04c — Offline Image/Short-Video Generation Engine (optional research worker)

**Release category: source code and safety tests only. Actual model execution NOT performed in CI or Render. Private API is disabled.**

This milestone progresses the public **02 / Capability — Image & Video Generation** and the **06 / Experience — Product Design & Experience** browser-only planning tool toward **real optional local inference** while respecting rights, security and the absence of purchased subscriptions. It does not activate a generative provider, run a pretrained model, ship GPU infrastructure or make claims about AI output quality.

## Actual implementation

- Worker: apps/api/app/creative_local_generation.py. Accepts tightly validated image and text-to-video requests only, referring to **operator-installed, licence-approved local model files**. No network service is used to fetch weights.
- For **real image inference**, allowlisted local Diffusers StableDiffusionPipeline or StableDiffusionXLPipeline is loaded by AutoPipelineForText2Image.
- For **real short-clip inference**, allowlisted local TextToVideoSDPipeline is loaded by DiffusionPipeline, with **16–64 frames, 8 fps, 576×320 resolution**. This is a **2–8 second generated clip**, NOT the 30–120 second educational/faceless finished video described by the public Creative Workbench. Full videos will need separately approved clip composition, transitions, voice/soundtrack rights, captions and final QC.
- Optional heavy dependencies, separate from the public site and private API: apps/api/requirements-creative-local-optional.txt. Diffusers, PyTorch, weights, a GPU and video codec are **not installed** by the normal API build or CI.
- Only approved local model classes are allowlisted; symlinks, paths outside an operator-approved model directory, unexpected pickle/ executable extensions, missing safetensors and unknown task classes are refused. Full local model-file contents are SHA-256 hashed and bound to authorization.
- Two *distinct* Ed25519 approvers must sign an exact approved job and model tree. The signed validity window is at most 30 minutes and includes claims that prompts, licences, reference rights and likeness consent were reviewed.
- By default, **execution is refused**. The flags MAT_CREATIVE_OFFLINE_EXECUTION_ENABLED=1 and MAT_CREATIVE_NETWORK_ISOLATED=1 must be explicitly set in an independently verified network-disabled GPU execution environment. **Flags only attest operator intent; they cannot themselves enforce a firewall.** Do not set them until separate real infrastructure checks. No production API route exposes this worker.
- A generated PNG or MP4 (if genuine local inference were executed) is stored solely in a private **0700 quarantine** directory. Media output magic is checked, receipt with input/model/approval/output hashes is written 0600, and there is no endpoint to distribute or publish it.
- Post-generation review contract: apps/api/app/creative_output_review.py. A distinct independent reviewer can issue an Ed25519-signed, exact media-hash-bound safety/rights/consent review. Output is still **NOT DISTRIBUTION AUTHORIZED** regardless of reviewer approval; independent verification of actual safety tools, licences and customer release consent must precede any future distribution integration.

## Technical references (not model endorsement)

- Hugging Face Diffusers AutoPipelineForText2Image supports task-selected locally loaded pipelines.
- Diffusers TextToVideoSDPipeline supports local text-to-video frames and export_to_video for clips.
- The compatible licence, commercial use, user-submitted reference rights, identity consent, training-data policies and safety constraints for any specific model **must be checked separately** before even a research run. This repository **does not recommend or bundle** a particular checkpoint.

## Operator-controlled future research only (NOT approved now)

Never run this in the public Render static website or production API. Only a separately approved, no-egress research host / isolated GPU container may install optional dependencies and pre-approved local checkpoint files. Private weight storage and model licence review must be independently witnessed. An operator may later use:

    PYTHONPATH=apps/api python -m app.creative_local_generation \
      --job /approved/jobs/one.json \
      --authorization /approved/receipts/one.signed.json \
      --model-root /approved/models \
      --quarantine-root /private/quarantine

The worker **will fail closed** unless properly configured with owner/reviewer verification public keys (MAT_CREATIVE_OWNER_VERIFY_KEY, MAT_CREATIVE_REVIEWER_VERIFY_KEY), checked local weights, 2 valid current human approval signatures, and the two explicit opt-in environment flags. The image/video **output never enters the website**, even on success.

No private signer key should ever enter the worker or be committed to GitHub. Public verification keys must be pinned outside untrusted job files. Models with code, pickle weights, hidden symlinks or unapproved licences should not be loaded.

## Outstanding operational blockers

- **F04:** GitHub main still has no enforceable required-check private-repo protection.
- **F05:** No independent approved isolated staging environment, cost ceiling, region and owner.
- **F06:** No real staff SSO/MFA verification for creative work.
- **F07:** No independent encrypted offsite restoration.
- **F08:** No live network egress denial, independent safety-model/output performance evaluation, monitoring or rollback evidence.
- **F09:** No consented customer pilot, source rights authenticity proof or independently verified business value.

Phase 01 remains 3/9 verified and Phase 02–03 operational NO-GO. These gates are not altered by merge, test success or static website deployment.

## Tests and provenance

The new CI runs source-contract tests using **deliberately fake PNG/MP4-like bytes** as injection stubs: these are **not actual generated images/videos and should not be shown as products**. The tests verify job bounds, signer independence, expiring approval, job/model hash tampering, unsafe model assets, disabled-by-default execution, quarantine cleanup, independent output review and absolute no-publish status. No pretrained checkpoint download, GPU, provider token, video codec or subscription is necessary for tests.

The existing browser-only Creative Workbench remains useful for drafting and exporting rights-aware production plans. Actual content generation, human moderation and media release remain separate steps and separate future operational approvals.
