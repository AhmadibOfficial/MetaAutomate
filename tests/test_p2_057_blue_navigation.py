"""P2-057 blue project workspace: simplified copy and real navigation."""
from html.parser import HTMLParser
from pathlib import Path

SITE=Path(__file__).resolve().parents[1]/"apps/site"

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=[]
        self.forms=[]
        self.links=[]
    def handle_starttag(self,tag,attrs):
        values=dict(attrs)
        if values.get("id"):self.ids.append(values["id"])
        if tag=="form":self.forms.append(values.get("id"))
        if tag=="a" and values.get("href"):self.links.append(values["href"])

def test_legacy_form_and_unused_marketing_chrome_are_removed():
    html=(SITE/"engage/index.html").read_text()
    p=Page()
    p.feed(html)
    assert not p.forms
    assert len(p.ids)==len(set(p.ids))
    for retired in ("Prefer a structured project form?",
                    'id="brief-form"','id="project-chat-alternative"',
                    'class="site-header"','class="site-footer"',
                    'class="utility-bar"','src="/assets/site.js"'):
        assert retired not in html,retired
    assert 'id="project-chat-input"' in html
    assert 'id="project-chat-summary"' in html
    assert 'id="project-chat-email"' in html
    assert "/creative/" in p.links and "/" in p.links

def test_menu_can_hide_or_show_sidebar_and_keyboard_remains_usable():
    html=(SITE/"engage/index.html").read_text()
    js=(SITE/"assets/project-workspace-dark.js").read_text()
    css=(SITE/"assets/project-workspace-dark.css").read_text()
    assert 'id="workspace-sidebar-toggle"' in html
    assert 'aria-controls="project-workspace-side"' in html
    assert 'aria-expanded="true"' in html
    for key in ("aside.hidden=!menuOpen","menuOpen=!onMobile()",
                'menu.setAttribute("aria-expanded"',
                'menu.setAttribute("aria-label"',
                'body.dataset.sidebar=menuOpen?"open":"closed"',
                "onMobile()","workspace-menu-backdrop","Escape",
                "event.ctrlKey||event.metaKey","search?.focus()"):
        assert key in js,key
    assert '[data-sidebar="closed"] .project-chat' in css
    assert '.project-chat-side[hidden]' in css
    assert '.workspace-sidebar-toggle' in css
    assert '@media(max-width:740px)' in css
    assert ':focus-visible' in css
    assert 'prefers-reduced-motion' in css
    for unsafe in ("fetch(","XMLHttpRequest","WebSocket(",
                   "sessionStorage","localStorage","sendBeacon("):
        assert unsafe not in js,unsafe

def test_brand_palette_font_and_old_site_deep_links():
    css=(SITE/"assets/project-workspace-dark.css").read_text()
    html=(SITE/"engage/index.html").read_text()
    assert 'content="#040D20"' in html
    assert "#08090b" not in css
    assert '#082d68' in css
    assert '#072554' in css
    assert "Plus Jakarta Sans" in css
    assert "Inter" in css
    assert "font-size:1.06rem" in css
    assert "Choose a tool and start creating." in (SITE/"assets/project-workspace-dark.js").read_text()
    assert "/engage/#brief-form" not in (SITE/"index.html").read_text()
    assert "/engage/#brief-form" not in (SITE/"automation/index.html").read_text()
    assert "/engage/#project-chat-input" in (SITE/"index.html").read_text()
