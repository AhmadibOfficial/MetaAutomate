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


def test_homepage_communicates_customer_offer_and_has_real_destinations():
    html = (SITE / "index.html").read_text()
    p = page("index.html")
    assert "Business challenges deserve" in html
    assert "smarter solutions" in html
    assert "Invest in clarity" in html
    assert "stronger client experiences" in html
    assert "Business owners &amp; founders" in html
    assert "Operations teams" in html
    assert {"solutions", "workspace-demo", "services", "industries", "platform"} <= p.ids
    assert html.index('id="solutions"') < html.index('id="workspace-demo"') < html.index('id="services"')
    assert "Explore our planning approach" in html
    assert "The right investment starts" in html
    assert "Give your team more time" in html
    assert "Build trust through quality" in html
    assert 'class="section proof-section"' not in html
    assert html.count('class="social-card social-') == 2
    assert html.count('class="footer-social-link"') == 8
    assert "/engage/#brief-form" in p.refs
    assert "#solutions" in p.refs
    assert "/services/#ai" in p.refs
    assert "/services/#data" in p.refs
    assert "/services/#security" in p.refs
    assert "/company/#roadmap" in p.refs


def test_seven_target_sectors_are_explicit_not_live_product_claims():
    home = (SITE / "index.html").read_text(encoding="utf-8")
    services = (SITE / "services/index.html").read_text(encoding="utf-8")
    assert home.count('class="focus-sector-card"') == 7
    for name in ("Retail", "Wholesale", "Transportation", "Logistics",
                 "Tourism", "Education", "Healthcare"):
        assert f"<h3>{name}</h3>" in home
        assert name.lower() in services.lower()
    for workflow in ("inventory", "sales", "customer follow-ups", "finance",
                     "operational decisions"):
        assert workflow in home.lower()
    assert "not deployed sector products" in home
    assert "not seven deployed sector platforms" in services
    assert "Agriculture, food security and Islamic knowledge systems" in home
    assert "no promise of guaranteed earnings" not in home.lower()
    assert "not a promise of guaranteed earnings" in home


def test_nine_capability_cards_are_scoped_and_link_to_real_disciplines():
    html = (SITE / "index.html").read_text(encoding="utf-8")
    structure = page("index.html")
    assert html.count('class="capability-card') == 9
    for name in (
        "AI Agents &amp; Orchestration", "Image &amp; Video Generation",
        "Social Media Automation", "Software Engineering",
        "Cybersecurity &amp; QA", "Data Analysis &amp; Research",
        "Cloud &amp; DevOps", "Business Automation",
        "Islamic Knowledge Systems",
    ):
        assert name in html
    for anchor in ("/services/#ai", "/services/#experience",
                   "/services/#software", "/services/#security",
                   "/services/#data", "/services/#cloud"):
        assert anchor in structure.refs
    assert "not nine live products" in html
    assert "scoped, reviewed and tested before live use" in html


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


def test_operating_philosophy_has_seven_non_operational_steps():
    html = (SITE / "index.html").read_text(encoding="utf-8")
    js = (SITE / "assets/site.js").read_text(encoding="utf-8")
    assert '02 / OUR OPERATING PHILOSOPHY' in html
    assert "understand, think, design, create, automate, verify and improve" in html
    assert html.count('class="operation-tab') == 7
    for number, name in enumerate(
        ("understand", "think", "design", "create", "automate", "verify", "improve"), 1
    ):
        assert f'id="tab-{name}"' in html
        assert f'data-operation="{name}"' in html
        assert f'number:"{number:02d} / 07"' in js
    assert 'id="operation-counter">01 / 07' in html
    assert "Customer operations and autonomous execution require independently verified controls" in html
    assert "explicit authorization" in html


