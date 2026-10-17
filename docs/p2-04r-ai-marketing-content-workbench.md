# P2-04r — AI Marketing Content Workbench (source-only)

Status: **source-only structured work-order engine**. Does NOT connect an LLM, publish, schedule, send email, create real images or videos, access live audience analytics, or make accuracy/performance guarantees. The source is a prepared offline planner, not an operational marketing agent.

## Marketing coverage

| Work order kind | Draft deliverable | Evidence and safety gate |
|---|---|---|
| Social | Platform hook, caption, CTA, hashtags, scheduling copy idea | No fabricated engagement metrics, false endorsements or platform connectivity |
| Blog | Topic, keyword mapping, outline, article drafts and internal linking plan | Cite source data, check claims and avoid invented search rankings |
| Product | Product titles, benefits, feature descriptions and SEO copy | No invented prices, features, availability or specifications |
| Email | Subject, preheader, segmented copy and follow-up concept | Consent, unsubscribe and recipient controls; never send without configured permissions |
| Ads | Claims-checked ad variations and sales/video scripts | No guaranteed ROI, false urgency or deceptive targeting |
| Visual | Licensed image/thumbnail/mockup brief | Rights, brand logo and identifiable likeness authorisation |
| Video | 30–120s storyboard, captions, narration concept and short-clip plan | This is a BRIEF; genuine AI model inference remains blocked by P2-04i/q |
| Authority | FAQ, glossary, cited comparisons and research outline | Distinguish validated facts, estimates, hypotheses and missing evidence |

## Source implementation

\`apps/api/app/marketing_content_workbench.py\` provides:

- \`create_campaign(brief)\`: validates a structured campaign objective (brand, offer, audience, goal, country, selected platforms, verified facts with source references, approved CTA, evidence owner, and chosen deliverable types).
- Deterministically creates work orders with source-constrained prompts for later approved LLM generation and fact-check checklists.
- \`inspect_candidate(...)\`: records the hash of candidate content and a provisional human-review claim. Its output NEVER authorizes publication or scheduling.
- Explicit \`generation_engine_connected: false\`, \`model_outputs_created: false\` and \`publication_authorized: false\`. This is not AI content generation.

All claims must be grounded in actual sources. A caller can currently mislabel an invented statement as a verified fact; this module does not authenticate referenced source documents. Genuine claim verification, original research and factual review remain separate dependencies.

## Next engineering milestone

P2-04s — **Governed Content Generation and Performance Measurement**:
1. Add a strictly opt-in, authorized LLM adapter, with quotas, privacy review, prompt-injection protections and evidence-based hallucination checks.
2. Build channel-specific renderers and branded (white-theme) editorial templates for Facebook, Instagram, TikTok, YouTube, email and SEO pages; only connected channels may become publication targets.
3. Add independent brand, rights, consent, financial claim and sources checks; create immutable approval records.
4. Establish separate Metricool integration using verified workspace/platform connections; **do not assume Facebook/LinkedIn** connections, and do not publish in this milestone.
5. Measure authenticated attribution, conversion rates, contribution and retained customer value; no fabricated ROAS or income guarantees.

## Release boundaries

No credentials, paid subscription, actual LLM access, customer activation, off-platform publishing or deploying to Render. PR #94, #95 and #97 remain separate gated technical work. Phase 01 verification 3/9, Phase 02/03 operational NO-GO remain unchanged. The P2-04r content workbench must not be confused with its underlying AI media-generation capabilities.
