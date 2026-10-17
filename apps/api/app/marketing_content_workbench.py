"""P2-04r: offline Marketing Content Workbench work orders and review gates.

Does not invoke any model, send email, schedule posts, scrape competitors,
or claim that generated drafts are factual. Approved external connectors must
be developed and authorised separately.
"""
from __future__ import annotations

from hashlib import sha256
import json
import re

KINDS={
    "social": ("Social media posts & captions",
               "Platform-specific hook, plain-language caption, CTA and relevant hashtags.",
               "Never fabricate customer testimonials, reach or engagement statistics."),
    "blog": ("Blog posts & articles",
             "Evidence-backed topic, keywords, outline, draft sections and suggested internal links.",
             "Cite each externally verifiable claim; do not invent citations or claim unverified SEO rankings."),
    "product": ("Product descriptions",
                "Feature-first, audience-appropriate product title, benefits, specifications and honest CTA.",
                "Do not invent dimensions, availability, prices, certifications or results."),
    "email": ("Email campaigns & newsletters",
              "Segmented subject, preheader, body, compliant CTA and follow-up concept.",
              "Require consent and unsubscribe method; do not impersonate recipients or invent open rates."),
    "ads": ("Ad copy & sales scripts",
            "Channel-specific headline, benefit, substantiated proof, CTA and video-script variation.",
            "Avoid guaranteed sales, misleading scarcity, unsupported ROAS and deceptive claims."),
    "visual": ("Visuals & graphics",
               "Rights-aware image brief for thumbnail, mockup, promotional graphic and alt text.",
               "No third-party logo or recognizable person's likeness without authorization."),
    "video": ("Video content & editing",
              "Storyboard, opening hook, on-screen text, narrated script, captions and cut-down plan.",
              "30-120s is a script brief, not a claim that real AI film rendering is available."),
    "authority": ("Data-backed & authority content",
                  "Source-led FAQ, glossary, original research plan and fair comparison guide.",
                  "Clearly label hypotheses, estimates, sources and evidence gaps."),
}
CHANNELS={"facebook","instagram","tiktok","youtube","linkedin","email","website","search","catalog"}
MAX_FACTS=12
HANDLE=re.compile(r"^[a-z][a-z0-9_-]{5,63}$")
CONTACT=re.compile(r"^[\w.\-+ ]{0,100}$")

class ContentHold(ValueError):
    pass

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True,allow_nan=False).encode("ascii")

def _short(value, label, limit, *, minimum=1):
    if type(value) is not str or not minimum <= len(value.strip()) <= limit:
        raise ContentHold(f"{label} must contain {minimum}-{limit} characters")
    return value.strip()