def test_operating_use_cases_are_illustrative_complete_and_connected():
    html = (SITE / "index.html").read_text(encoding="utf-8")
    js = (SITE / "assets/site.js").read_text(encoding="utf-8")
    assert html.count('class="use-case-option') == 3
    for name in ("Inventory &amp; purchasing", "Content &amp; client engagement",
                 "Secure digital products"):
        assert name in html
    for code in ("inventory", "content", "mobile"):
        assert f'data-use-case="{code}"' in html
        assert f'    {code}: {{' in js
    for stage in ("understand", "think", "design", "create", "automate",
                  "verify", "improve"):
        assert js.count(f"        {stage}: ") == 3
    assert 'aria-live="polite"' in html
    assert "No live execution".lower() in html.lower()
    assert "Guided scenarios" in html
    assert "not customer testimonials" in html.lower()
    assert "Guided scenarios" in html or "Customer operations and autonomous execution require independently verified controls" in html


def test_workspace_example_is_truthful_fiction_not_a_fake_product_screenshot():
    html = (SITE / "index.html").read_text()
    assert "PLANNING EXPERIENCE" in html
    assert "illustrative information" in html
    assert "Guided planning scenario" in html
    assert "No orders, messages or external actions sent" in html
    assert "Objective Workspace brings goals" in html
    assert html.count("data-workspace-step=") == 3
    assert 'role="group" aria-label="Objective Workspace example steps"' in html
    assert 'aria-live="polite"' in html
    assert 'aria-pressed="true"' in html


def test_all_four_pages_keep_brand_and_navigate_to_website_solution_path():
    for p in ("index.html", "services/index.html",
              "company/index.html", "engage/index.html"):
        html = (SITE / p).read_text()
        structure = page(p)
        assert "/assets/metaautomate-mark.webp" in html
        assert "/#solutions" in structure.refs
        assert "/#workspace-demo" in structure.refs
        assert "/services/" in structure.refs
        assert "/company/" in structure.refs
        assert "/engage/" in structure.refs
        assert "Always HALAL" in html
        assert any(img.get("src") == "/assets/metaautomate-mark.webp"
                   for img in structure.images)
        for resource in structure.scripts:
            assert resource.get("src", "").startswith("/assets/")


def test_enquiry_is_email_draft_no_submission_or_external_form_action():
    html = (SITE / "engage/index.html").read_text()
    structure = page("engage/index.html")
    assert "Email a project question" in html
    assert "Tell us your business challenge" in html
    assert "value at stake" in html
    assert "What business challenge are you tackling?" in html
    assert "What value would a successful outcome create?" in html
    assert "investment in AI" in html
    assert "No account, automatic submission or server storage." in html
    assert len(structure.forms) == 1
    assert structure.forms[0].get("id") == "brief-form"
    assert not structure.forms[0].get("action")
    assert structure.forms[0].get("method", "").lower() != "post"
    assert any(x.startswith("mailto:metaautomating@gmail.com")
               for x in structure.refs)
    assert "Nothing is sent until" in html or "Nothing is sent" in html
    assert "Do not include passwords" in html



def test_company_roadmap_does_not_misrepresent_source_as_live_execution():
    content = (SITE / "company/index.html").read_text(encoding="utf-8")
    assert "Our roadmap describes active engineering" in content
    assert "Customer access, provider integrations" in content
    assert "documented security" in content
    assert "subscriptions will follow documented security" in content
    assert "customer access" in content.lower()
    assert "<small>PLANNED</small>" not in content


def test_primary_website_ctas_do_not_use_white_on_bright_cyan():
    css = (SITE / "assets/site.css").read_text(encoding="utf-8")
    assert "/* Publication accessibility review:" in css
    accessibility = css.split("/* Publication accessibility review:", 1)[1]
    assert "linear-gradient(115deg,#005caa,#0063b2)" in accessibility
    assert "linear-gradient(110deg,#005caa,#0063b2)" in accessibility
    assert ".eyebrow:not(.eyebrow-dark){color:#006aa3}" in accessibility
    assert ".clarity-index,.workspace-demo-kicker{color:#00679c}" in accessibility

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
