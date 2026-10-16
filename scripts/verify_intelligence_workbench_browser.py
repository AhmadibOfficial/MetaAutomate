#!/usr/bin/env python3
"""P2-03u: three responsive viewports, offline safety, usable export and navigation."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright

ROOT=Path(__file__).resolve().parents[1]
BASE="http://127.0.0.1:18686"
ART=ROOT/"artifacts/validation"


def main() -> int:
    ART.mkdir(parents=True,exist_ok=True)
    server=ThreadingHTTPServer(("127.0.0.1",18686),
        partial(SimpleHTTPRequestHandler,directory=str(ROOT/"apps/site")))
    Thread(target=server.serve_forever,daemon=True).start()
    errors=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            for width in (1440,390,360):
                context=browser.new_context(
                    viewport={"width":width,"height":900},
                    reduced_motion="reduce",device_scale_factor=1,
                    accept_downloads=True,
                )
                page=context.new_page()
                page.on("pageerror",lambda error:errors.append(str(error)))
                page.on("request",lambda req:errors.append("External: "+req.url)
                    if not req.url.startswith(BASE+"/") and not req.url.startswith("blob:")
                    else None)
                response=page.goto(BASE+"/intelligence/",wait_until="networkidle")
                assert response and response.status==200
                expect(page).to_have_title("01 / Intelligence — AI Project Workbench | MetaAutomate")
                expect(page.locator("#graph li")).to_have_count(5)
                expect(page.locator("#graph")).to_contain_text("External action (disabled)")
                expect(page.locator("#blockers li")).to_have_count(3)
                expect(page.locator("#baseline")).to_contain_text("12 example records")
                expect(page.locator("#simulation")).to_contain_text("Ready to simulate")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1"),width
                if width==1440:
                    page.screenshot(path=str(ART/"intelligence-desktop.png"),full_page=True)
                else:
                    page.screenshot(path=str(ART/f"intelligence-mobile-{width}.png"),
                                    full_page=True)
                page.locator("#simulate").click()
                expect(page.locator("#simulation")).to_contain_text(
                    "0 provider calls, 0 AI model calls, 0 CRM writes")
                page.locator("#scenario").select_option("INVENTORY_RESILIENCE")
                expect(page.locator("#plan-heading")).to_have_text("Inventory Resilience")
                expect(page.locator("#objective")).to_contain_text("stock availability risks")
                page.locator("#data-state").select_option("MISSING")
                expect(page.locator("#blockers")).to_contain_text("representative data source")
                page.locator("#sensitivity").select_option("PERSONAL")
                expect(page.locator("#blockers")).to_contain_text("privacy review")
                page.locator("#request").select_option("REQUEST_EXTERNAL_WORKFLOW")
                expect(page.locator("#blockers")).to_contain_text("External platform permissions")
                expect(page.locator("#graph")).to_contain_text("Blocked")
                page.locator("#scenario").select_option("CONTENT_OPERATIONS")
                expect(page.locator("#plan-heading")).to_have_text("Content Operations")
                expect(page.locator("#graph")).to_contain_text("Proposed social publishing")
                page.locator("#simulate").click()
                expect(page.locator("#simulation")).to_contain_text("EXTERNAL never ran")
                with page.expect_download() as info:
                    page.locator("#download").click()
                download=info.value
                assert download.suggested_filename=="metaautomate-intelligence-example-plan.json"
                payload=json.loads(Path(download.path()).read_text(encoding="utf-8"))
                assert payload["project"]["id"]=="CONTENT_OPERATIONS"
                assert payload["classification"]=="SYNTHETIC_SOURCE_ONLY"
                assert payload["choices"]["requested_action"]=="REQUEST_EXTERNAL_WORKFLOW"
                assert payload["workflow"][-1]["status"]=="BLOCKED_EXTERNAL"
                assert not payload["workflow"][-1]["actual_execution_authorized"]
                assert payload["evidence"]["external_actions_attempted"]==0
                page.locator("#scenario").focus()
                expect(page.locator("#scenario")).to_be_focused()
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1"),width
                context.close()
            context=browser.new_context(viewport={"width":1400,"height":900})
            page=context.new_page()
            page.goto(BASE+"/services/",wait_until="networkidle")
            expect(page.locator("#ai a[href='/intelligence/']")).to_be_visible()
            expect(page.locator("#ai a[href^='/engage/']")).to_be_visible()
            context.close()
            browser.close()
        assert not errors,errors
    finally:
        server.shutdown()
        server.server_close()
    print("PASS: Intelligence workbench, 4 scenarios, human stop, no network, export, 3 layouts and services link")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
