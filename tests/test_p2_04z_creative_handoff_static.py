"""P2-04z: guarded browser-local handoff between project chat and workbench.

These checks only verify source structure. Genuine browser acceptance needs
Playwright with a real site runtime; this is not model inference proof.
"""
from pathlib import Path
from html.parser import HTMLParser

SITE=Path(__file__).resolve().parents[1]/"apps/site"
def read(path):
    return (SITE/path).read_text(encoding="utf-8")
class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=[]
        self.scripts=[]
    def handle_starttag(self,name,attrs):
        values=dict(attrs)
        if values.get("id"):
            self.ids.append(values["id"])
        if name=="script":
            self.scripts.append(values.get("src"))

def test_guide_still_works_and_handoff_is_explicit():
    html=read("engage/index.html")
    p=Elements()
    p.feed(html)
    assert len(p.ids)==len(set(p.ids))
    assert "/assets/creative-handoff.js" in p.scripts
    assert p.scripts.index("/assets/creative-handoff.js") < p.scripts.index("/assets/project-chat.js")
    assert p.scripts.index("/assets/creative-handoff.js") < p.scripts.index("/assets/project-device-ai.js")
    for key in ("project-chat-creative","project-chat-creative-format",
                "project-ai-creative-handoff","project-ai-creative-format",
                "project-ai-export","project-chat-summary","project-ai-messages"):
        assert key in p.ids
    assert 'id="project-ai-creative-handoff" type="button" disabled' in html
    assert "temporarily" in html
    assert 'id="brief-form"' in html

def test_transfer_is_ten_minute_expiring_and_one_time_only():
    handoff=read("assets/creative-handoff.js")
    assert "const TTL_MS=10*60*1000" in handoff
    assert 'window.sessionStorage.setItem(KEY' in handoff
    assert 'window.sessionStorage.removeItem(KEY)' in handoff
    assert "Date.now()-item.createdAt>TTL_MS" in handoff
    assert 'goal.length<20' in handoff
    assert 'goal.length>700' in handoff
    assert "Object.freeze({save,consume})" in handoff
    for prohibited in ("fetch(", "new WebSocket", "XMLHttpRequest",
                       "localStorage", "sendBeacon(", "innerHTML",
                       "document.cookie"):
        assert prohibited not in handoff

def test_user_controlled_chat_and_download_never_publishes():
    guided=read("assets/project-chat.js")
    ai=read("assets/project-device-ai.js")
    assert 'getElementById("project-chat-creative")?.addEventListener("click"' in guided
    assert 'source:"guided"' in guided
    assert 'window.location.assign("/creative/#creative-form")' in guided
    assert 'creativeHandoff?.addEventListener("click"' in ai
    assert 'source:"device_ai"' in ai
    assert "goal:lastProjectQuestion" in ai
    assert "lastProjectQuestion=text.slice(0,700)" in ai
    assert 'exportChat?.addEventListener("click"' in ai
    assert 'link.download="metaautomate-on-device-chat.txt"' in ai
    assert 'window.location.assign("/creative/#creative-form")' in ai
    assert "AI reply or full chat history is transferred" in read("engage/index.html")

def test_creative_workbench_does_not_approve_unverified_rights():
    html=read("creative/index.html")
    script=read("assets/creative.js")
    assert 'src="/assets/creative-handoff.js"' in html
    assert html.index('src="/assets/creative-handoff.js"') < html.index('src="/assets/creative.js"')
    assert 'id="creative-import-notice"' in html
    assert "MetaAutomateCreativeHandoff?.consume?.()" in script
    assert 'kind.value=incoming.kind' in script
    assert 'goalField.value=incoming.goal' in script
    assert "Rights, consent and human approval" in script
    assert 'option value="unknown"' in html
    assert '"owned", "licensed", "permission", "none"' in script
    assert "Generation, export of media, distribution and publishing remain disabled here" in script
