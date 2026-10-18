"""Direct actionable MetaAutomate controls and honest media capabilities."""
from pathlib import Path

SITE=Path(__file__).resolve().parents[1]/"apps/site"

def test_start_project_has_functional_media_destinations():
    page=(SITE/"engage/index.html").read_text()
    assert 'href="/creative/#instant-design"' in page
    assert 'href="/creative/#instant-video"' in page
    workbench=(SITE/"creative/index.html").read_text()
    assert 'id="instant-design"' in workbench
    assert 'id="instant-video"' in workbench
    assert 'id="maker-form"' in workbench
    assert 'id="video-maker-form"' in workbench

def test_media_output_is_real_local_generation_not_a_false_neural_claim():
    png=(SITE/"assets/creative-maker.js").read_text()
    video=(SITE/"assets/creative-video.js").read_text()
    assert "canvas.width=w" in png
    assert "canvas.toBlob" in png
    assert "createObjectURL" in png
    assert "MediaRecorder(" in video
    assert "captureStream(" in video
    assert "video-maker-rights" in video
    assert "No server, AI model" in video
    assert "not neural" in png.lower() or "No API, provider" in png

def test_no_obsolete_chat_transfer_or_download():
    page=(SITE/"engage/index.html").read_text()
    js=(SITE/"assets/project-device-ai.js").read_text()
    assert "project-ai-export" not in page
    assert "project-ai-creative-handoff" not in page
    assert "project-chat-creative" not in page
    assert "creative-handoff.js" not in page
    assert "Download conversation" not in page
    assert "sessionStorage" not in js
