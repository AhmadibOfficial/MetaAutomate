#!/usr/bin/env python3
"""P2-03s visual browser acceptance: continuity KPIs, scenarios and source links."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright

ROOT=Path(__file__).resolve().parents[1]
BASE="http://127.0.0.1:18585"
ART=ROOT/"artifacts/validation"


def main():
    ART.mkdir(parents=True,exist_ok=True)
    server=ThreadingHTTPServer(("127.0.0.1",18585),
       partial(SimpleHTTPRequestHandler,directory=str(ROOT/"apps/site")))
    Thread(target=server.serve_forever,daemon=True).start()
    failures=[]
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(headless=True)
            for width in (1440,390,360):
                context=browser.new_context(viewport={"width":width,"height":900},
                                           reduced_motion="reduce",device_scale_factor=1)
                page=context.new_page()
                page.on("pageerror",lambda error:failures.append(str(error)))
                page.on("request",lambda req:failures.append("External: "+req.url)
                        if not req.url.startswith(BASE+"/") else None)
                res=page.goto(BASE+"/intelligence-lab/continuity/",wait_until="networkidle")
                assert res and res.status==200
                expect(page).to_have_title("Continuity & Cost Intelligence — MetaAutomate | Source Preview")
                expect(page.locator("#kpis .kpi")).to_have_count(4)
                expect(page.locator("#kpis .kpi").nth(0)).to_contain_text("25,000")
                expect(page.locator("#kpis .kpi").nth(2)).to_contain_text("12,300")
                expect(page.locator(".risk-card")).to_have_count(3)
                expect(page.locator("#risk-list")).to_contain_text("Supplier Delay")
                expect(page.locator("#scenario-results")).to_contain_text("12,300")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"),width
                if width==1440:
                    page.screenshot(path=str(ART/"continuity-desktop.png"),full_page=True)
                else:
                    page.screenshot(path=str(ART/f"continuity-mobile-{width}.png"),full_page=True)
                page.locator("#scenario").select_option("DEMAND_DOWN_25")
                expect(page.locator("#scenario-results")).to_contain_text("18,750")
                expect(page.locator("#scenario-results")).to_contain_text("6,050")
                page.locator("#scenario").select_option("COMBINED_STRESS")
                expect(page.locator("#scenario-results")).to_contain_text("15,240")
                expect(page.locator("#scenario-results")).to_contain_text("3,510")
                page.locator("#business").select_option("bespoke_demo")
                expect(page.locator("#kpis .kpi").nth(0)).to_contain_text("35,000")
                expect(page.locator("#kpis .kpi").nth(2)).to_contain_text("4,700")
                page.locator("#scenario").select_option("UNCHANGED")
                expect(page.locator("#scenario-results")).to_contain_text("4,700")
                expect(page.locator(".risk-card").first).to_contain_text("20 / 25")
                expect(page.locator(".pilot-grid article")).to_have_count(3)
                page.locator("#scenario").focus()
                expect(page.locator("#scenario")).to_be_focused()
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"),width
                context.close()
            ctx=browser.new_context(viewport={"width":1440,"height":900})
            page=ctx.new_page()
            page.goto(BASE+"/intelligence-lab/",wait_until="networkidle")
            for module in ("finance","operations","executive"):
                page.locator('[data-module="'+module+'"]').click()
                expect(page.locator('a[href="/intelligence-lab/continuity/"]')).to_be_visible()
            ctx.close()
            browser.close()
        assert not failures,failures
    finally:
        server.shutdown();server.server_close()
    print("PASS: 3 continuity viewports, scenarios, human-only playbooks, finance/operations/executive navigation")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
