#!/usr/bin/env python3
"""P2-03r Chromium acceptance: responsive Facebook funnel and no external requests."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:18484"
ART = ROOT / "artifacts/validation"


def main():
    ART.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(
        ("127.0.0.1", 18484),
        partial(SimpleHTTPRequestHandler, directory=str(ROOT / "apps/site")),
    )
    Thread(target=server.serve_forever, daemon=True).start()
    errors = []
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            for width in (1440, 390, 360):
                ctx=browser.new_context(
                    viewport={"width":width,"height":900},
                    reduced_motion="reduce",device_scale_factor=1)
                page=ctx.new_page()
                page.on("pageerror",lambda err: errors.append(str(err)))
                page.on("request",lambda req: errors.append("External: "+req.url)
                        if not req.url.startswith(BASE+"/") else None)
                resp=page.goto(BASE+"/intelligence-lab/facebook/",wait_until="networkidle")
                assert resp and resp.status==200
                expect(page).to_have_title(
                    "Facebook Lead Intelligence — MetaAutomate | Source Preview"
                )
                expect(page.locator(".fb-stages article")).to_have_count(4)
                expect(page.locator("#decision")).to_have_text("No lead until submission")
                expect(page.locator("#ledger")).to_contain_text("0 · disabled")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1"), width
                if width==1440:
                    page.screenshot(path=str(ART/"facebook-lead-desktop.png"),full_page=True)
                else:
                    page.screenshot(path=str(ART/f"facebook-lead-mobile-{width}.png"),full_page=True)
                page.locator('input[name="formstage"][value="SUBMITTED"]').check()
                expect(page.locator("#decision")).to_have_text("Review submitted lead metadata")
                expect(page.locator("#ledger")).to_contain_text("Lead profile retrieval")
                expect(page.locator("#ledger")).to_contain_text("Not verified")
                page.locator("#business").select_option("bespoke_demo")
                expect(page.locator("#source")).to_contain_text("SIM-FORM-BESPOKE")
                page.locator("#timeline").select_option("SOON")
                expect(page.locator("#ledger")).to_contain_text("Timeline answer selected")
                page.locator('input[name="formstage"][value="OPENED"]').check()
                expect(page.locator("#decision")).to_have_text("No lead until submission")
                page.locator("#business").focus()
                expect(page.locator("#business")).to_be_focused()
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1"), width
                ctx.close()
            ctx=browser.new_context(viewport={"width":1440,"height":900})
            page=ctx.new_page()
            page.goto(BASE+"/intelligence-lab/",wait_until="networkidle")
            for module in ("growth","crm","marketing"):
                page.locator('[data-module="'+module+'"]').click()
                expect(page.locator('a[href="/intelligence-lab/facebook/"]')).to_be_visible()
            ctx.close()
            browser.close()
        assert not errors, errors
    finally:
        server.shutdown()
        server.server_close()
    print("PASS: Facebook form open/submitted states, no contact capture, 3 viewports, CRM/Growth/Marketing links")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
