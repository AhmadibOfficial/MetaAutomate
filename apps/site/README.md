# MetaAutomate Global Company Experience v2

A distinctive four-page international technology-company website for MetaAutomate.

Positioning: an emerging-technology business combining intelligent systems, software engineering, cybersecurity, cloud, data, product design and experience. This is a business-facing corporate website, **not** an open-source project launch or a statement that every planned technology is operational.

## The brand standard

Preserve the owner-approved MetaAutomate mark and deep navy/electric blue/silver/gold palette. Mission, vision, core values and strategic focus remain consistent:
- Tagline: **Turn Your Vision Into Reality**
- Descriptor: **Intelligence · Creation · Automation**
- Proposition: **Solutions, Convenience and Experiences**
- Values: **Integrity, Excellence, Innovation, Impact, Always HALAL**
- Mission: To build intelligent systems that automate work, create solutions and empower individuals, organizations and societies to achieve more.
- Vision: To become the world's most trusted, impact-driven AI automation platform creating opportunities, innovation, and positive change.
- Strategic sectors: Agriculture, Healthcare, Food Security, Islamic Knowledge Systems and related emerging-technology opportunities.

## Site structure

- Home (/): Global MetaAutomate positioning, interactive engineering philosophy, services, sectors and real Objective Workspace foundation.
- Services (/services/): Six disciplines, with scoped example engagements. Work is defined per project; it does not claim a client track record that hasn't been demonstrated.
- Company (/company/): Mission, vision, values, meanings behind the approved logo and the four-phase roadmap.
- Project brief (/engage/): Browser-only interactive project brief builder with TXT download and clipboard copy. It does **not** send submissions or store any data on the server.

The whole site consists of local HTML, CSS, JS and the approved logo. There are no third-party font calls, tracking scripts, cookies, database connections or API requests.

## Preview locally

From repository root, run:

    python3 -m http.server 18080 --bind 127.0.0.1 --directory apps/site

Then open http://127.0.0.1:18080/ in the same computer. It does not touch MetaAutomate's Objective Workspace service on port 8000.

For browser testing, in a separate terminal with the static server running:

    python3 -m pip install playwright
    python3 -m playwright install chromium
    python3 scripts/verify_brand_site.py

GitHub Actions runs the tests automatically, including keyboard-accessible system tabs, mobile navigation at 390px and 360px, an end-to-end project brief download and verification that no requests leave the local test origin.

## Real capabilities versus future roadmap

MetaAutomate's current Objective Workspace is a development-stage planning product with structured objectives, proposed task graphs, saved plans and human review. Autonomous external execution, a production public app and integrated AI agents are **not** available. The website showcases service disciplines and direction while remaining accurate about operational capabilities.

## Deployment

The production business site is hosted as a Render **static site**, publishing only apps/site from private GitHub. The Render service already exists and hosts the preceding design version at https://metaautomate-business-website.onrender.com/.

**Auto deploy is disabled.** Do not trigger a redeploy automatically when merging this proposal. Get specific approval after the maintainer reviews the screenshots, service descriptions and contact experience. No API or customer data belongs in the public static site.

The owner has now supplied **metaautomating@gmail.com** for business inquiries. The website presents it as a direct mailto link in every footer and on /engage/. The brief generator offers an optional mailto draft with prefilled project details, clipboard copy and download, while explicitly requiring the visitor to review and send the email themselves. If the brief exceeds a safe mailto URL length, the draft is shortened and the visitor is instructed to attach the full downloaded text. No mail is automatically sent and the static site collects no information on a server. The mailbox ownership and reception capabilities have not been independently tested.

The repository is private. The existing GPLv2 LICENSE text is unchanged; prior distribution rights, future licensing and official logo rights are separate decisions.

## Official MetaAutomate social channels

MetaAutomate provided the following addresses for the business website. They appear in the global footer and in the homepage's dedicated social network section. The site uses ordinary secure external links and loads **no third-party embeds, trackers, feeds or social APIs**.

- **YouTube**: https://youtube.com/@MetaAutomate
- **LinkedIn**: https://www.linkedin.com/company/meta-automate
- **Instagram**: https://instagram.com/meta_automate
- **X / Twitter**: https://twitter.com/MetaAutomate
- **Facebook**: https://facebook.com/MetaAutomate
- **TikTok**: https://tiktok.com/@metaautomate

TikTok's trailing punctuation and LinkedIn's escaped formatting were normalized from the business-provided URLs. The URLs are supplied by the business; platform profile ownership was not independently verified. Do not claim follower counts, verification badges, response time or official customer support through these channels without confirmation.

## Business inquiry address

The business owner supplied **metaautomating@gmail.com** as MetaAutomate's inquiry address. It is a direct correspondence channel, not an authenticated SMTP connection, automated CRM, ticketing system or proof of mailbox control.

The project brief intentionally generates and opens a client-side `mailto:` draft. Visitors must use their own email application and press **Send**; a link click by itself does not deliver an inquiry. For long or complex briefs, download the original `.txt` and attach it manually. The static site makes no fetch/POST requests and stores no project data. Do not share confidential credentials or sensitive personal information in an initial inquiry.
