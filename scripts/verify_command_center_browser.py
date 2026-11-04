#!/usr/bin/env python3
"""P2-065: actual Chromium acceptance for command-center desktop/tablet/mobile.

Temporary loopback HTTP only, synthetic prompts, no production/service calls.
Reports desktop/mobile screenshots and redacted test summary under artifacts/.
"""
from __future__ import annotations
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright, expect

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"apps/site"
OUT=ROOT/"artifacts/command-center"
OUT.mkdir(parents=True,exist_ok=True)

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args):
        return

def no_horizontal_overflow(page,label):
    d=page.evaluate("""() => ({
        doc:document.documentElement.scrollWidth,
        viewport:document.documentElement.clientWidth,
        shell:document.querySelector(".shell").scrollWidth,
        shellClient:document.querySelector(".shell").clientWidth
    })""")
    assert d["doc"] <= d["viewport"] + 2, (label,d)
    assert d["shell"] <= d["shellClient"] + 2, (label,d)
    return d

def test_desktop(browser,base,errors,external):
    ctx=browser.new_context(viewport={"width":1440,"height":900},reduced_motion="reduce",accept_downloads=True)
    page=ctx.new_page()
    page.on("pageerror",lambda error:errors.append(str(error)))
    page.route("**/*",lambda route:route.continue_() if route.request.url.startswith(base+"/") else
               (external.append(route.request.url),route.abort()))
    r=page.goto(base+"/command/",wait_until="load")
    assert r is not None and r.status==200
    expect(page).to_have_title("MetaAutomate — Command Center")
    expect(page.locator(".rail-action")).to_have_count(5)
    expect(page.locator(".tool-card")).to_have_count(6)
    expect(page.locator("#welcome")).to_be_visible()
    expect(page.locator("#mobile-toggle")).to_be_hidden()
    expect(page.locator("#command-input")).to_be_visible()
    assert no_horizontal_overflow(page,"desktop")
    page.screenshot(path=str(OUT/"command-desktop.png"),full_page=True)

    # A tool selection is an action, not merely a card animation.
    page.locator('[data-choose="image"]').click()
    expect(page.locator("#selected-tool-name")).to_have_text("Image Studio")
    page.locator("#command-input").fill("Create a product graphic with a headline and subtitle")
    page.locator("#command-input").press("Enter")
    expect(page.locator("#message-list .message")).to_have_count(2)
    expect(page.locator(".message-link")).to_have_attribute("href","/creative/")
    expect(page.locator("#chat-count")).to_have_text("1")
    expect(page.locator("#conversation")).to_be_visible()
    expect(page.locator(".message.guide .speaker")).to_contain_text("Rules-based")
    page.screenshot(path=str(OUT/"command-desktop-chat.png"),full_page=True)

    with page.expect_download() as result:
        page.locator("#export-chat").click()
    download=result.value
    assert download.suggested_filename=="metaautomate-guided-session.txt"
    artifact=Path(download.path()).read_text(encoding="utf-8")
    assert "No external actions executed." in artifact
    assert "Create a product graphic" in artifact
    assert "Continue: /creative/" in artifact

    # Search current session history and reopen a conversation.
    page.locator("#chat-search").fill("Create a product")
    expect(page.locator(".history-item")).to_have_count(1)
    page.locator("#chat-search").fill("does not match")
    expect(page.locator(".history-item")).to_have_count(0)
    expect(page.locator("#chat-empty")).to_contain_text("No chat titles")
    page.locator("#chat-search").fill("")
    page.locator("#new-chat").click()
    expect(page.locator("#welcome")).to_be_visible()
    expect(page.locator(".history-item")).to_have_count(1)
    page.locator(".history-item").click()
    expect(page.locator("#message-list .message")).to_have_count(2)

    page.locator('[data-panel="agents"]').click()
    expect(page.locator("#panel-agents")).to_be_visible()
    expect(page.locator("#agent-directory .directory-item")).to_have_count(6)
    page.locator('#agent-directory .tool-actions button').first.click()
    expect(page.locator("#panel-chat")).to_be_visible()
    expect(page.locator("#selected-tool-name")).to_have_text("Image Studio")
    page.locator('[data-panel="projects"]').click()
    expect(page.locator("#panel-projects")).to_be_visible()
    page.locator('[data-panel="tools"]').click()
    expect(page.locator("#panel-tools")).to_be_visible()
    page.locator('[data-panel="settings"]').click()
    expect(page.locator("#panel-settings")).to_be_visible()
    page.locator("#clear-all").click()
    expect(page.locator("#chat-count")).to_have_text("0")
    expect(page.locator(".clear-confirmation")).to_contain_text("Chats cleared")
    assert no_horizontal_overflow(page,"desktop settings")
    ctx.close()

