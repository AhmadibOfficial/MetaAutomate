# P2-04b — Creative Workbench: Image & Video Planning

Status: **functional browser-only prototype; NOT a live generative media service**.

The public marketing website currently advertises the **02 / CAPABILITY — Image & Video Generation** and **06 / EXPERIENCE — Product Design & Experience**. This milestone connects those claims to an honest, no-subscription planning interaction, without implying image or video media has been produced. The public website uses an existing approved Render static-site deployment; no new paid service or account is necessary.

## User journey

1. Start at homepage **Image & Video Generation**; open the new Creative Workbench page, or navigate from services **Product Design & Experience**.
2. Pick Image Concept or Short-form Video (fixed 30, 60, 90 or 120 seconds); describe an educational/business objective, audience, and creative tone.
3. Declare image/reference rights: owned/original, licensed, written permission, none, or unknown. Licensed/permission work additionally requires a traceable evidence reference. Declare likeness/voice consent: not needed, consented, unresolved, or missing.
4. Name the human reviewer and build a local draft. When rights or consent are missing, the status is **HOLD** with explicit issues. With declarations, the result is **READY FOR HUMAN REVIEW — NOT APPROVED**; this does not authenticate permission or grant publishing authorization.
5. See deterministic image composition direction or a four-scene short video storyboard with time ranges, narration/soundtrack and captions guidance.
6. Download a plain-text **review brief** using the browser's local Blob/download API. It does NOT download an image or video or call a model.
7. Clear the form to reset. No data leaves the browser, is posted to MetaAutomate, placed into storage or used for marketing measurement.

## Why this stage is honest

"Rights-aware" means identifying ownership, consent and licence **claims** that require independent human verification. A select field, named reviewer or textual evidence reference does not validate a licence or consent. No external AI media model is connected, no image pixels or movie are generated, no paid APIs invoked, no real-world user information is saved or posted, and no social content is automatically published. Source-only user interaction does not represent a launched full-service subscription product.

The working prototype is deliberately separate from the production Intelligence server and Foundation F04–F09 gates. Future operational service requires real authenticated reviewers, protected source/evidence storage, vendor terms/licensing checks, cost controls, model/output testing, content moderation, audit trail, legitimate access to sources, human review before generation and any publication, and an approved live deployment.

## Engineering and verification

- Browser assets: apps/site/creative/index.html, apps/site/assets/creative.js, apps/site/assets/creative.css.
- Navigation: homepage Capability 02 → Creative Workbench; Services Experience 06 → Creative Workbench and project enquiry.
- Automated source/privacy assertions: tests/test_creative_workbench_static.py.
- Local Chromium desktop (1440) and mobile (390/360) acceptance: scripts/verify_creative_workbench_browser.py. Verifies rights/consent HOLD, licence reference requirement, readiness not approval, 90-second storyboard, local export, XSS-safe user text, zero external requests, mobile layout and form reset.
- Workflow: .github/workflows/creative-workbench-browser.yml.
- No runtime Python API, secrets, worker access, migrations, model providers, third-party analytics or new subscriptions.

**Foundation remains 3/9 verified, F04–F09 blocked and Phase 02/03 operational NO-GO.** A successful static publication does not establish real private staging.
