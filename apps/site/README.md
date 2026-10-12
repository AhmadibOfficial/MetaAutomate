# MetaAutomate — Business Website

A premium, self-contained, responsive **public marketing website** for MetaAutomate. The official blue/silver/gold logo and mission/vision/core values are sourced from the approved brand board.

It is intentionally separate from the Objective Workspace API under apps/api and apps/web.

## What this website can do

- Explain MetaAutomate's business mission, vision, tagline and focus sectors.
- Describe the *current* working Objective Workspace accurately: draft planning, saved graphs and human review only.
- Showcase the *planned* capability vision without claiming AI agents, payments or external execution are live.
- Provide mobile navigation, accessible capability filters, and working in-page navigation.
- Publish as static HTML, CSS, JS, and one approved logo image; **no database, authentication, analytics, or JavaScript API calls**.

## Review without hosting

    cd apps/site
    python3 -m http.server 18080 --bind 127.0.0.1

Then open http://127.0.0.1:18080/ on the same computer. This is independent of the existing MetaAutomate workspace on port 8000.

For automated tests, from the repository root:

    python3 -m pip install playwright
    python3 -m playwright install chromium
    python3 scripts/verify_brand_site.py

The test needs the local website server running. GitHub CI starts the server automatically and publishes desktop/mobile screenshots.

## No-card static hosting option

Render provides a no-payment-required signup and free Static Sites, including an HTTPS onrender.com domain. Link the PRIVATE GitHub repository (authorize access to this repo only), then create a **Static Site** with:

- Repository: AhmadibOfficial/MetaAutomate
- Branch: merge-reviewed main only
- Build command: echo "Static website"
- Publish directory: apps/site
- Auto deploy: OFF until the owner explicitly approves changes

The root render.yaml provides the equivalent static-only Blueprint configuration. **No Render service has been created yet.** This site is a **public-facing business homepage**, so anyone can inspect the HTML/CSS/JS and official public logo served to their browser, even though GitHub source stays private.

Important: Render's free static-site use consumes the account's included bandwidth and build minutes. A working Objective Workspace, API and durable PostgreSQL database cannot be created by deploying this folder alone.

Render official docs: https://render.com/docs/static-sites
No-payment setup: https://render.com/docs/your-first-deploy
Blueprint syntax: https://render.com/docs/blueprint-spec

## Business and code licensing

The GitHub repository is private. Its pre-existing root LICENSE still includes GPLv2 text; this static website change does **not** revise or remove it. Repository visibility does not revoke existing third-party rights to copies previously obtained. Brand and copyright ownership should be reviewed separately before issuing a different software license.

The MetaAutomate mark is a brand asset provided/approved by the business owner. Publishing the website makes the logo visible online; it does not by itself create or resolve trademark rights or ownership of independently contributed code.

## Current limitations

This website is a business information site, not the logged-in product. Avoid presenting the planned capabilities as already available. No signup, demo request form or lead capture is implemented: those require an approved privacy notice, backend, abuse protection and functional contact channel.
