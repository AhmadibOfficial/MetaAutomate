"""P2-062c: fail-closed offline contract for task-first five-industry workspace."""
from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "apps/site/workspace/index.html"
JS = ROOT / "apps/site/assets/unified-workspace.js"
CSS = ROOT / "apps/site/assets/unified-workspace.css"
ENGINE = ROOT / "apps/site/assets/campaign-engine.js"

class SourceHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.routes = []
        self.sectors = []
        self.scripts = []
        self.forms = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.append(a["id"])
        if "data-route" in a:
            self.routes.append((a["data-route"], a.get("href")))
        if "data-sector" in a:
            self.sectors.append(a["data-sector"])
        if tag == "script":
            self.scripts.append(a)
        if tag == "form":
            self.forms.append(a)

@pytest.fixture(scope="module")
def source():
    assert all(p.is_file() and p.stat().st_size > 100 for p in (HTML, JS, CSS, ENGINE))
    page, code, style = [p.read_text(encoding="utf-8") for p in (HTML, JS, CSS)]
    parsed = SourceHTML()
    parsed.feed(page)
    return page, code, style, parsed

def test_only_four_clear_main_views(source):
    page, code, _, parsed = source
    routes = ("home", "work", "results", "settings")
    assert {name for name, _ in parsed.routes} == set(routes)
    assert set(parsed.routes) == {(n, "#" + n) for n in routes}
    assert all('id="view-' + n + '"' in page for n in routes)
    assert 'id="view-modules"' not in page
    assert 'id="view-readiness"' not in page
    assert 'id="view-evidence"' not in page
    assert "What would you like" in page
    assert "to <em>improve today?" in page
    assert "My Work" in page and "Results" in page and "Team &amp; Settings" in page

def test_five_specific_industries_not_generic_placeholders(source):
    page, code, _, parsed = source
    assert sorted(parsed.sectors) == sorted([
        "sales", "healthcare", "realestate", "retail", "cloud"
    ])
    for text in ["Sales &amp; Customers", "Healthcare", "Real Estate",
                 "Retail &amp; Stock", "Cloud &amp; IT"]:
        assert text in page
    for key in parsed.sectors:
        assert key + ":" in code
    assert '"plan-review"' in code and '"complete-plan"' in code
    assert 'plan.steps.every(step=>step.done)' in code
    assert 'outsideActionsPerformed:false' in code

def test_sources_valid_and_no_dom_injection_or_network(source):
    page, code, style, parsed = source
    assert len(parsed.ids) == len(set(parsed.ids)), "Duplicate HTML IDs"
    js_ids = set(re.findall(r'\$\("([a-z0-9-]+)"\)', code))
    assert js_ids <= set(parsed.ids), "Unknown DOM IDs: " + repr(js_ids - set(parsed.ids))
    assert {s.get("src") for s in parsed.scripts} == {
        "/assets/campaign-engine.js", "/assets/unified-workspace.js"}
    assert "connect-src 'none'" in page
    assert "form-action 'none'" in page and "frame-src 'none'" in page
    assert "Nothing is uploaded, published" in page
    assert all("action" not in form and "method" not in form for form in parsed.forms)
    for banned in ("fetch(", "XMLHttpRequest", "WebSocket(", "localStorage",
                   "sessionStorage", ".innerHTML", "eval(", "new Function("):
        assert banned not in code, banned
    for color in ("#081c36", "#0788d2", "#e9b84f", "#e2e9f1"):
        assert color in style.lower()

def test_real_stock_engine_and_human_draft_guard(source):
    _, code, _, _ = source
    for part in ('engine.parseCSV(text)', 'engine.analyze(data)', 'engine.makeCampaign(',
                 'new TextDecoder("utf-8",{fatal:true})',
                 'token!==generation', 'dropDraft()', 'function revokeDraft()',
                 'if(!planDraft||!approvedDraft)return', 'sourceAuthenticated:false',
                 'aiModelUsed:false', 'externalPublishingPerformed:false',
                 'signed:false', 'generateAtUntrusted'):
        if part == "generateAtUntrusted":
            assert "generatedAtUntrustedClientClock" in code
        else:
            assert part in code


def test_focused_public_homepage_links_all_five_industries():
    home = (ROOT / "apps/site/index.html").read_text("utf-8")
    css = (ROOT / "apps/site/assets/focused-home.css").read_text("utf-8")
    assert "Real business challenges." in home
    assert "Every industry." in home
    assert "/workspace/" in home
    for key in ("sales", "healthcare", "realestate", "retail", "cloud"):
        assert '/workspace/?sector=' + key + '#home' in home
    assert "connect-src 'none'" in home
    assert 'href="/assets/focused-home.css"' in home
    assert "min-width:0" not in css or "solution-grid" in css
    assert "Objective Workspace" not in home
    assert "capability-grid" not in home
    assert "AI model-generated" not in home

def test_local_chromium_harness_covers_all_five_sectors_separately():
    harness = (ROOT / "scripts/verify_unified_workspace_browser.py").read_text("utf-8")
    assert "for sector, challenge in business_cases:" in harness
    for key in ("sales", "healthcare", "realestate", "retail", "cloud"):
        assert f'("{key}",' in harness
    assert 'page.locator("#clear-session").click()' in harness
    assert 'assert page.locator("#results-reviewed").inner_text() == "1"' in harness
    assert 'assert page.locator("#results-reviewed").inner_text() == "0"' in harness
    assert 'No customer' not in harness or 'synthetic' in harness.lower()


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not installed")
def test_js_syntax_and_existing_inventory_regression():
    for path in (JS, ENGINE):
        result = subprocess.run(["node", "--check", str(path)], cwd=ROOT, text=True,
                                capture_output=True, timeout=20)
        assert result.returncode == 0, result.stdout + result.stderr
    result = subprocess.run(["node", "--test", "tests/campaign_engine.test.cjs"],
                            cwd=ROOT, text=True, capture_output=True, timeout=40)
    assert result.returncode == 0, result.stdout + result.stderr
