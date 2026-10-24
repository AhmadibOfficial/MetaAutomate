"""P2-060c source-only regression guards: accessibility by design, not certification.

Run real Chromium verification separately. These tests need no Playwright
installation, paid provider, database, network or locally saved screenshots.
"""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "apps/site/campaigns/index.html"
CSS = ROOT / "apps/site/assets/campaign-workbench.css"
UI = ROOT / "apps/site/assets/campaign-workbench.js"
VERIFY = ROOT / "scripts/verify_campaign_accessibility.py"


class Tags(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def markup():
    parsed = Tags()
    parsed.feed(HTML.read_text(encoding="utf-8"))
    return parsed.tags


def by_id(element_id):
    matches = [(tag, attrs) for tag, attrs in markup() if attrs.get("id") == element_id]
    assert len(matches) == 1, element_id
    return matches[0]


def test_skip_link_and_focusable_landmarks():
    html = HTML.read_text(encoding="utf-8")
    assert 'class="skip" href="#main"' in html
    tag, attributes = by_id("main")
    assert tag == "main"
    assert attributes["tabindex"] == "-1"
    for heading in ("results-title", "project-title"):
        tag, attributes = by_id(heading)
        assert tag == "h2"
        assert attributes["tabindex"] == "-1"


def test_media_preview_has_actual_descriptive_text_target():
    tag, attributes = by_id("campaign-canvas")
    assert tag == "canvas"
    assert attributes["role"] == "img"
    assert attributes["aria-describedby"] == "campaign-graphic-description"
    tag, _ = by_id("campaign-graphic-description")
    assert tag == "p"


def test_all_workflow_inputs_have_associated_label_or_legend():
    tags = markup()
    labels = {attrs.get("for") for tag, attrs in tags if tag == "label"}
    inputs = [
        attrs for tag, attrs in tags if tag in {"input", "textarea", "select"}
        and attrs.get("type") not in {"checkbox", "radio"}
    ]
    for attrs in inputs:
        assert attrs.get("id") in labels, attrs
    tag, attrs = by_id("campaign-status")
    assert tag == "p" and attrs["aria-live"] == "polite"
    assert attrs["role"] == "status"


def test_focus_outline_uses_dark_color_on_light_and_gold_on_dark():
    css = CSS.read_text(encoding="utf-8")
    assert ":focus-visible{outline:3px solid var(--navy)" in css
    assert ".topbar :is(button,a,input,select,textarea):focus-visible" in css
    assert "outline-color:var(--gold)" in css
    assert ':where(main,h2)[tabindex="-1"]:focus' in css
    assert "@media(prefers-reduced-motion:reduce)" in css


def test_dynamic_focus_and_approval_revocation_are_reachable():
    js = UI.read_text(encoding="utf-8")
    for required in (
        'el("results-title").focus();',
        'el("project-title").focus();',
        'el("campaign-graphic-description").textContent =',
        'el("campaign-graphic-description").textContent = "No campaign graphic prepared.";',
        'el("campaign-confirm").checked = false',
        "function revokeApproval()",
        'approval = metrics = null;',
        'publishPerformed: false',
        'aiModelUsed: false',
    ):
        assert required in js, required


def test_playwright_accessibility_gate_is_local_and_not_wide_claim():
    source = VERIFY.read_text(encoding="utf-8")
    assert "serve_local()" in source
    assert "same_origin(route.request.url, base)" in source
    assert "launch_full_chromium(pw)" in source
    assert 'page.keyboard.press("Tab")' in source
    assert 'page.keyboard.press("Enter")' in source
    assert 'page.keyboard.press("Space")' in source
    assert 'focus_outline(page, ".skip"' in source
    assert 'focus_outline(page, "#campaign-create"' in source
    assert 'DEVELOPER_LOCAL_ACCESSIBILITY_AUTOMATION_PASS' in source
    assert 'NOT independent WCAG' in source
    for forbidden in ("fetch(", "requests.get(", "urlopen(", "social_publish("):
        assert forbidden not in source
