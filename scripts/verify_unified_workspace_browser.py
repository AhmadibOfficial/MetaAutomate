#!/usr/bin/env python3
"""Synthetic-only, offline Playwright acceptance for simplified MetaAutomate GUI.

Serves exactly five approved static assets on ephemeral loopback; blocks external
requests. No personal information, customer systems, migrations or publishing.
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "apps/site"
ALLOW = {
    "/workspace/": ("workspace/index.html", "text/html; charset=utf-8"),
    "/assets/unified-workspace.css": ("assets/unified-workspace.css", "text/css; charset=utf-8"),
    "/assets/unified-workspace.js": ("assets/unified-workspace.js", "text/javascript; charset=utf-8"),
    "/assets/campaign-engine.js": ("assets/campaign-engine.js", "text/javascript; charset=utf-8"),
    "/assets/metaautomate-mark.webp": ("assets/metaautomate-mark.webp", "image/webp"),
}
FAKE_CSV = (
    "sku,name,stock,weekly_sales,unit_price_kobo\n"
    "CAP-01,Example Cap,18,0,850000\n"
    "KAF-02,Example Kaftan,24,3,3500000\n"
    "SHO-03,Example Shoes,0,5,1200000\n"
).encode("utf-8")

class StaticHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        expected=f"127.0.0.1:{self.server.server_port}"
        if self.path not in ALLOW or self.headers.get("Host") != expected:
            self.send_error(404)
            return
        rel,mime=ALLOW[self.path]
        path=SITE / rel
        if path.is_symlink() or any(part.is_symlink() for part in path.parents if part != SITE.parent):
            self.send_error(403)
            return
        data=path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type",mime)
        self.send_header("Content-Length",str(len(data)))
        self.send_header("X-Content-Type-Options","nosniff")
        self.end_headers()
        self.wfile.write(data)
    def do_POST(self):
        self.send_error(405)
    def log_message(self,format,*args):
        return

def main():
    try:
        from playwright.sync_api import expect, sync_playwright
    except ImportError as exc:
        raise SystemExit("BROWSER_TEST_BLOCKED: approved Playwright installation required") from exc
    server=ThreadingHTTPServer(("127.0.0.1",0),StaticHandler)
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    origin=f"http://127.0.0.1:{server.server_port}"
    errors=[]
    off_origin=[]
    try:
        with sync_playwright() as playwright:
            exe=os.environ.get("MAT_CHROMIUM_EXECUTABLE")
            if exe and not Path(exe).is_file():
                raise RuntimeError("Requested Chromium executable does not exist")
            browser=playwright.chromium.launch(headless=True,executable_path=exe or None)
            try:
                page=browser.new_page(viewport={"width":1440,"height":900},accept_downloads=True)
                def local_only(route):
                    url=urlsplit(route.request.url)
                    if url.scheme!="http" or url.netloc!=f"127.0.0.1:{server.server_port}" or url.path not in ALLOW:
                        off_origin.append(route.request.url)
                        route.abort()
                    else:
                        route.continue_()
                page.route("**/*",local_only)
                page.on("pageerror",lambda e:errors.append(str(e)))
                response_status=[]
                page.on("response", lambda r: response_status.append((r.url, r.status)))
                assert page.goto(origin+"/workspace/",wait_until="load").status==200
                if not page.locator("#view-home").is_visible():
                    raise AssertionError("Unexpected invisible Home: " + json.dumps({
                        "url": page.url,
                        "html_present": page.locator("#view-home").count(),
                        "hidden": page.locator("#view-home").get_attribute("hidden") if page.locator("#view-home").count() else None,
                        "display": page.locator("#view-home").evaluate("(el)=>getComputedStyle(el).display") if page.locator("#view-home").count() else None,
                        "errors": errors,
                        "off_origin": off_origin,
                        "responses": response_status,
                    }))
                assert page.locator("[data-sector]").count()==5
                assert page.locator(".sidebar-nav a").count()==4
                for key in ["sales","healthcare","realestate","retail","cloud"]:
                    page.locator('[data-sector="'+key+'"]').click()
                    assert page.locator('[data-sector="'+key+'"]').get_attribute("aria-pressed")=="true"
                # Five independently reset technical flows, one synthetic source.
                # These are automated checks, never five independent human sessions.
                business_cases = [
                    ("sales", "Review customer inquiry follow-ups"),
                    ("healthcare", "Review appointment administration"),
                    ("realestate", "Coordinate property viewing requests"),
                    ("retail", "Review stock reconciliation"),
                    ("cloud", "Review approved technology costs"),
                ]
                for sector, challenge in business_cases:
                    page.locator('[data-sector="' + sector + '"]').click()
                    page.locator("#challenge").fill(challenge)
                    page.locator("#new-work-form button[type=submit]").click()
                    expect(page.locator("#view-work")).to_be_visible()
                    assert page.locator("#plan-list .plan-button").count() == 1
                    assert page.locator("#complete-plan").is_disabled()
                    tasks = page.locator("#plan-steps input[type=checkbox]")
                    assert tasks.count() == 4
                    for index in range(4):
                        tasks.nth(index).check()
                    assert page.locator("#complete-plan").is_disabled()
                    page.locator("#plan-review").check()
                    page.locator("#complete-plan").click()
                    assert "reviewed" in page.locator("#plan-status").inner_text().lower()
                    page.locator('.sidebar-nav a[data-route="results"]').click()
                    assert page.locator("#results-plans").inner_text() == "1"
                    assert page.locator("#results-reviewed").inner_text() == "1"
                    assert page.locator("#results-steps").inner_text() == "4"
                    page.locator('.sidebar-nav a[data-route="settings"]').click()
                    page.locator("#clear-session").click()
                    page.locator('.sidebar-nav a[data-route="results"]').click()
                    assert page.locator("#results-plans").inner_text() == "0"
                    assert page.locator("#results-reviewed").inner_text() == "0"
                    page.locator('.sidebar-nav a[data-route="home"]').click()
                    expect(page.locator("#view-home")).to_be_visible()
                # Continue separate evidence/inventory/mobile regression tests.
                page.locator('[data-sector="realestate"]').click()
                page.locator("#challenge").fill("Reduce time between viewing request and agent review")
                page.locator("#new-work-form button[type=submit]").click()
                expect(page.locator("#view-work")).to_be_visible()
                assert page.locator("#plan-list .plan-button").count()==1
                assert page.locator("#complete-plan").is_disabled()
                checklist=page.locator("#plan-steps input[type=checkbox]")
                assert checklist.count()==4
                for i in range(4):
                    checklist.nth(i).check()
                assert page.locator("#complete-plan").is_disabled()
                page.locator("#plan-review").check()
                page.locator("#complete-plan").click()
                assert "reviewed" in page.locator("#plan-status").inner_text().lower()
                page.locator('.sidebar-nav a[data-route="results"]').click()
                assert page.locator("#results-plans").inner_text()=="1"
                assert page.locator("#results-reviewed").inner_text()=="1"
                assert page.locator("#results-steps").inner_text()=="4"
                with page.expect_download() as report:
                    page.locator("#export-evidence").click()
                obj=json.loads(Path(report.value.path()).read_text(encoding="utf-8"))
                assert obj["independentlyVerified"] is False
                assert obj["outsideActionsPerformed"] is False
                assert obj["customerTractionVerified"] is False
                assert obj["localReviewedPlanCount"]==1
                page.locator('.sidebar-nav a[data-route="work"]').click()
                page.locator("#inventory-helper summary").click()
                page.locator("#inventory-file").set_input_files({
                    "name":"synthetic.csv","mimeType":"text/csv","buffer":FAKE_CSV
                })
                page.locator("#inventory-form button[type=submit]").click()
                assert "3 products checked" in page.locator("#inventory-summary").inner_text()
                assert page.locator("#inventory-table tr").count()==3
                page.locator("#draft-form button[type=submit]").click()
                assert page.locator("#draft-output").is_visible()
                assert page.locator("#save-draft").is_disabled()
                page.locator("#review-check").check()
                page.locator("#record-review").click()
                assert page.locator("#save-draft").is_enabled()
                page.locator("#draft-text").fill("Revised sample copy")
                assert page.locator("#save-draft").is_disabled()
                page.locator("#inventory-file").set_input_files({
                    "name":"unsafe.csv","mimeType":"text/csv",
                    "buffer":b"sku,name,stock,weekly_sales,unit_price_kobo\nCAP-01,=SUM(1),18,0,850000\n"
                })
                page.locator("#inventory-form button[type=submit]").click()
                assert page.locator("#inventory-results").is_hidden()
                page.locator('.sidebar-nav a[data-route="settings"]').click()
                expect(page.locator("#view-settings")).to_be_visible()
                page.locator("#clear-session").click()
                page.locator('.sidebar-nav a[data-route="results"]').click()
                assert page.locator("#results-plans").inner_text()=="0"
                assert page.locator("#results-products").inner_text()=="0"
                mobile=browser.new_page(viewport={"width":390,"height":844},is_mobile=True)
                mobile.route("**/*",local_only)
                mobile.on("pageerror",lambda e:errors.append(str(e)))
                assert mobile.goto(origin+"/workspace/",wait_until="load").status==200
                mobile.locator("#menu-toggle").click()
                assert mobile.locator("#sidebar").evaluate("n => n.classList.contains('open')")
                mobile.locator('.sidebar-nav a[data-route="work"]').click()
                assert mobile.locator("#view-work").is_visible()
                assert not mobile.locator("#sidebar").evaluate("n => n.classList.contains('open')")
                viewport=mobile.evaluate("({scroll:document.documentElement.scrollWidth,viewport:innerWidth})")
                assert viewport["scroll"]<=viewport["viewport"]+2,viewport
                assert not errors, errors
                assert not off_origin, off_origin
                print(json.dumps({"result":"DEVELOPER_LOCAL_BROWSER_PASS",
                    "scope":"synthetic, loopback-only","screens":4,"industries":5,"sectorPlanFlowsChecked":5,
                    "evidence":"user-declared, not independently verified","ciVerified":False,
                    "productionApproved":False},sort_keys=True))
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=4)

if __name__=="__main__":
    main()