def create_campaign(brief:dict)->dict:
    """Create deterministic, structured prompts for subsequent authorised LLM use.

    No LLM call is made; this is NOT actual AI content generation.
    """
    required={
        "campaign_id","brand","industry","offer","audience","goal",
        "channels","verified_facts","approved_cta",
        "content_kinds","country","evidence_owner",
    }
    if type(brief) is not dict or set(brief)!=required:
        raise ContentHold("Campaign schema invalid")
    code=brief["campaign_id"]
    if type(code) is not str or not HANDLE.fullmatch(code):
        raise ContentHold("Invalid campaign identifier")
    brand=_short(brief["brand"],"brand",100)
    industry=_short(brief["industry"],"industry",100)
    offer=_short(brief["offer"],"offer",240)
    audience=_short(brief["audience"],"audience",180)
    goal=_short(brief["goal"],"goal",180)
    cta=_short(brief["approved_cta"],"approved CTA",150)
    country=_short(brief["country"],"country",60)
    owner=_short(brief["evidence_owner"],"evidence owner",80)
    channels=brief["channels"]
    kinds=brief["content_kinds"]
    facts=brief["verified_facts"]
    if (type(channels) is not list or not 1<=len(channels)<=6 or
        any(type(x) is not str or x not in CHANNELS for x in channels) or
        len(set(channels))!=len(channels)):
        raise ContentHold("Unknown, duplicate or excessive channels")
    if (type(kinds) is not list or not 1<=len(kinds)<=len(KINDS) or
        any(type(x) is not str or x not in KINDS for x in kinds) or
        len(set(kinds))!=len(kinds)):
        raise ContentHold("Unknown, duplicate or excessive content kinds")
    if type(facts) is not list or not 1<=len(facts)<=MAX_FACTS:
        raise ContentHold("At least one verified business fact required")
    validated=[]
    for fact in facts:
        if type(fact) is not dict or set(fact)!={"claim","source_reference"}:
            raise ContentHold("Facts must include claim and source reference")
        claim=_short(fact["claim"],"fact",260)
        source=_short(fact["source_reference"],"fact source",300)
        validated.append({"claim":claim,"source_reference":source})
    digest=sha256(canonical(brief)).hexdigest()
    tasks=[]
    for kind in kinds:
        name,deliverable,caveat=KINDS[kind]
        for channel in channels:
            # Channel can be irrelevant to a format, but remains a content
            # *draft* target. An adapter must not schedule or publish it.
            direction=[
                f"Prepare a DRAFT {name.lower()} package for {channel}.",
                f"Brand: {brand}. Industry: {industry}. Country: {country}.",
                f"Offer: {offer}. Target audience: {audience}.",
                f"Business goal: {goal}. Approved CTA: {cta}.",
                f"Requested output: {deliverable}",
                "Ground every factual statement only in the following "
                "approved claims and evidence references:",
            ]
            direction += [f"- {f['claim']} [source: {f['source_reference']}]"
                          for f in validated]
            direction += [
                f"Accuracy constraint: {caveat}",
                "Never invent prices, proof of income, medical claims, statistics, "
                "customer reviews, quotes, external sources, testimonials, "
                "platform connectivity, consent or user rights.",
                "If evidence is missing, include a clearly marked evidence gap "
                "and suggest a factual alternative.",
                "Deliver proposed copy AND an explicit fact-check checklist, "
                "not a publication-ready claim of verified performance.",
                "No model invocation, media generation, publishing, "
                "scheduling or customer messaging is authorised here.",
            ]
            tasks.append({
                "id":f"{code}:{kind}:{channel}",
                "content_kind":kind,"channel":channel,
                "prompt":"\n".join(direction),
                "status":"DRAFT_UNGENERATED",
                "requires_factual_review":True,
                "requires_rights_review":kind in {"visual","video","ads"},
                "external_action_authorized":False,
            })
    return {
        "schema_version":1,"campaign_id":code,
        "brief_sha256":digest,
        "evidence_owner":owner,
        "work_orders":tasks,
        "generation_engine_connected":False,
        "model_outputs_created":False,
        "publication_authorized":False,
        "customer_messaging_authorized":False,
        "scheduling_authorized":False,
    }

def inspect_candidate(bundle:dict, work_order_id:str, candidate:str,
                      evidence_checked:bool, rights_checked:bool)->dict:
    """A human review *record*, never a publication authorisation."""
    if type(bundle) is not dict or type(bundle.get("work_orders")) is not list:
        raise ContentHold("Invalid work order bundle")
    targets=[x for x in bundle["work_orders"]
             if type(x) is dict and x.get("id")==work_order_id]
    if len(targets)!=1:
        raise ContentHold("Unknown or ambiguous content work order")
    target=targets[0]
    if target.get("status")!="DRAFT_UNGENERATED":
        raise ContentHold("Unsupported work order state")
    _short(candidate,"candidate text",12000,minimum=30)
    if type(evidence_checked) is not bool or type(rights_checked) is not bool:
        raise ContentHold("Human review flags must be boolean")
    approved=evidence_checked and (rights_checked or not target["requires_rights_review"])
    return {
        "work_order_id":work_order_id,
        "candidate_sha256":sha256(candidate.encode("utf-8")).hexdigest(),
        "review_status":"HUMAN_REVIEW_CLAIM_RECORDED_NOT_PUBLISHED"
                       if approved else "HOLD_UNVERIFIED_DRAFT",
        "actual_model_execution_verified":False,
        "publication_authorized":False,
        "scheduling_authorized":False,
    }
