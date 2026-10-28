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


def test_homepage_communicates_five_real_challenges_without_false_delivery_claims():
    html = (SITE / "index.html").read_text()
    p = page("index.html")
    assert "Real business challenges." in html
    assert "Clear next steps." in html
    assert "Development preview" in html
    assert "not an autonomous customer service" in html
    assert {"main", "solutions", "how"} & p.ids == {"solutions", "how"}
    assert "/workspace/" in p.refs
    assert "/engage/#project-chat-input" in p.refs
    assert "/creative/" in p.refs
    assert "#solutions" in p.refs
    assert "#how" in p.refs

def test_five_industry_sector_paths_map_to_workspace():
    html = (SITE / "index.html").read_text()
    assert html.count('class="solution"') == 5
    for key in ("sales", "healthcare", "realestate", "retail", "cloud"):
        assert f"/workspace/?sector={key}#home" in html
    for name in ("Sales &amp; Customers", "Healthcare", "Real Estate",
                 "Retail &amp; Inventory", "Cloud &amp; Enterprise IT"):
        assert name in html
    assert "Specialized integrations remain under development." in html

def test_home_has_small_solutions_list_instead_of_large_capability_catalog():
    html = (SITE / "index.html").read_text()
    assert 'class="solution-grid"' in html
    assert 'class="capability-card' not in html
    assert 'class="focus-sector-card"' not in html
    assert "Nine" not in html
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


def test_three_plain_language_steps_replace_seven_technical_tabs():
    html = (SITE / "index.html").read_text()
    assert 'class="how"' in html
    assert '<strong>Choose</strong>' in html
    assert '<strong>Plan</strong>' in html
    assert '<strong>Review</strong>' in html
    assert html.count('class="operation-tab') == 0
    assert 'src="/assets/site.js"' not in html

def test_deep_links_survive_without_restoring_old_sections():
    html = (SITE / "index.html").read_text()
    for anchor in ('id="solutions"', 'id="workspace-demo"',
                   'id="platform"', 'id="services"', 'id="industries"'):
        assert anchor in html
    for href in ('href="/workspace/"', 'href="/creative/"',
                 'href="/engage/#project-chat-input"'):
        assert href in html
    assert "No confusing dashboards or inflated AI claims." in html

def test_workspace_route_is_truthfully_scoped_to_local_preview():
    html = (SITE / "index.html").read_text()
    app = (SITE / "workspace/index.html").read_text()
    assert "browser-local development preview" in html
    assert "Nothing is uploaded, published" in app
    assert "Do not include names, patient records" in app
    assert "What would you like" in app
    assert "not a fake screenshot" not in html.lower()

def test_brand_and_navigation_preserve_existing_service_pages():
    for p in ("index.html", "services/index.html",
              "company/index.html", "engage/index.html"):
        html = (SITE / p).read_text()
        structure = page(p)
        assert "/assets/metaautomate-mark.webp" in html
        if p == "index.html":
            assert "/workspace/" in structure.refs
            assert "#solutions" in structure.refs
            assert "#how" in structure.refs
            assert 'class="product-tools shell"' not in html
        elif p == "engage/index.html":
            assert "/" in structure.refs
            assert "/creative/" in structure.refs
            assert 'id="workspace-sidebar-toggle"' in html
            assert 'id="brief-form"' not in html
        else:
            assert "/#solutions" in structure.refs
            assert "/#workspace-demo" in structure.refs
            assert "/company/" in structure.refs
            assert "/engage/" in structure.refs
        assert any(img.get("src") == "/assets/metaautomate-mark.webp"
                   for img in structure.images)
        for resource in structure.scripts:
            assert resource.get("src", "").startswith("/assets/")

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


def test_focused_homepage_cta_uses_dark_legible_blue_and_has_focus_states():
    css = (SITE / "assets/focused-home.css").read_text()
    assert "linear-gradient(95deg,#0780ca,#0ba4e7)" in css
    assert ":focus-visible" in css
    assert "prefers-reduced-motion" in css
    assert "@media(max-width:670px)" in css

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
