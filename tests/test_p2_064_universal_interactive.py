"""P2-064 — static safety, accessible navigation, exact brand and domain-pack parity.
These checks validate committed source only. They do not assert a live deployment,
real browser acceptance, model inference, or independent customer outcomes.
"""
from __future__ import annotations
from html.parser import HTMLParser
from pathlib import Path
import json
import re
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "apps" / "site"
MARKETING = SITE / "index.html"
WORKSPACE = SITE / "universal" / "index.html"
LANDING_CSS = SITE / "assets" / "universal-landing.css"
WORKSPACE_CSS = SITE / "assets" / "universal-workspace.css"
LANDING_JS = SITE / "assets" / "universal-landing.js"
WORKSPACE_JS = SITE / "assets" / "universal-workspace.js"
PACKS = ROOT / "contracts" / "domains" / "v2" / "domain-packs.v1.json"

GOALS = ("customers", "operations", "costs", "automation", "insights")
PAGES = ("home", "work", "results", "settings")
PALETTE = ("#040D20", "#00A7ED", "#DCE6F1", "#EFB94F")

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.scripts = []
        self.css = []
        self.links = []
        self.attrs = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.attrs.append((tag, a))
        if a.get("id"):
            self.ids.append(a["id"])
        if tag == "script":
            self.scripts.append(a.get("src"))
        if tag == "link" and a.get("rel") == "stylesheet":
            self.css.append(a.get("href"))
        if tag == "a":
            self.links.append(a.get("href"))

def page(path: Path):
    html=path.read_text("utf-8")
    parsed=Page()
    parsed.feed(html)
    assert len(parsed.ids)==len(set(parsed.ids)), "Duplicate element IDs"
    assert "connect-src 'none'" in html
    assert "form-action 'none'" in html
    assert "default-src 'self'" in html
    assert not re.search(r'<script[^>]+src="https?://',html)
    assert not re.search(r'<link[^>]+href="https?://',html)
    return html, parsed

def test_universal_workflow_home_has_five_goal_options_and_four_views():
    html, dom = page(WORKSPACE)
    assert {a["data-goal"] for tag,a in dom.attrs if "data-goal" in a} == set(GOALS)
    assert {a["data-route"] for tag,a in dom.attrs if tag=="a" and "data-route" in a
            and a.get("href","#").startswith("#")}==set(PAGES)
    assert all(f'id="view-{view}"' in html for view in PAGES)
    assert "What would you like to" in html
    assert 'id="industry"' in html
    assert 'id="custom-sector"' in html
    assert 'id="project-form"' in html
    assert 'id="workflow-list"' in html
    assert 'id="workflow-steps"' in html
    assert 'id="review-confirm"' in html
    assert 'id="complete-workflow"' in html
    assert 'id="export-report"' in html
    assert 'id="clear-session"' in html

def test_universal_pack_selection_is_derived_from_source_catalog_not_five_limit():
    js=WORKSPACE_JS.read_text("utf-8")
    catalog=json.loads(PACKS.read_text("utf-8"))
    match=re.search(r'const SECTORS = Object.freeze\((\[[^\n]*\])\);',js)
    assert match, "Missing compiled domain-pack options"
    sectors=json.loads(match.group(1))
    expected=[{"value":p["id"],"label":p["label"]} for p in catalog["profiles"]]
    assert sectors==expected
    assert len(sectors)>=20
    assert {"custom_operations", "agriculture", "logistics", "manufacturing"} <= {
        item["value"] for item in sectors}
    assert all(p["status"]=="DESIGN_ONLY" and not p["enabled"] and
               not p["production_ready"] for p in catalog["profiles"])
    assert "selector.value" in js and "custom-sector-group" in js
    assert '"custom_operations"' in js

def test_human_approval_not_equivalent_to_executed_action():
    html,_=page(WORKSPACE)
    js=WORKSPACE_JS.read_text("utf-8")
    for text in (
        "No connected AI, customer accounts, external execution or automatic publishing.",
        "not an executed business operation",
        "Creating or reviewing a workflow alone does not prove",
        "Review is required before completion is recorded."
    ):
        assert text in html
    assert 'plan.steps.every(s=>s.done)' in js
    assert '!$("review-confirm").checked' in js
    assert "externalExecutionPerformed:false" in js
    assert "financialSavingsVerified:false" in js
    assert "independentVerification:false" in js
    assert "aiProviderUsed:false" in js
    assert 'if(items.length>=12)' in js
    assert '"LOCAL_TAB_ONLY"' in js
    assert "localStorage" not in js and "sessionStorage" not in js

def test_four_signature_colors_responsive_and_reduced_motion():
    for css_path in (WORKSPACE_CSS,LANDING_CSS):
        css=css_path.read_text("utf-8")
        for color in PALETTE:
            assert color in css, (css_path,color)
        assert ":focus-visible" in css
        assert "prefers-reduced-motion" in css
        assert "@media(max-width:" in css
        assert "color:var(--midnight)" in css
        assert len(css.encode("utf-8"))<30*1024

def test_public_homepage_interaction_is_real_and_local():
    html,dom=page(MARKETING)
    js=LANDING_JS.read_text("utf-8")
    assert 'href="/universal/"' in html
    assert len([1 for tag,a in dom.attrs if tag=="button" and "data-goal" in a])==5
    assert dom.scripts==["/assets/universal-landing.js"]
    assert dom.css==["/assets/universal-landing.css"]
    assert {x for x in ("solutions","how","workspace-demo","services","industries","platform")
            if x in dom.ids}=={"solutions","how","workspace-demo","services","industries","platform"}
    assert 'link.href="/universal/?goal="+key' in js
    assert 'button.addEventListener("click"' in js
    assert 'button.addEventListener("keydown"' in js
    assert 'aria-pressed' in js

def test_no_network_storage_or_dom_injection():
    _,dom=page(WORKSPACE)
    assert dom.scripts==["/assets/universal-workspace.js"]
    assert dom.css==["/assets/universal-workspace.css"]
    for path in (LANDING_JS,WORKSPACE_JS):
        s=path.read_text("utf-8")
        for forbidden in ("fetch(", "XMLHttpRequest", "WebSocket(", "sendBeacon(",
                          "localStorage", "sessionStorage", "document.cookie",
                          ".innerHTML", ".outerHTML", "eval(", "new Function("):
            assert forbidden not in s,(path,forbidden)
        assert "textContent" in s
    scripts=WORKSPACE_JS.read_text("utf-8")
    ids=set(dom.ids)
    targets=set(re.findall(r'\$\("([a-z0-9-]+)"\)',scripts))
    assert targets <= ids, "Missing DOM IDs: "+repr(targets-ids)

@pytest.mark.skipif(shutil.which("node") is None,reason="Node.js not available")
def test_scripts_parse_in_node():
    for file in (LANDING_JS,WORKSPACE_JS):
        result=subprocess.run(["node","--check",str(file)],
            cwd=ROOT,text=True,capture_output=True,timeout=20)
        assert result.returncode==0,result.stdout+result.stderr
