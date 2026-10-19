"""P2-04y: real local-WebGPU option is explicit, never a silent backend."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/"apps/site"
HTML=(ROOT/"engage/index.html").read_text()
JS=(ROOT/"assets/project-device-ai.js").read_text()
CSS=(ROOT/"assets/project-device-ai.css").read_text()

def test_guided_chat_kept_as_fallback():
    assert 'id="brief-form"' not in HTML
    assert 'id="project-chat-messages"' in HTML
    assert 'id="project-chat-send"' in HTML
    assert 'id="project-ai-experience"' in HTML
    assert '<section id="project-ai-experience" class="project-ai-experience" aria-label="Experimental on-device AI chat" hidden>' in HTML
    assert 'id="project-ai-open"' in HTML
    assert 'id="project-ai-load"' in HTML
    assert 'src="/assets/project-device-ai.js"' in HTML
    assert 'href="/assets/project-device-ai.css"' in HTML

def test_experimental_mode_warns_before_external_downloads():
    assert "WebGPU-compatible browser" in HTML
    assert "hundreds of megabytes" in HTML
    assert "third-party hosts" in HTML
    assert "not been independently security-audited" in HTML
    assert "not" in HTML
    assert "navigator.gpu.requestAdapter()" in JS
    assert 'load.addEventListener("click", async () =>' in JS
    assert 'await import(moduleURL)' in JS
    assert 'CreateMLCEngine(modelId,' in JS
    assert 'Qwen2.5-0.5B-Instruct-q4f32_1-MLC' in JS
    assert 'https://esm.run/@mlc-ai/web-llm@0.2.85' in JS

def test_no_fake_live_claims_or_remote_api_integration():
    assert 'No MetaAutomate account, cloud AI server' in HTML
    assert 'Image, video, voice generation' in HTML
    assert 'window.isSecureContext' in JS
    assert 'max_tokens:260' in JS
    assert 'turns=[...limited,' in JS
    assert 'textContent = message' in JS
    assert 'feed.replaceChildren()' in JS
    assert 'fetch(' not in JS
    assert 'localStorage' not in JS
    assert 'sessionStorage' not in JS
    assert 'innerHTML' not in JS
    assert 'new WebSocket' not in JS
    assert 'modelId = "Qwen2.5-0.5B-Instruct-q4f32_1-MLC"' in JS

def test_accessibility_and_small_screen_controls():
    assert 'aria-label="On-device AI conversation"' in HTML
    assert 'id="project-ai-status" class="project-ai-status" role="status" aria-live="polite"' in HTML
    assert 'id="project-ai-error" class="project-ai-error" role="alert"' in HTML
    assert 'aria-expanded="false"' in HTML
    assert 'id="project-ai-send" type="button" disabled' in HTML
    assert 'id="project-ai-reset"' in HTML
    assert '@media(max-width:620px)' in CSS
    assert 'focus-visible' in CSS
    assert 'prefers-reduced-motion' in CSS