def test_responsive(browser,base,width,height,errors,external):
    ctx=browser.new_context(viewport={"width":width,"height":height},
                            is_mobile=width<=720,has_touch=width<=720,
                            device_scale_factor=1,reduced_motion="reduce")
    page=ctx.new_page()
    page.on("pageerror",lambda error:errors.append(str(error)))
    page.route("**/*",lambda route:route.continue_() if route.request.url.startswith(base+"/") else
               (external.append(route.request.url),route.abort()))
    assert page.goto(base+"/command/",wait_until="load").status==200
    expect(page.locator("#welcome")).to_be_visible()
    expect(page.locator("#command-input")).to_be_visible()
    if width<=970:
        expect(page.locator("#mobile-toggle")).to_be_visible()
        page.locator("#mobile-toggle").click()
        expect(page.locator("#chat-sidebar")).to_have_class("chat-sidebar is-open")
        expect(page.locator("#mobile-toggle")).to_have_attribute("aria-expanded","true")
        page.locator("#side-close").click()
        expect(page.locator("#mobile-toggle")).to_have_attribute("aria-expanded","false")
    else:
        expect(page.locator("#mobile-toggle")).to_be_hidden()
    if width<=720:
        # Dedicated mobile navigation remains visible with a full-width composer.
        expect(page.locator(".icon-rail")).to_be_visible()
        assert page.locator(".icon-rail").evaluate("(node)=>getComputedStyle(node).position")=="fixed"
        page.locator('[data-panel="tools"]').click()
        expect(page.locator("#panel-tools")).to_be_visible()
        page.locator('[data-panel="chat"]').click()
        expect(page.locator("#welcome")).to_be_visible()
    # Quick prompt action then actual rule-based response.
    page.locator('[data-prompt="Create a product graphic for a business promotion"]').click()
    expect(page.locator("#command-input")).to_have_value("Create a product graphic for a business promotion")
    page.locator("#command-form .send-button").click()
    expect(page.locator("#message-list .message")).to_have_count(2)
    assert no_horizontal_overflow(page,f"width {width}px")
    page.screenshot(path=str(OUT/f"command-{width}px.png"),full_page=True)
    ctx.close()

def main():
    assert SITE.is_dir()
    handler=partial(QuietHandler,directory=str(SITE))
    server=ThreadingHTTPServer(("127.0.0.1",0),handler)
    thread=Thread(target=server.serve_forever,daemon=True)
    thread.start()
    base=f"http://127.0.0.1:{server.server_address[1]}"
    errors,external=[],[]
    sizes=[(1024,768),(768,1024),(390,844),(360,780),(320,690)]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            try:
                test_desktop(browser,base,errors,external)
                for width,height in sizes:
                    test_responsive(browser,base,width,height,errors,external)
                ctx=browser.new_context()
                pg=ctx.new_page()
                for path in ("/creative/","/engage/","/workspace/","/intelligence/",
                             "/intelligence-lab/","/automation/","/company/"):
                    assert pg.goto(base+path,wait_until="domcontentloaded").status==200,path
                ctx.close()
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
    assert not errors,errors
    assert not external,external
    report={
        "status":"LOCAL_BROWSER_ACCEPTANCE",
        "viewports":[1440,1024,768,390,360,320],
        "privacy":"No off-origin requests observed in command center",
        "chat_model_inference":False,
        "real_external_operations":False,
        "screen_reader_tested":False,
        "production_deployed":False,
        "page_errors":errors,
        "off_origin_requests":external,
    }
    (OUT/"acceptance.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("PASS: 6 responsive Chromium sizes; new chat, guidance, search, export, navigation and existing routes")

if __name__=="__main__":
    main()
