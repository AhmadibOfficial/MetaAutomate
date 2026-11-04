"""P2-065 Command Center static, safety and layout source contracts.

A passing source test does not prove mobile usability or backend authorization.
Run scripts/verify_command_center_browser.py for real browser acceptance.
"""
from pathlib import Path
import json
import re
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"apps/site"
HTML=(SITE/"command/index.html").read_text("utf-8")
JS=(SITE/"assets/command-center.js").read_text("utf-8")
CSS=(SITE/"assets/command-center.css").read_text("utf-8")

class ContractParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=[]
        self.hrefs=[]
        self.tags=[]
    def handle_starttag(self,tag,attrs):
        x=dict(attrs)
        self.tags.append(tag)
        if "id" in x:self.ids.append(x["id"])
        if "href" in x:self.hrefs.append(x["href"])

def parsed():
    p=ContractParser()
    p.feed(HTML)
    return p

def test_command_center_is_original_brand_and_accessible_navigation():
    p=parsed()
    assert len(p.ids)==len(set(p.ids))
    assert '<html lang="en">' in HTML
    assert 'name="viewport"' in HTML
    assert 'viewport-fit=cover' in HTML
    assert 'href="#main"' in HTML
    assert 'id="main" tabindex="-1"' in HTML
    assert 'aria-label="Primary workspace"' in HTML
    assert 'aria-label="Chats and recent work"' in HTML
    assert 'aria-expanded="false"' in HTML
    assert 'aria-label="Chat messages"' in HTML
    assert 'aria-live="polite"' in HTML
    assert 'name="description"' in HTML
    assert "Nexio" not in HTML
    for name in ["chat","agents","projects","tools","settings"]:
        assert f'data-panel="{name}"' in HTML
        assert f'id="panel-{name}"' in HTML

def test_existing_product_routes_and_real_media_tools_remain():
    p=parsed()
    for route in ("/","/creative/","/engage/","/workspace/","/intelligence/",
                  "/intelligence-lab/","/automation/","/company/"):
        assert route in p.hrefs
        assert (SITE/route.lstrip("/")).is_dir() if route != "/" else SITE.is_dir()
    for item in ("image","video","project","intelligence"):
        assert f'data-choose="{item}"' in HTML
    assert len(re.findall(r'class="tool-card"',HTML))==4
    assert 'id="view-all-tools"' in HTML
    assert 'id="tool-data"' in HTML
    tool_json=re.search(r'<script type="application/json" id="tool-data">(.*?)</script>',HTML,re.S)
    assert tool_json
    data=json.loads(tool_json.group(1))
    assert len(data)==6
    for key,entry in data.items():
        assert entry["url"] in p.hrefs
        assert len(entry["steps"])==4
        assert entry["url"].startswith("/")
        assert key in ("image","video","project","intelligence","workflow","growth")

def test_responsive_web_mobile_and_assistive_support():
    for breakpoint in ("1180px","970px","720px","530px","375px"):
        assert f"max-width:{breakpoint}" in CSS
    assert "env(safe-area-inset-bottom)" in CSS
    assert "100dvh" in CSS
    assert "prefers-reduced-motion:reduce" in CSS
    assert ":focus-visible" in CSS
    assert "--navy:#081c36" in CSS
    assert "--blue:#0788d2" in CSS
    assert "--gold:#e9b84f" in CSS
    assert "--silver:#e2e9f1" in CSS
    assert "aria-pressed" in JS
    assert "aria-expanded" in JS
    assert 'e.key==="Escape"' in JS

def test_strict_local_privacy_and_no_false_ai_claims():
    assert "connect-src 'none'" in HTML
    assert "form-action 'none'" in HTML
    assert "script-src 'self'" in HTML
    assert "No external actions" in HTML
    assert "rule-based planning" in HTML.lower()
    for banned in ("fetch(","XMLHttpRequest","WebSocket(","localStorage","sessionStorage",".innerHTML","eval(","new EventSource("):
        assert banned not in JS
    for expected in ("MAX_CHATS = 12","MAX_TURNS = 30","history.replaceChildren()",
                     'prompt.setCustomValidity("', "URL.createObjectURL", "URL.revokeObjectURL",
                     "activeId=null","sanitize(prompt.value)", "requestSubmit()"):
        assert expected in JS

def test_assets_and_legacy_preservation():
    for path in ("assets/command-center.css","assets/command-center.js",
                 "assets/metaautomate-mark.webp","workspace/index.html",
                 "assets/unified-workspace.js","assets/creative-maker.js","assets/creative-video.js",
                 "assets/project-device-ai.js"):
        assert (SITE/path).is_file(),path
    assert "/assets/command-center.css" in HTML
    assert "/assets/command-center.js" in HTML
    assert "https://" not in HTML
