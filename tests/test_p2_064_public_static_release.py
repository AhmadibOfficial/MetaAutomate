"""Public static website release P2-064; source-only contract and accessibility checks."""
from html.parser import HTMLParser
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "apps" / "site"
HOME = (SITE / "index.html").read_text("utf-8")
WORK = (SITE / "workspace/index.html").read_text("utf-8")
JS = (SITE / "assets/unified-workspace.js").read_text("utf-8")
CSS = (SITE / "assets/unified-workspace.css").read_text("utf-8")
ENGINE = (SITE / "assets/campaign-engine.js").read_text("utf-8")

PACK_IDS = (
    "wholesale", "transportation", "logistics", "tourism", "hospitality",
    "education", "manufacturing", "agriculture", "construction",
    "financial_operations", "telecommunications", "energy_utilities",
    "public_services", "legal_professional", "media_marketing",
    "nonprofit", "custom_operations",
)

def test_approved_brand_and_responsive_goals():
    for name, code in (
        ("navy", "#081c36"), ("blue", "#0788d2"),
        ("gold", "#e9b84f"), ("silver", "#e2e9f1")
    ):
        assert code in CSS.lower(), name
    for name in ("customer", "operations", "finance", "automation", "insights"):
        assert f'data-goal="{name}"' in WORK
    assert WORK.count('class="goal-card"') == 5
    assert 'aria-label="Choose an objective"' in WORK
    assert ".goal-card[aria-pressed=true]" in CSS
    assert "@media(max-width:600px)" in CSS
    assert "prefers-reduced-motion" in CSS

def test_industry_expansion_is_navigation_not_customer_automation():
    assert WORK.count('class="sector-card"') == 5
    assert WORK.count('<option value="') == len(PACK_IDS) + 1  # includes the empty placeholder
    for pack in PACK_IDS:
        assert f'<option value="{pack}">' in WORK
        assert f'"{pack}"' in JS
    assert 'id="more-industries"' in WORK
    assert "Object.assign(industries, extraIndustries)" in JS
    assert "objectiveFamilies[selectedGoal].steps.map" in JS
    assert "Every industry. One simple starting point." in HOME

def test_security_review_and_local_only_boundaries():
    assert "connect-src 'none'" in WORK
    assert "form-action 'none'" in WORK
    assert "frame-src 'none'" in WORK
    assert "Nothing is uploaded, published" in WORK
    assert 'id="complete-plan" disabled' in WORK
    assert "plan.steps.every(step=>step.done)" in JS
    assert "outsideActionsPerformed:false" in JS
    assert "aiModelUsed:false" in JS
    assert "sourceAuthenticated:false" in JS
    assert "plan.reviewed=true" in JS
    assert "No live AI, customer accounts or external integrations" in WORK
    for banned in ("fetch(", "XMLHttpRequest", "WebSocket(", "localStorage",
                   "sessionStorage", ".innerHTML", "eval("):
        assert banned not in JS
    assert "module.exports" in ENGINE
    assert "parseCSV" in ENGINE and "analyze" in ENGINE
    assert "makeCampaign" in ENGINE

def test_unique_ids_and_all_assets_local():
    for source in (HOME, WORK):
        ids = re.findall(r'\bid="([^"]+)"', source)
        assert len(ids) == len(set(ids))
    for file in (
        "assets/metaautomate-mark.webp",
        "assets/focused-home.css",
        "assets/campaign-engine.js",
        "assets/unified-workspace.css",
        "assets/unified-workspace.js",
        "creative/index.html", "engage/index.html"
    ):
        assert (SITE / file).is_file(), file
    linked_ids = set(re.findall(r'\$\("([a-z0-9-]+)"\)', JS))
    page_ids = set(re.findall(r'\bid="([^"]+)"', WORK))
    assert linked_ids <= page_ids, linked_ids - page_ids
    assert 'href="/creative/"' in HOME
    assert 'href="/engage/#project-chat-input"' in HOME
