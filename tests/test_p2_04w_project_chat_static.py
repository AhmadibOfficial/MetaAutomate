"""P2-04w: conversation-first project intake static and privacy contract."""
from html.parser import HTMLParser
from pathlib import Path
import re

SITE = Path(__file__).resolve().parents[1] / "apps" / "site"

class Structure(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.forms = []
        self.scripts = []
        self.buttons = []
        self.links = []
        self.details = 0
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.append(a["id"])
        if tag == "form":
            self.forms.append(a.get("id"))
        if tag == "script" and a.get("src"):
            self.scripts.append(a["src"])
        if tag == "button":
            self.buttons.append(a)
        if tag == "a":
            self.links.append(a.get("href",""))
        if tag == "details":
            self.details += 1

def test_conversation_is_primary_and_old_enquiry_form_is_removed():
    html = (SITE / "engage" / "index.html").read_text()
    p = Structure()
    p.feed(html)
    assert 'What would you like to build today?' in html
    assert p.forms == [], "Only the conversation-led experience remains"
    assert p.details == 0
    assert 'id="project-chat-alternative"' not in html
    assert 'id="brief-form"' not in html
    assert len(p.ids) == len(set(p.ids)), "Duplicate DOM ID"
    assert "/assets/project-chat.js" in p.scripts
    assert "/assets/site.js" in p.scripts
    for node in (
        "project-chat-messages","project-chat-input","project-chat-send",
        "project-chat-new","project-chat-progress","project-chat-summary",
        "project-chat-summary-text","project-chat-email",
        "project-chat-copy","project-chat-download","project-chat-edit"
    ):
        assert node in p.ids
    assert 'role="log"' in html
    assert 'aria-live="polite"' in html
    assert "Guided chat" in html
    assert "Nothing is sent" in html or "nothing has been sent" in html
    assert 'data-project-template="creative"' in html
    assert "metaautomating@gmail.com" in html
    assert "What would you like to build today?" in html

def test_local_chat_never_claims_model_execution_or_stores_user_conversations():
    js = (SITE / "assets" / "project-chat.js").read_text()
    css = (SITE / "assets" / "project-chat.css").read_text()
    assert 'new URLSearchParams' in js
    assert 'SERVICES.has(requested)' in js
    assert 'textContent' in js
    assert 'QUESTIONS.length' in js
    assert 'const BUSINESS_EMAIL = "metaautomating@gmail.com"' in js
    assert 'navigator.clipboard.writeText(currentBrief)' in js
    assert 'URL.createObjectURL(new Blob(' in js
    assert 'composeEmailHref' in js
    assert 'currentBrief = buildBrief()' in js
    assert 'event.key === "Enter" && !event.shiftKey' in js
    for forbidden in ('fetch(', 'XMLHttpRequest', 'new WebSocket',
                      'localStorage', 'sessionStorage', 'sendBeacon(',
                      'innerHTML', 'eval(', 'document.cookie', 'MediaRecorder'):
        # The source comment may mention some forbidden words as documentation.
        code = "\n".join(line for line in js.splitlines()
                         if not line.lstrip().startswith("*") and
                         not line.lstrip().startswith("/*"))
        assert forbidden not in code, forbidden
    assert "@media(max-width:620px)" in css
    assert ":focus-visible" in css
    assert "prefers-reduced-motion" in css

def test_service_shortcuts_remain_known_existing_disciplines():
    js = (SITE / "assets" / "project-chat.js").read_text()
    html = (SITE / "engage" / "index.html").read_text()
    for label in ("Product Design & Experience",
                  "AI Systems & Automation", "Software & Digital Products",
                  "Cybersecurity & Quality"):
        assert label in js
    assert '/engage/' in (SITE / "services" / "index.html").read_text()
    assert 'id="workspace-sidebar-toggle"' in html
    assert 'id="brief-form"' not in html
    assert "openStructuredLink" not in js
