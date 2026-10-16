#!/usr/bin/env python3
"""P2-03w: test source-governed 12-module / 5-engine map at desktop/mobile."""
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1]
BASE="http://127.0.0.1:18787"
ART=ROOT/"artifacts/validation"


def main():
    ART.mkdir(parents=True,exist_ok=True)
    server=ThreadingHTTPServer(("127.0.0.1",18787),
        partial(SimpleHTTPRequestHandler,directory=str(ROOT/"apps/site")))
    Thread(target=server.serve_forever,daemon=True).start()
    errors=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            for width in (1440,390,360):
                context=browser.new_context(viewport={"width":width,"height":920},
                    reduced_motion="reduce",device_scale_factor=1)
                page=context.new_page()
                page.on("pageerror",lambda error:errors.append(str(error)))
                page.on("request",lambda req:errors.append(req.url)
                        if not req.url.startswith(BASE+"/") else None)
                response=page.goto(BASE+"/intelligence/governance/",wait_until="networkidle")
                assert response and response.status==200
                expect(page).to_have_title("Intelligence Governance Map — MetaAutomate | Source Preview")
                expect(page.locator("#module-list button")).to_have_count(12)
                expect(page.locator("#engines article")).to_have_count(5)
                expect(page.locator("#models article")).to_have_count(4)
                expect(page.locator("#module-count")).to_have_text("12")
                expect(page.locator("#engine-count")).to_have_text("5")
                expect(page.locator("#foundation")).to_have_text("3/9")
                expect(page.locator("#model-calls")).to_have_text("0")
                expect(page.locator("#module-name")).to_have_text("Objective Workspace")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1"),width
                if width==1440:filename="intelligence-governance-desktop.png"
                else:filename=f"intelligence-governance-mobile-{width}.png"
                page.screenshot(path=str(ART/filename),full_page=True)
                page.locator("#module-list button[data-module='finance']").click()
                expect(page.locator("#module-name")).to_have_text("Financial Intelligence")
                expect(page.locator("#module-engines")).to_contain_text("Learning")
                expect(page.locator("#module-tools")).to_contain_text("Summarize Evidence")
                expect(page.locator("#module-eval")).to_contain_text("not been measured")
                page.locator("#module-list button[data-module='marketing']").click()
                expect(page.locator("#module-name")).to_have_text("Marketing Intelligence")
                expect(page.locator("#module-engines")).to_contain_text("Automation")
                expect(page.locator("#module-tools")).not_to_contain_text("Summarize Evidence")
                page.locator("#module-list button[data-module='executive']").click()
                expect(page.locator("#module-engines span")).to_have_count(5)
                expect(page.locator("#models")).to_contain_text("claude-opus-5-5")
                expect(page.locator("#models")).to_contain_text("gpt-6.1-sol")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1"),width
                context.close()
            context=browser.new_context(viewport={"width":1440,"height":900})
            page=context.new_page()
            page.goto(BASE+"/intelligence/",wait_until="networkidle")
            expect(page.locator('a[href="/intelligence/governance/"]')).to_be_visible()
            context.close()
            browser.close()
        assert not errors,errors
    finally:
        server.shutdown()
        server.server_close()
    print("PASS: 12 modules, 5 shared engines, 4 models, 3 viewport layouts, navigation, CSP/no external calls")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
