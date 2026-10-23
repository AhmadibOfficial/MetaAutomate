#!/usr/bin/env python3
"""P2-060 Chromium acceptance: local import, recommendation, creative, consent, evidence."""
from __future__ import annotations

import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = "http://127.0.0.1:18080"
OUT = Path("artifacts/validation/p2-060")
OUT.mkdir(parents=True, exist_ok=True)
CSV = ("sku,name,stock,weekly_sales,unit_price_kobo\n"
       "CAP-01,Branded Cap,18,0,850000\n"
       "FAB-02,Classic Kaftan,24,3,3500000\n"
       "SHOE-03,Low Stock Shoes,1,5,1400000\n")


def run():
    errors = []
    requests = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for label, width in (("desktop", 1440), ("mobile", 390), ("small", 360)):
            context = browser.new_context(
                viewport={"width": width, "height": 900},
                accept_downloads=True, reduced_motion="reduce")
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: requests.append(request.url)
                    if not request.url.startswith(BASE) else None)
            res = page.goto(BASE + "/campaigns/", wait_until="networkidle")
            assert res.status == 200
            expect(page.get_by_role("heading", name="Work with your own stock records.")).to_be_visible()
            page.locator("#campaign-file").set_input_files({
                "name": "inventory.csv", "mimeType": "text/csv",
                "buffer": CSV.encode("utf-8")
            })
            page.locator("#campaign-import button[type=submit]").click()
            expect(page.locator("#campaign-count")).to_have_text("3")
            expect(page.locator("#campaign-flagged")).to_have_text("2")
            expect(page.locator("#campaign-results")).to_be_visible()
            assert page.locator('input[name="candidate"]').count() == 2
            page.locator("#campaign-brand").fill("MetaAutomate Sample Shop")
            page.locator("#campaign-create").click()
            expect(page.locator("#campaign-project")).to_be_visible()
            expect(page.locator("#campaign-post")).to_have_value(re.compile("Branded Cap") )
            expect(page.locator("#campaign-approval")).to_be_visible()
            assert page.locator("#campaign-copy").is_disabled()
            expect(page.locator("#campaign-canvas")).to_have_attribute("width", "1080")
            with page.expect_download() as download_info:
                page.locator("#campaign-png").click()
            png = download_info.value
            assert png.suggested_filename.endswith(".png")
            png.save_as(OUT / f"campaign-{label}.png")
            assert (OUT / f"campaign-{label}.png").stat().st_size > 5000
            with page.expect_download() as download_info:
                page.locator("#campaign-video-download").click()
            video_brief = download_info.value
            assert video_brief.suggested_filename.endswith(".txt")
            assert page.locator('a[href="/creative/#instant-video"]').count() == 1
            page.locator("#campaign-confirm").check()
            page.locator("#campaign-authorize").click()
            expect(page.locator("#campaign-approval-state")).to_contain_text("Internal draft review recorded")
            assert page.locator("#campaign-copy").is_enabled()
            page.locator("#campaign-post").fill("Changed campaign draft; review required.")
            assert page.locator("#campaign-copy").is_disabled()
            page.locator("#campaign-confirm").check()
            page.locator("#campaign-authorize").click()
            page.locator("#campaign-impressions").fill("100")
            page.locator("#campaign-clicks").fill("20")
            page.locator("#campaign-orders").fill("3")
            page.locator("#campaign-metric-source").fill("Example manually checked counts")
            page.locator("#campaign-metric-form button[type=submit]").click()
            expect(page.locator("#campaign-metrics-result")).to_contain_text("Self-reported")
            with page.expect_download() as download_info:
                page.locator("#campaign-evidence").click()
            evidence = download_info.value
            path = OUT / f"campaign-evidence-{label}.json"
            evidence.save_as(path)
            report = json.loads(path.read_text())
            assert report["safeguards"]["publishPerformed"] is False
            assert report["safeguards"]["aiModelUsed"] is False
            assert report["metrics"]["evidence"] == "SELF_REPORTED_NOT_INDEPENDENTLY_VERIFIED"
            assert report["approval"]["scope"] == "COPY_OR_DOWNLOAD_ONLY"
            dims = page.evaluate("() => ({width: innerWidth, scroll: document.documentElement.scrollWidth})")
            assert dims["scroll"] <= dims["width"] + 2, dims
            page.screenshot(path=str(OUT / f"campaign-workbench-{label}.png"), full_page=True)
            assert not errors, errors
            assert not requests, requests
            context.close()
        browser.close()
    print("PASS: P2-060 import -> assessment -> graphic/video brief -> review -> metrics, 1440/390/360px")
    print("No cross-origin requests and no external publishing performed.")


if __name__ == "__main__":
    run()
