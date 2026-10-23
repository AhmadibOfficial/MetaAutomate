# P2-060 — Unified Campaign Workbench

## Delivery

This milestone is a working browser-only inventory-to-campaign vertical slice. It does NOT claim a production AI agent, social publishing integration, cloud model, or authenticated customer platform.

| Capability | Implemented source | Still pending |
| --- | --- | --- |
| Data Analysis & Research | Real user-supplied CSV parsing, validation, conservative stock signals | Verified real-time sales intelligence, hosted private data ingestion |
| Business Automation | Deterministic staged campaign workflow and event record | Event-driven worker and authenticated business integrations |
| AI Agents & Orchestration | Bounded task sequence and human approval gates | Real model reasoning, authenticated agent tools and multiagent runtime |
| Image Studio & Video Projects | Original four-color 1080×1080 Canvas PNG and editable/downloadable video production brief | Neural generation; automatic rendered video within this workspace |
| Social Media Automation | Editable post, explicit internal approval, gated copy | Connected social accounts, provider scheduling and publishing, verified analytics |

The existing Creative Studio at /creative/#instant-video can export narrated WebM files with user-owned audio. The new workbench links to it. The video brief itself is not a playable video.

## Input contract

Import a CSV (128 KB maximum, 400 rows maximum) with exactly these headers:

    sku,name,stock,weekly_sales,unit_price_kobo

Example data:

    CAP-01,Embroidered Cap,18,0,850000
    FAB-02,Classic Kaftan,24,3,3500000

Prices use exact integer kobo; e.g. 3500000 means ₦35,000.00. SKUs must be unique, ASCII 2–36 characters. Stock and weekly sales must be integers from 0 through 1,000,000. Prices must be positive and under 100,000,000,000 kobo. Quoted commas, escaped quotation marks, UTF-8 BOM and CRLF are supported. CSV formula-like names, control characters, duplicate SKUs, malformed quoting, invalid row widths and oversized files are rejected. Do not import customer names, personally identifiable data, secrets or confidential business files into this public browser preview.

Data stays in local browser memory and is erased by reloading. It is not uploaded. A strict Content Security Policy disables browser network connections on the workbench. Downloads occur only when explicitly requested.

## Business logic

Prioritize items with:
1. At least five units and zero reported weekly sales.
2. High inventory relative to recorded weekly sales (stock at least max(10, 4 × weekly sales)).

Exclude out-of-stock and low-stock products. This is a basic stock prioritization rule, not a sales forecast. It cannot establish profit, pricing advice or campaign effectiveness.

The graphic uses MetaAutomate Midnight Navy (#040D20), Electric Blue (#00A7ED), Silver (#DCE6F1), and Gold (#EFB94F). All graphics are original browser-made layouts. Draft copy uses the source price and reminds reviewers to confirm current stock, prices, delivery and product rights.

## Approval, metrics and evidence

The review checkbox and button record only INTERNAL_DRAFT_REVIEW_RECORDED for COPY_OR_DOWNLOAD_ONLY. Edits to the social draft or storyboard revoke prior approval. No real provider permission is granted or post sent.

Users may enter self-reported impressions, clicks and orders with a measurement source note, constrained to orders <= clicks <= impressions. Click ratios are exact arithmetic on user-supplied counts. Evidence reports are clearly SELF_REPORTED_NOT_INDEPENDENTLY_VERIFIED and explicitly deny campaign attribution, revenue or profit claims. JSON download includes the draft, approval record, counts, local in-memory actions, and disabled-external-effects flags. It is not independently signed evidence of publication.

## Acceptance commands

Run in the existing MetaAutomate repository:

    node --test tests/campaign_engine.test.cjs
    python3 -m pytest -q tests/test_p2_060_campaign_workbench.py
    python3 -m http.server 18080 --bind 127.0.0.1 --directory apps/site

With a separate terminal and Playwright Chromium installed:

    python3 scripts/verify_campaign_workbench_browser.py

The browser acceptance checks import, prioritization, PNG and video-brief download, creative link, internal approval and its revocation, manually entered metrics, downloaded JSON evidence, zero cross-origin requests, no page errors, and desktop/mobile layout. A source review alone is not a browser acceptance result.

## Release policy

No customer accounts, PostgreSQL migrations, real media inference, social publication, background scheduling, external provider credentials, AI model downloads or Render configuration changes in P2-060. The preexisting Foundation 3/9 and Phase 02/03 operational NO-GO status remains binding. Merge and website deployment require passing validation, independent review and separate release authorization.

## Next engineering steps

- P2-061: tenant-authenticated data ingest, encryption, minimization, deletion, retention, and audit controls.
- P2-062: independently evaluated model-backed planning and authenticated approval-bound tool execution.
- P2-063: rights-cleared media workers, provider-specific scheduling permissions and verified publication receipts.
- P2-064: provable outcome measurement using authenticated sources and comparison methodology.

These are plans, not features claimed live in this milestone.
