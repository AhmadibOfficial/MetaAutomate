#!/usr/bin/env python3
"""Offline, synthetic-only Chromium acceptance for P2-062 workspace GUI.

Only five allowlisted files are served from apps/site on ephemeral 127.0.0.1.
Never use business data, a public host, existing developer databases or services.
Requires a previously approved local Playwright/Chromium installation.
"""
from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import tempfile
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
FAKE_CSV = ("sku,name,stock,weekly_sales,unit_price_kobo\n"
            "CAP-01,Embroidered Cap,18,0,850000\n"
            "FAB-02,Classic Kaftan,24,3,3500000\n"
            "SHO-03,Canvas Shoe,0,5,1200000\n").encode("utf-8")


class StrictHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ALLOW or self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}":
            self.send_error(404)
            return
        relative, mime = ALLOW[self.path]
        path = SITE / relative
        if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != SITE.parent):
            self.send_error(403)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        self.send_error(405)

    def log_message(self, format, *args):
        pass


def run(out: Path | None):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit("BROWSER_ACCEPTANCE_BLOCKED: install approved Playwright outside the repository") from exc

    if out is not None:
        if out.exists() or out.is_symlink() or ROOT in out.parents:
            raise SystemExit("BROWSER_ACCEPTANCE_BLOCKED: choose a NEW directory outside the Git checkout")
        out.mkdir(parents=True, mode=0o700)
    server = ThreadingHTTPServer(("127.0.0.1", 0), StrictHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    violations: list[str] = []
    errors: list[str] = []
    try:
        with sync_playwright() as playwright:
            exe = os.environ.get("MAT_CHROMIUM_EXECUTABLE")
            if exe and not Path(exe).is_file():
                raise RuntimeError("Configured Chromium executable does not exist")
            browser = playwright.chromium.launch(headless=True, executable_path=exe or None)
            try:
                page = browser.new_page(viewport={"width": 1440, "height": 900}, accept_downloads=True)
                def check_request(route):
                    url = urlsplit(route.request.url)
                    if url.scheme != "http" or url.netloc != f"127.0.0.1:{server.server_port}" or url.path not in ALLOW:
                        violations.append(route.request.url)
                        route.abort()
                    else:
                        route.continue_()
                page.route("**/*", check_request)
                page.on("pageerror", lambda exception: errors.append(str(exception)))
                assert page.goto(origin + "/workspace/", wait_until="load").status == 200
                assert page.locator("#view-overview").is_visible()
                assert page.locator("#view-inventory").is_hidden()
                page.locator('a[data-route="inventory"]').first.click()
                assert page.locator("#view-inventory").is_visible()
                with page.expect_download() as sample:
                    page.locator("#download-sample").click()
                assert sample.value.suggested_filename == "metaautomate-sample-inventory.csv"
                page.locator("#inventory-file").set_input_files({
                    "name": "fake-inventory.csv", "mimeType": "text/csv", "buffer": FAKE_CSV
                })
                page.locator("#inventory-form button[type=submit]").click()
                assert page.locator("#inventory-total").inner_text() == "3"
                assert page.locator("#inventory-candidates").inner_text() == "2"
                assert page.locator("#inventory-table tr").count() == 3
                page.locator('a[data-route="campaign"]').first.click()
                assert page.locator("#draft-form").is_visible()
                page.locator("#brand-name").fill("Fictional Demo Brand")
                page.locator("#draft-form button[type=submit]").click()
                assert page.locator("#draft-output").is_visible()
                assert "Fictional Demo Brand" in page.locator("#draft-text").input_value()
                assert page.locator("#copy-draft").is_disabled()
                page.locator("#review-check").check()
                page.locator("#record-review").click()
                assert page.locator("#save-draft").is_enabled()
                page.locator("#draft-text").fill("Revised fake content")
                assert page.locator("#save-draft").is_disabled(), "Editing must revoke approval"
                assert not page.locator("#review-check").is_checked()
                page.locator("#review-check").check()
                page.locator("#record-review").click()
                with page.expect_download() as draft:
                    page.locator("#save-draft").click()
                assert draft.value.suggested_filename == "metaautomate-reviewed-draft.txt"
                page.locator('a[data-route="evidence"]').first.click()
                with page.expect_download() as receipt:
                    page.locator("#export-evidence").click()
                path = receipt.value.path()
                report = json.loads(Path(path).read_text("utf-8"))
                assert report["independentlyVerified"] is False
                assert report["revenueVerified"] is False
                assert report["externalPublishingPerformed"] is False
                assert report["payload"]["approvalScope"] == "COPY_OR_DOWNLOAD_ONLY"
                if out:
                    page.screenshot(path=str(out / "workspace-desktop.png"), full_page=True)
                page.locator('a[data-route="modules"]').first.click()
                page.locator("#module-search").fill("creative")
                assert page.locator("#module-grid .module-card:visible").count() == 1
                page.locator("#module-search").fill("nonexistent-service-name")
                assert page.locator("#module-no-results").is_visible()
                page.locator("#module-search").fill("")
                mobile = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True,
                                          device_scale_factor=1, accept_downloads=False)
                mobile.route("**/*", check_request)
                mobile.on("pageerror", lambda exception: errors.append(str(exception)))
                assert mobile.goto(origin + "/workspace/", wait_until="load").status == 200
                assert mobile.locator("#menu-toggle").is_visible()
                mobile.locator("#menu-toggle").click()
                assert mobile.locator("#sidebar").evaluate("el => el.classList.contains('open')")
                mobile.locator('.rail-nav a[data-route="readiness"]').click()
                assert mobile.locator("#view-readiness").is_visible()
                assert mobile.locator("#sidebar").evaluate("el => !el.classList.contains('open')")
                sizes = mobile.evaluate("({ body: document.documentElement.scrollWidth, viewport: innerWidth })")
                assert sizes["body"] <= sizes["viewport"] + 2, sizes
                if out:
                    mobile.screenshot(path=str(out / "workspace-mobile.png"), full_page=True)
                assert not violations, f"Off-origin or unapproved requests attempted: {violations}"
                assert not errors, f"Page errors: {errors}"
                result = {
                    "result": "DEVELOPER_LOCAL_BROWSER_PASS",
                    "fixture": "FICTIONAL_DATA_ONLY",
                    "testScopes": ["1440 desktop", "390 mobile", "real CSV parsing", "draft review/revocation",
                                   "local JSON/text downloads", "module filtering", "zero off-origin traffic"],
                    "productionApproved": False, "sourceAuthenticated": False, "ciVerified": False
                }
                if out:
                    (out / "browser-report.json").write_text(json.dumps(result, indent=2) + "\n", "utf-8")
                print(json.dumps(result, sort_keys=True))
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, help="New private artifact directory outside this checkout")
    args = parser.parse_args()
    run(args.output_dir)
