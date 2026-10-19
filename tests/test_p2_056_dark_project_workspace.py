"""P2-056 — dark Chat/Work project experience static contracts."""
from html.parser import HTMLParser
from pathlib import Path

SITE=Path(__file__).resolve().parents[1]/"apps"/"site"
HTML=(SITE/"engage"/"index.html").read_text(encoding="utf-8")
CSS=(SITE/"assets"/"project-workspace-dark.css").read_text(encoding="utf-8")
JS=(SITE/"assets"/"project-workspace-dark.js").read_text(encoding="utf-8")

class Markup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=[]
        self.scripts=[]
        self.links=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get("id"): self.ids.append(a["id"])
        if tag=="script" and a.get("src"): self.scripts.append(a["src"])
        if tag=="a" and a.get("href"): self.links.append(a["href"])

def test_immersive_workspace_preserves_real_tools_and_guided_intake():
    page=Markup()
    page.feed(HTML)
    assert len(page.ids)==len(set(page.ids))
    for needed in (
        "workspace-mode-chat","workspace-mode-work","workspace-work-panel",
        "workspace-work-brief","workspace-work-ai","workspace-search-input",
        "workspace-mobile-menu","workspace-menu-backdrop",
        "project-chat-new","project-chat-input","project-chat-messages",
        "project-chat-summary","project-ai-open","project-ai-experience","brief-form",
    ):
        assert needed in page.ids,needed
    assert "What would you like to build today?" in HTML
    assert 'class="project-immersive-page" data-workspace-mode="chat"' in HTML
    assert 'aria-pressed="true">Chat</button>' in HTML
    assert 'aria-pressed="false">Work</button>' in HTML
    assert 'aria-label="Choose workspace mode"' in HTML
    assert "GUIDED CHAT · PRIVATE BY DEFAULT" in HTML
    assert "/creative/#instant-design" in page.links
    assert "/creative/#instant-video" in page.links
    assert "/services/" in page.links
    for script in ("/assets/site.js","/assets/project-chat.js",
                   "/assets/project-device-ai.js","/assets/project-workspace-dark.js"):
        assert script in page.scripts
    assert page.scripts.index("/assets/project-chat.js") < page.scripts.index("/assets/project-workspace-dark.js")
    assert page.scripts.index("/assets/project-device-ai.js") < page.scripts.index("/assets/project-workspace-dark.js")
    assert '<link rel="stylesheet" href="/assets/project-workspace-dark.css">' in HTML

def test_switcher_controls_actually_switch_and_preserve_ai_consent():
    for fragment in (
        'body.dataset.workspaceMode=isWork?"work":"chat"',
        'workPanel.hidden=!isWork',
        'aria-pressed',
        '"project-chat-input"',
        '"project-ai-open"',
        '"project-ai-close"',
        'document.getElementById("project-chat-new")',
        'search?.addEventListener("input"',
        'project-workspace-side',
        'Escape',
        'event.ctrlKey||event.metaKey',
    ):
        assert fragment in JS,fragment
    for forbidden in (
        "fetch(","XMLHttpRequest","sessionStorage","localStorage",
        "new WebSocket","navigator.sendBeacon","innerHTML =","eval(",
    ):
        assert forbidden not in JS,forbidden
    assert "Download model and start local AI" in HTML
    assert "Requires WebGPU" in HTML
    assert "customer accounts" in HTML.lower()

def test_dark_theme_is_scoped_responsive_and_accessible():
    assert "body.project-immersive-page" in CSS
    assert ".project-immersive-page .project-chat" in CSS
    assert 'data-workspace-mode="work"' in CSS
    assert ".workspace-mode-switch" in CSS
    assert ".workspace-work-grid" in CSS
    assert ".workspace-menu-backdrop" in CSS
    assert "@media(max-width:740px)" in CSS
    assert "@media(max-width:440px)" in CSS
    assert "prefers-reduced-motion" in CSS
    assert ":focus-visible" in CSS
    assert "display:none!important" in CSS
    assert "#08090b" in CSS
