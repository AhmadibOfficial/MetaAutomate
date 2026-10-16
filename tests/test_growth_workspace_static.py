"""Static Growth Autopilot customer demo: truthful, data-consistent, zero-external effects."""
from html.parser import HTMLParser
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "apps/site/automation"
FIXTURE = ROOT / "contracts/domains/v1/fixtures/synthetic_growth_autopilot.v1.json"


class ElementParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.scripts = []
        self.links = []
        self.forms = 0
        self.titles = []
        self.tabs = []
        self.panels = []
        self.buttons = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "form":
            self.forms += 1
        if tag == "script":
            self.scripts.append(attrs.get("src", ""))
        if tag == "link" and attrs.get("rel") == "stylesheet":
            self.links.append(attrs.get("href", ""))
        if tag == "button":
            self.buttons.append(attrs)
        if attrs.get("role") == "tab":
            self.tabs.append(attrs)
        if attrs.get("role") == "tabpanel":
            self.panels.append(attrs)


def content():
    html = (SITE / "index.html").read_text(encoding="utf-8")
    css = (SITE / "workspace.css").read_text(encoding="utf-8")
    js = (SITE / "workspace.js").read_text(encoding="utf-8")
    structure = ElementParser()
    structure.feed(html)
    return html, css, js, structure


def test_static_demo_is_navigable_and_discoverable_but_not_live():
    html, css, js, p = content()
    assert (ROOT / "apps/site/index.html").read_text().count(
        'href="/automation/"'
    ) == 1
    assert p.scripts == ["/automation/engine-snapshot.js", "/automation/workspace.js"]
    assert "/automation/workspace.css" in p.links
    assert len(p.ids) == len(set(p.ids))
    assert p.forms == 0
    assert "Growth Autopilot — MetaAutomate" in html
    assert 'href="/"' in html
    assert 'href="/engage/"' in html
    assert 'class="skip"' in html and 'href="#workspace-main"' in html
    assert "Growth Autopilot / Product Preview" in html
    assert "Subscription access requires a separate commercial launch" in html
    assert "Interactive product preview" in html
    assert "ILLUSTRATIVE FIGURES" in html
    assert "customer accounts are not connected" in html
    assert "not actual sales or currency conversions" in html
    assert "$9/mo" not in html and "$29/mo" not in html
    assert "₦" not in html
    assert "not net profit" in html
    assert "Responsible automation by design" in html
    assert "F04–F09" not in html
    assert "NO-GO" not in html
    customer_copy = re.sub(r"<[^>]+>", " ", html).lower()
    assert not re.search(r"\b(demo|fictional)\b", customer_copy)
    assert "figures are illustrative" in customer_copy
    assert "Choose a business scenario" in html
    assert "subscription" in html.lower()
    assert "customer accounts are not connected" in html


def test_every_workflow_view_is_keyboard_accessible_and_semantic():
    html, css, js, structure = content()
    assert len(structure.tabs) == 4
    assert len(structure.panels) == 4
    assert {x["data-view"] for x in structure.tabs} == {
        "overview", "automations", "value", "setup"
    }
    assert {x["id"] for x in structure.panels} == {
        "panel-overview", "panel-automations", "panel-value", "panel-setup"
    }
    assert all(x["aria-controls"] in structure.ids for x in structure.tabs)
    assert all(x["aria-labelledby"] in structure.ids for x in structure.panels)
    assert all(x.get("type") == "button" for x in structure.buttons)
    assert 'aria-live="polite"' in html
    assert 'aria-orientation="vertical"' in html
    for key in ("ArrowDown", "ArrowRight", "ArrowUp", "ArrowLeft", "Home", "End"):
        assert key in js
    assert "setAttribute" in js and 'aria-selected' in js
    assert "focus-visible" in css
    assert "prefers-reduced-motion" in css
    for dimension in ("1180px", "900px", "610px"):
        assert dimension in css


def test_sample_metrics_and_trigger_references_match_committed_synthetic_fixture():
    html, css, js, structure = content()
    f = json.loads(FIXTURE.read_text())
    assert f["classification"] == "SYNTHETIC_DEMO_ONLY"
    assert f["currency"] == "DEMO_CREDITS"
    assert len(f["workspaces"]) == 2
    for group in f["workspaces"]:
        assert group["workspace"] in js
        assert str(group["goal_target_demo_credits"]) in js
        assert str(group["marketing_spend_demo_credits"]) in js
        for product in group["products"]:
            assert product["product_id"] in js
            assert "price:" + str(product["unit_price_demo_credits"]) in js
            assert "cost:" + str(product["variable_cost_demo_credits"]) in js
        for order in group["orders"]:
            assert order["order_id"] in js
            assert order["journey_id"] in js
        for event in group["events"]:
            assert event["event_id"] in js
            assert event["event_type"] in js
            marker = "consent:" + str(event["consent_status"] == "SYNTHETIC_OPTED_IN").lower()
            assert marker in js
    assert "academy_demo" in html and "bespoke_demo" in html
    assert 'value="contribution"' in html
    assert 'value="repeat"' in html
    assert 'value="orders"' in html
    assert "modeled" in html.lower()
    assert "caused" not in html.lower() or "not" in html.lower()


def test_demo_never_calls_api_sends_message_processes_payment_or_stores_client_data():
    html, css, js, structure = content()
    prohibited = (
        "fetch(", "XMLHttpRequest(", "WebSocket(", "sendBeacon(",
        "localStorage.", "sessionStorage.", "document.cookie",
        "navigator.serviceWorker", "postMessage(", "window.open(",
        "stripe", "paypal", "api.selar.com", "api.metricool.com",
    )
    for token in prohibited:
        assert token not in js, token
    assert "queue.replaceChildren" in js
    assert "document.createElement" in js
    assert "textContent" in js
    assert "SUPPRESSED_PROVIDER_OWNS" in js
    assert "SUPPRESSED_NO_MARKETING_CONSENT" in js
    assert "REVIEW_REQUIRED" in js
    assert 'human approval' in html.lower() or 'human in control' in html.lower()
    assert 'business.value' in js
    assert "Designed for decisions that matter" in html
    assert "In development" in html
    assert "Subscription access requires a separate commercial launch" in html
    assert "does not execute those actions" in html


def test_official_brand_logo_used_and_css_is_light_first_without_external_fetches():
    html, css, js, p = content()
    assert '/assets/metaautomate-mark.webp' in html
    assert "color-scheme:light" in css
    assert "--paper:#fff" in css
    assert "font:" in css
    assert not re.search(r"@import|url\(['\"]?https?://", css, re.I)
    assert not re.search(r'<script[^>]+src=["\']https?://', html, re.I)
    assert 'rel="icon"' in html
    assert 'name="viewport"' in html
