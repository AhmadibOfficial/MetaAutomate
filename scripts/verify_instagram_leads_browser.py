#!/usr/bin/env python3
"""P2-03q Instagram offline browser acceptance, screen widths and no-network guards."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright

ROOT=Path(__file__).resolve().parents[1]
BASE="http://127.0.0.1:18383"
ART=ROOT/"artifacts/validation"


def main():
    ART.mkdir(parents=True,exist_ok=True)
    server=ThreadingHTTPServer(("127.0.0.1",18383),
       partial(SimpleHTTPRequestHandler,directory=str(ROOT/"apps/site")))
    Thread(target=server.serve_forever,daemon=True).start()
    errors=[]
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(headless=True)
            for width in (1440,390,360):
                context=browser.new_context(viewport={"width":width,"height":900},
                                            reduced_motion="reduce",device_scale_factor=1)
                page=context.new_page()
                page.on("pageerror",lambda err:errors.append(str(err)))
                page.on("request",lambda r:errors.append("External request: "+r.url)
                        if not r.url.startswith(BASE+"/") else None)
                response=page.goto(BASE+"/intelligence-lab/instagram/",wait_until="networkidle")
                assert response and response.status==200
                expect(page).to_have_title("Instagram Lead Intelligence — MetaAutomate | Offline Preview")
                expect(page.locator(".ig-stages article")).to_have_count(4)
                expect(page.locator("#case option")).to_have_count(4)
                expect(page.locator("#decision")).to_have_text("Lead Form Crm Review")
                expect(page.locator("#checks")).to_contain_text("0 · disabled")
                assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),width
                if width==1440:
                    page.screenshot(path=str(ART/"instagram-leads-desktop.png"),full_page=True)
                else:
                    page.screenshot(path=str(ART/f"instagram-leads-mobile-{width}.png"),full_page=True)
                page.locator("#case").select_option("SIM-IG-02")
                expect(page.locator("#decision")).to_have_text("Review Inbound Dm Within 24h")
                page.locator("#case").select_option("SIM-IG-05")
                expect(page.locator("#decision")).to_have_text("Review Ad Window Only If Origin Verified")
                page.locator("#business").select_option("bespoke_demo")
                expect(page.locator("#case option")).to_have_count(5)
                expect(page.locator("#decision")).to_have_text("Review Single Private Reply Only")
                page.locator("#case").select_option("SIM-IG-04")
                expect(page.locator("#decision")).to_have_text("Hold Comment Reply Ineligible")
                page.locator("#case").select_option("SIM-IG-06")
                expect(page.locator("#decision")).to_have_text("No Submission No Chat")
                page.locator("#budget_band").select_option("MEDIUM")
                expect(page.locator("#decision")).to_have_text("No Submission No Chat")
                page.locator("#reset").click()
                expect(page.locator("#budget_band")).to_have_value("UNKNOWN")
                page.locator("#case").select_option("SIM-IG-08")
                expect(page.locator("#decision")).to_have_text("Suppress Opt Out")
                page.locator("#case").select_option("SIM-IG-09")
                expect(page.locator("#decision")).to_have_text("Hold Comment Reply Ineligible")
                page.locator("#reset").focus()
                expect(page.locator("#reset")).to_be_focused()
                assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"),width
                context.close()
            context=browser.new_context(viewport={"width":1440,"height":900})
            page=context.new_page()
            page.goto(BASE+"/intelligence-lab/",wait_until="networkidle")
            for module in ("growth","crm","marketing"):
                page.locator('[data-module="'+module+'"]').click()
                expect(page.locator('a[href="/intelligence-lab/instagram/"]')).to_be_visible()
            context.close()
            browser.close()
        assert not errors,errors
    finally:
        server.shutdown();server.server_close()
    print("PASS: Instagram 4-channel policy preview, opt-out, no-chat, private reply, ad-origin, desktop/mobile, module links")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
