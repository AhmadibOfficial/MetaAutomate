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
    python3 -m pytest -q tests/test_p2_060_campaign_workbench.py tests/test_p2_060_browser_harness.py
    python3 scripts/verify_campaign_workbench_browser.py

Playwright for Python and its Chromium browser must already be installed locally.

### Kali Playwright 1.55.0+ds missing-driver recovery (development only)

Kali's Debian-derived `python3-playwright 1.55.0+ds-2` may import
correctly but lack its separate Node Playwright CLI at
`/usr/share/nodejs/playwright/cli.js`. This is a **tooling blocker**, not
an application acceptance failure. The verifier now detects the absent CLI
before starting the HTTP server and reports `BROWSER_ACCEPTANCE_BLOCKED`.

Use an isolated Python virtualenv **outside the repository** instead of
`sudo pip`, `--break-system-packages`, deleting old environments or
altering packages used by theHarvester/wapiti3. Review the available free
disk space and network costs before installing new browser binaries.
The commands below create a new environment and separate Chromium cache;
do not overwrite any existing directory.

    (
      set -euo pipefail
      VENV="$HOME/.local/share/metautomate-browser-venv"
      BROWSERS="$HOME/.cache/metautomate-playwright-browsers"
      if [ -e "$VENV" ] || [ -L "$VENV" ]; then
        echo "STOP: browser venv path already exists"
        exit 1
      fi
      if [ -L "$BROWSERS" ]; then
        echo "STOP: unexpected symlink for browser cache"
        exit 1
      fi
      mkdir -p -- "$HOME/.local/share"
      python3 -m venv "$VENV"
      "$VENV/bin/python" -m pip install "playwright==1.55.0"
      PLAYWRIGHT_BROWSERS_PATH="$BROWSERS" "$VENV/bin/python" -m playwright install --no-shell chromium
      PLAYWRIGHT_BROWSERS_PATH="$BROWSERS" "$VENV/bin/python" scripts/verify_campaign_workbench_browser.py
    )
### 2026-10-24: full Chromium present; headless-shell download failed

The isolated wheel and full Chromium 140 (Playwright build 1187) were
downloaded successfully, but the **separate** 104 MiB headless-shell failed
after repeated TLS timeouts and DNS errors. The browser verifier now starts
the version-matched full Chromium via `channel="chromium"` (Playwright's
official *new headless* mode), which does not require that shell archive.
See https://playwright.dev/python/docs/browsers .

**Do not reinstall the Python wheel, delete the existing cache or rerun
`playwright install chromium` without `--no-shell`.** On the existing
installation, attempt browser verification directly:

    cd ~/MetaAutomate
    PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q tests/test_p2_060_campaign_workbench.py tests/test_p2_060_browser_harness.py
    PLAYWRIGHT_BROWSERS_PATH="$HOME/.cache/metautomate-playwright-browsers" \
      "$HOME/.local/share/metautomate-browser-venv/bin/python" \
      scripts/verify_campaign_workbench_browser.py

If the full Chromium binary cannot launch (e.g., missing OS shared
libraries), keep browser acceptance **BLOCKED** and inspect its exact
error first. Do not install system packages, force browser flags,
bypass CSP, or silently change to another browser. Actual screenshots
and downloaded evidence are accepted only after the full verifier passes.

These commands are **manual**, not automatically executed by the
application or CI. A venv setup failure must halt before the browser step.
If the machine lacks `python3-venv`, has insufficient storage or cannot
download Chromium over TLS, record the failure rather than changing system
packages without a separate review. Playwright's managed Chromium is a
version-specific download; system Chromium is not automatically an equivalent.
Leave the operational NO-GO unchanged until the actual browser run passes.

The browser verifier now **self-hosts the trusted static site only on an
ephemeral 127.0.0.1 port**, rejects requests with unexpected Hosts, HTTP writes,
static path traversal, and symlink escapes, and blocks off-origin browser
requests. Do **not** start a separate HTTP server or use production endpoints.

Screenshot, PNG, video-brief and self-reported sample-metric JSON artifacts
are saved to a newly created private directory outside the Git checkout
(the command prints its absolute path). A requested location is allowed only
if it is a new directory outside the repository:

    python3 scripts/verify_campaign_workbench_browser.py --output-dir "$HOME/meta-browser-proof-20261024"

Use fabricated inventory only; browser artifacts are developer-local evidence
without independent signature, customer consent verification or commercial
traction. Output from a failing browser verification is **not a PASS** even
if individual screenshots were saved before the failure.

The browser acceptance checks import, prioritization, PNG and video-brief
download, creative link, internal approval and its revocation, synthetic
metrics, downloaded JSON evidence, zero off-origin requests, no page errors,
and desktop/mobile layout. The source-only harness regression tests do not
replace real Playwright Chromium execution.

The standalone verifier does not merge or deploy, activate social accounts,
use public network services, run AI models, upload data, apply migrations or
make GitHub Actions pass. The operational 3/9 Foundation NO-GO and independent
release-review gates remain unchanged.

## Release policy

No customer accounts, PostgreSQL migrations, real media inference, social publication, background scheduling, external provider credentials, AI model downloads or Render configuration changes in P2-060. The preexisting Foundation 3/9 and Phase 02/03 operational NO-GO status remains binding. Merge and website deployment require passing validation, independent review and separate release authorization.

## Next engineering steps

- P2-061: tenant-authenticated data ingest, encryption, minimization, deletion, retention, and audit controls.
- P2-062: independently evaluated model-backed planning and authenticated approval-bound tool execution.
- P2-063: rights-cleared media workers, provider-specific scheduling permissions and verified publication receipts.
- P2-064: provable outcome measurement using authenticated sources and comparison methodology.

These are plans, not features claimed live in this milestone.
