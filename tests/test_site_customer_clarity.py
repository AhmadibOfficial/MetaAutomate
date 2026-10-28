"""MetaAutomate customer-clarity site: copy, privacy, asset budget and navigation.

These source-level checks complement Playwright real Chromium acceptance.
No hosted service, real customer account, or product execution is required.
"""
from pathlib import Path
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "apps" / "site"


class PageStructure(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.refs = []
        self.forms = []
        self.images = []
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "a":
            self.refs.append(attrs.get("href", ""))
        if tag == "form":
            self.forms.append(attrs)
        if tag == "img":
            self.images.append(attrs)
        if tag == "script":
            self.scripts.append(attrs)


def page(path: str) -> PageStructure:
    content = (SITE / path).read_text(encoding="utf-8")
    parser = PageStructure()
    parser.feed(content)
    return parser


def test_homepage_communicates_universal_value_without_overpromising():
    html=(SITE/"index.html").read_text()
    p=page("index.html")
    assert "Your business is complex." in html
    assert "Your next move" in html
    assert "One workspace" in html
    assert "What would you like to improve?" in html
    assert "Live AI agents, customer integrations and automated external actions are not enabled." in html
    assert "/universal/" in p.refs
    assert "#solutions" in p.refs and "#how" in p.refs
    assert "/creative/" in p.refs and "/workspace/" in p.refs

def test_homepage_selects_five_goals_without_hardcoding_five_sectors():
    html=(SITE/"index.html").read_text()
    assert html.count('class="focus-card"')==5
    for key in ("customers","operations","costs","automation","insights"):
        assert f'data-goal="{key}"' in html
    assert "No industry limit." in html
    assert "Room for every industry." in html
    assert 'id="focus-start"' in html

def test_home_has_focused_interaction_not_capability_directory():
    html=(SITE/"index.html").read_text()
    assert 'class="focus-grid"' in html
    assert 'class="capability-card' not in html
    assert 'class="focus-sector-card"' not in html
    assert 'id="workspace-demo"' in html
    assert "review" in html.lower() and "workspace" in html.lower()

def test_evolution_roadmap_distinguishes_delivery_from_long_term_aspiration():
    html = (SITE / "company/index.html").read_text(encoding="utf-8")
    assert html.count('class="roadmap-entry') == 4
    for phase in ("PHASE 01", "PHASE 02", "PHASE 03", "PHASE 04"):
        assert phase in html
    assert "Engineering a better world, one milestone at a time." in html
    assert "A Better World." in html
    assert "OUR LONG-TERM AMBITION" in html
    assert "ENGINEERING FOUNDATION IN PROGRESS" in html
    assert "INTEGRATION ENGINEERING IN PROGRESS" in html
    assert "Customer activation follows independent security and operational review." in html
    assert "International readiness" in html


def test_three_clear_steps_replace_technical_tabs():
    html=(SITE/"index.html").read_text()
    for phrase in ("Understand your challenge","Organize an actionable workflow","Build trust through evidence"):
        assert phrase in html
    assert html.count('class="visual-card"')==3
    assert html.count('class="operation-tab')==0
    assert 'src="/assets/site.js"' not in html

def test_deep_links_survive_without_restoring_old_sections():
    html=(SITE/"index.html").read_text()
    for anchor in ('id="solutions"','id="workspace-demo"',
                   'id="platform"','id="services"','id="industries"'):
        assert anchor in html
    for href in ('href="/universal/"','href="/creative/"',
                 'href="/engage/#project-chat-input"','href="/workspace/"'):
        assert href in html
    assert "One connected experience".lower() in html.lower()

def test_universal_workspace_has_clear_action_and_privacy_boundaries():
    home=(SITE/"index.html").read_text()
    universal=(SITE/"universal/index.html").read_text()
    assert "Create and review" in home or "create a clear plan" in home
    assert "No connected AI, customer accounts, external execution or automatic publishing." in universal
    assert "sample or non-sensitive information" in universal
    assert "What would you like to" in universal
    assert "External actions disabled" in universal

def test_brand_and_navigation_preserve_existing_service_pages():
    for p in ("index.html","services/index.html","company/index.html","engage/index.html"):
        html=(SITE/p).read_text()
        structure=page(p)
        assert "/assets/metaautomate-mark.webp" in html
        if p=="index.html":
            assert "/universal/" in structure.refs
            assert "#solutions" in structure.refs and "#how" in structure.refs
            assert 'class="product-tools shell"' not in html
        elif p=="engage/index.html":
            assert "/" in structure.refs and "/creative/" in structure.refs
            assert 'id="workspace-sidebar-toggle"' in html
            assert 'id="brief-form"' not in html
        else:
            assert "/#solutions" in structure.refs
            assert "/#workspace-demo" in structure.refs
            assert "/company/" in structure.refs
            assert "/engage/" in structure.refs
        assert any(img.get("src")=="/assets/metaautomate-mark.webp" for img in structure.images)
        for resource in structure.scripts:
            assert resource.get("src","").startswith("/assets/")

def test_project_chat_replaces_old_enquiry_with_local_mail_draft():
    html = (SITE / "engage/index.html").read_text()
    structure = page("engage/index.html")
    assert "What would you like to build today?" in html
    assert "Tell me your project idea." in html
    assert 'id="project-chat-input"' in html
    assert 'id="project-chat-summary"' in html
    assert 'id="project-chat-email"' in html
    assert 'id="workspace-sidebar-toggle"' in html
    assert 'id="brief-form"' not in html
    assert "Prefer a structured project form?" not in html
    assert not structure.forms
    assert any(x.startswith("mailto:metaautomating@gmail.com")
               for x in structure.refs)
    assert "Nothing is sent" in html
    assert "confidential" in html.lower()


def test_company_roadmap_does_not_misrepresent_source_as_live_execution():
    content = (SITE / "company/index.html").read_text(encoding="utf-8")
    assert "Our roadmap describes active engineering" in content
    assert "Customer access, provider integrations" in content
    assert "documented security" in content
    assert "subscriptions will follow documented security" in content
    assert "customer access" in content.lower()
    assert "<small>PLANNED</small>" not in content


def test_four_brand_colors_and_accessibility_are_applied():
    css=(SITE/"assets/universal-landing.css").read_text()
    for color in ("#040D20","#00A7ED","#DCE6F1","#EFB94F"):
        assert color in css
    assert ":focus-visible" in css
    assert "prefers-reduced-motion" in css
    assert "@media(max-width:550px)" in css
    assert "color:var(--midnight)" in css

def test_website_assets_have_size_budgets_and_no_third_party_dependencies():
    css = (SITE / "assets" / "site.css").read_bytes()
    js = (SITE / "assets" / "site.js").read_bytes()
    assert len(css) <= 64 * 1024, f"Site CSS size increased unexpectedly: {len(css)}"
    assert len(js) <= 18 * 1024, f"Site JS size increased unexpectedly: {len(js)}"
    assert len((SITE / "index.html").read_bytes()) <= 38 * 1024
    source = js.decode("utf-8")
    assert "fetch(" not in source
    assert "XMLHttpRequest" not in source
    assert "localStorage" not in source
    assert "sessionStorage" not in source
    assert "document.cookie" not in source
    for p in ("index.html", "services/index.html",
              "company/index.html", "engage/index.html"):
        html = (SITE / p).read_text()
        assert not re.search(r'<script[^>]+src="https?://', html)
        assert not re.search(r'<link[^>]+href="https?://', html)
