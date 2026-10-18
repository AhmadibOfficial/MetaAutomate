"""P2-050: working image creation is required; not merely a planning document."""
from html.parser import HTMLParser
from pathlib import Path

SITE=Path(__file__).resolve().parents[1]/"apps/site"
def read(path):
    return (SITE/path).read_text("utf-8")

def test_remove_rejected_download_and_transfer_controls():
    engage=read("engage/index.html")
    chat=read("assets/project-chat.js")
    ai=read("assets/project-device-ai.js")
    creative=read("creative/index.html")
    assert "project-ai-export" not in engage
    assert "project-chat-creative-format" not in engage
    assert "project-chat-creative" not in engage
    assert "project-ai-creative-handoff" not in engage
    assert "creative-handoff.js" not in engage
    assert "creative-handoff.js" not in creative
    assert "project-chat-creative" not in chat
    assert "project-ai-creative" not in ai
    assert "exportChat" not in ai
    assert "MetaAutomateCreativeHandoff" not in read("assets/creative.js")
    assert not (SITE/"assets/creative-handoff.js").exists()

def test_actual_image_creator_has_output_not_fake_ai_claim():
    html=read("creative/index.html")
    script=read("assets/creative-maker.js")
    assert 'id="instant-design"' in html
    assert 'id="maker-canvas"' in html
    assert 'id="maker-download"' in html
    assert 'id="maker-preview"' in html
    assert "Make a graphic. Download it." in html
    assert "not neural image/video generation" in html
    assert 'src="/assets/creative-maker.js"' in html
    assert 'href="/assets/creative-maker.css"' in html
    assert "canvas.toBlob(" in script
    assert 'a.download="metaautomate-original-"+format.value+".png"' in script
    assert '"image/png"' in script
    assert "const SIZES={square:[1080,1080],story:[1080,1920],wide:[1920,1080]}" in script
    assert "ctx.fillText" in script
    for unsafe in ("fetch(", "new WebSocket", "XMLHttpRequest", "innerHTML",
                   "sessionStorage", "localStorage", "document.cookie"):
        assert unsafe not in script,unsafe

def test_accessible_mobile_generator_and_rights_checks():
    html=read("creative/index.html")
    css=read("assets/creative-maker.css")
    plans=read("assets/creative.js")
    for kind in ("square","story","wide"):
        assert f'value="{kind}"' in html
    assert 'role="status" aria-live="polite"' in html
    assert '@media(max-width:620px)' in css
    assert ':focus-visible' in css
    assert 'const rightsKnown' in plans
    assert 'const consentKnown' in plans
    assert "NOT APPROVED" in plans
    assert "HOLD" in plans
    assert 'id="creative-brief-form"' in html

def test_duplicate_html_ids_not_added():
    import re
    for name in ("engage/index.html","creative/index.html"):
        ids=re.findall(r'\bid="([^"]+)"',read(name))
        assert len(ids)==len(set(ids)),name
