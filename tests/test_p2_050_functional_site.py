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

def test_narrated_video_generator_is_a_real_browser_encoding_task():
    html=read("creative/index.html")
    js=read("assets/creative-video.js")
    assert 'id="video-maker-form"' in html
    assert 'id="video-maker-audio"' in html
    assert 'id="video-maker-audio-preview"' in html
    assert 'id="video-maker-rights"' in html
    assert 'id="video-maker-preview"' in html
    assert 'id="video-maker-download"' in html
    assert 'src="/assets/creative-video.js"' in html
    assert "canvas.captureStream(24)" in js
    assert "new MediaRecorder(stream" in js
    assert "new AudioContext()" in js
    assert "decodeAudioData(await file.arrayBuffer())" in js
    assert "audioOut.stream.getAudioTracks()" in js
    assert "media.ondataavailable" in js
    assert "media.onstop" in js
    assert 'mimeType:codec' in js
    assert 'link.download="metaautomate-narrated-"+size.value+".webm"' in js
    assert 'decoded.duration<29.95 || decoded.duration>120.05' in js
    assert "audioUsable(decoded)" in js
    assert "rights.checked" in js
    assert "getUserMedia" not in js
    for x in ("fetch(", "localStorage", "sessionStorage", "XMLHttpRequest",
              "sendBeacon(", "innerHTML"):
        assert x not in js

def test_ai_tasks_produce_copyable_results_without_conversation_download():
    html=read("engage/index.html")
    script=read("assets/project-device-ai.js")
    assert 'id="project-ai-copy"' in html
    assert "project-ai-export" not in html
    for label in ("product", "marketing", "workflow", "video"):
        assert f'data-ai-task="{label}"' in html
    assert 'navigator.clipboard.writeText(lastAnswer)' in script
    assert "const TASKS = Object.freeze(" in script
    assert "taskButtons.forEach(button" in script
    assert 'href="/creative/#instant-design"' in html
    assert "sessionStorage" not in script

def test_product_homepage_launches_working_tools_first():
    html=read("index.html")
    assert 'class="product-tools shell"' in html
    assert html.index('class="product-tools shell"') < html.index('id="solutions"')
    assert 'href="/creative/#instant-design"' in html
    assert 'href="/creative/#instant-video"' in html
    assert "Create a PNG image" in html
    assert "Make a narrated video" in html
    assert 'href="/engage/"' in html
    assert 'href="/assets/product-tools.css"' in html
