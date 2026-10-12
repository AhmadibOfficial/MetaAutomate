# Free-of-charge hosting choices (MetaAutomate business)

## Selected first step — public business website

**Render Static Site Free**, linked from the approved private GitHub repository. It is a strong fit because MetaAutomate's new apps/site is just HTML/CSS/JavaScript and the approved logo. It does not require a running server, persistent storage, payment card, or customer data.

Render's official getting-started docs say no payment is required for the free deployment. Private Git provider repositories can be linked through authorization. Static sites provide an onrender.com HTTPS domain and automatic TLS. Build minutes/bandwidth are subject to included quotas; deploy should be approved explicitly.

- https://render.com/docs/your-first-deploy
- https://render.com/docs/static-sites
- https://render.com/docs/web-services

### Owner-controlled deployment checklist

1. Keep MetaAutomate GitHub private. Do not paste GitHub credentials into cloud configuration or public issues.
2. Review the website, brand logo and text. Merge only the focused business-website PR after tests pass.
3. Sign up with Render using GitHub. **Do not add a card**; select New → Static Site, not Web Service or PostgreSQL.
4. Grant Render's GitHub app access only to the MetaAutomate repository. Confirm the branch is main.
5. Build: echo "Static website". Publish: apps/site. Enable manual deployment initially.
6. Review the assigned HTTPS onrender.com URL before sharing it. Do not use any paid resource or set up optional billing without approval.

### Not the full product

Static hosting will not run the objective API or persist workflows. Never copy development .env, .workspace-access-key, PostgreSQL dumps, or business customer records into apps/site. All static files become publicly retrievable.

## Full FastAPI/PostgreSQL app later

Potential free pilot: **Render Free Web Service plus Neon Free PostgreSQL**. Render's free web services can sleep after 15 minutes idle; Neon offers a separate free Postgres tier. This route requires substantial security work: real production authentication/SSO, database migration, separated runtime credentials, CORS/CSRF/domain protection, backups, and rate limiting.

**Do not use Render Free PostgreSQL as durable business storage.** It expires 30 days after creation; its data is not suitable for long-lived customer production records. Render's free Web Service is publicly reachable on an HTTPS address, unlike private services, so the login and authorization model must be production-hardened first.

- https://render.com/docs/free
- https://neon.com/blog/neon-free-plan-1-gb-per-project

A free pilot is not guaranteed to have 24/7 uptime, unlimited usage, a permanent resource allocation or zero operational risk. This phase deliberately prioritizes website presence first, without exposing the operational application.

## Other options

Cloudflare Pages offers static-site deployment on a free tier, with build/asset limits. It can be reconsidered if Render signup becomes difficult. Do not assume any host's billing/card verification behavior is permanent without checking the signup flow.

- https://developers.cloudflare.com/pages/platform/limits/

We are NOT using Vercel Hobby for business deployment, nor Oracle Cloud registration while card verification remains a blocker. No provider accounts or billable resources have been created as part of this website PR.
