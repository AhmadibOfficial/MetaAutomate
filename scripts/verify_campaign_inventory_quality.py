#!/usr/bin/env python3
"""P2-060e: real Chromium acceptance for cautious inventory quality decisions.

All records are fabricated. Downloads are read only from Playwright's own
temporary download files and not persisted in the repository. No publishing,
remote inference, production data, provider credentials or external requests.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_campaign_workbench_browser import (
    CSV, ensure_playwright_driver, launch_full_chromium, same_origin, serve_local,
)

ENHANCED = (
    "sku,name,stock,weekly_sales,unit_price_kobo,stock_count_status,sales_coverage_status\n"
    "CAP-01,Branded Cap,18,0,850000,unknown,unknown\n"
    "FAB-02,Classic Kaftan,24,3,3500000,counted,complete\n"
    "SHOE-03,Low Stock Shoes,1,5,1400000,unknown,partial\n"
)
ALL_HELD = (
    "sku,name,stock,weekly_sales,unit_price_kobo,stock_count_status,sales_coverage_status\n"
    "CAP-01,Branded Cap,18,0,850000,unknown,unknown\n"
)


def import_csv(page, text: str) -> None:
    page.locator("#campaign-file").set_input_files({
        "name": "synthetic.csv", "mimeType": "text/csv", "buffer": text.encode("utf-8")
    })
    page.locator("#campaign-import button[type=submit]").click()


def download_json(page, selector: str) -> dict:
    with page.expect_download() as event:
        page.locator(selector).click()
    path = event.value.path()
    assert path is not None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def exercise(browser, base: str, width: int) -> None:
    from playwright.sync_api import expect

    context = browser.new_context(
        viewport={"width": width, "height": 900}, accept_downloads=True,
        service_workers="block", reduced_motion="reduce"
    )
    errors, off_origin = [], []
    try:
        def restrict(route):
            if same_origin(route.request.url, base):
                route.continue_()
            else:
                off_origin.append(route.request.url)
                route.abort()
        context.route("**/*", restrict)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        res = page.goto(base + "/campaigns/", wait_until="networkidle")
        assert res and res.status == 200
        import_csv(page, ENHANCED)
        expect(page.locator("#campaign-count")).to_have_text("3")
        expect(page.locator("#campaign-flagged")).to_have_text("1")
        expect(page.locator("#campaign-quality-note")).to_contain_text("1 candidate(s) held")
        expect(page.locator("#campaign-quality-note")).to_contain_text("0 legacy row(s)")
        expect(page.locator("#campaign-quality-held")).to_be_visible()
        expect(page.locator("#campaign-quality-held-items")).to_contain_text("CAP-01")
        assert page.locator('input[name="candidate"]').count() == 1
        assert page.locator('input[name="candidate"]').first.get_attribute("value") == "FAB-02"
        trace = download_json(page, "#campaign-quality-export")
        assert trace["kind"] == "INVENTORY_DECISION_TRACE"
        assert trace["classification"] == "USER_SUPPLIED_UNVERIFIED"
        assert trace["candidateCount"] == 1
        assert trace["heldCount"] == 1
        assert trace["legacyCount"] == 0
        assert trace["safeguards"]["inventoryIndependentlyVerified"] is False
        held = next(row for row in trace["records"] if row["sku"] == "CAP-01")
        assert held["decision"] == "quality-hold"
        assert held["candidate"] is False
        assert held["quality"]["status"] == "REVIEW_INPUTS"
        assert not held["quality"]["basis"] == "INDEPENDENTLY_VERIFIED"

        page.locator("#campaign-brand").fill("Synthetic MetaAutomate Shop")
        page.locator("#campaign-create").click()
        expect(page.locator("#campaign-post")).to_contain_text("Classic Kaftan")
        page.locator("#campaign-confirm").check()
        page.locator("#campaign-authorize").click()
        assert page.locator("#campaign-copy").is_enabled()
        page.locator("#campaign-post").fill("Revised synthetic campaign text")
        assert page.locator("#campaign-copy").is_disabled()
        page.locator("#campaign-confirm").check()
        page.locator("#campaign-authorize").click()
        evidence = download_json(page, "#campaign-evidence")
        assert evidence["inputQuality"]["mode"] == "SELF_DECLARED"
        assert evidence["inputQuality"]["basis"] == "USER_SUPPLIED_UNVERIFIED"
        assert evidence["safeguards"]["publishPerformed"] is False
        assert evidence["safeguards"]["aiModelUsed"] is False

        import_csv(page, ALL_HELD)
        expect(page.locator("#campaign-flagged")).to_have_text("0")
        expect(page.locator("#campaign-quality-note")).to_contain_text("1 candidate(s) held")
        assert page.locator("#campaign-create").is_disabled()
        assert page.locator("#campaign-quality-export").is_enabled()

        # Old 5-column customers retain the original workflow, explicitly
        # marked as missing completeness declarations rather than verified.
        import_csv(page, CSV)
        expect(page.locator("#campaign-count")).to_have_text("3")
        expect(page.locator("#campaign-flagged")).to_have_text("2")
        expect(page.locator("#campaign-quality-note")).to_contain_text("3 legacy row(s)")
        old = download_json(page, "#campaign-quality-export")
        assert old["legacyCount"] == 3 and old["heldCount"] == 0
        assert all(row["quality"]["mode"] == "LEGACY_UNATTESTED"
                   for row in old["records"])
        assert not errors, errors
        assert not off_origin, off_origin
        size = page.evaluate("() => ({width:innerWidth,scroll:document.documentElement.scrollWidth})")
        assert size["scroll"] <= size["width"] + 2, size
    finally:
        context.close()


def run() -> None:
    ensure_playwright_driver()
    with serve_local() as base:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = launch_full_chromium(pw)
            try:
                for width in (1440, 390, 320):
                    exercise(browser, base, width)
            finally:
                browser.close()
    print("DEVELOPER_LOCAL_INVENTORY_QUALITY_PASS")
    print("Enhanced held/allowed decisions, export, re-review, and legacy compatibility checked.")
    print("Synthetic-only; no independent data verification, external requests or publication.")


if __name__ == "__main__":
    try:
        run()
    except Exception as error:
        print(f"INVENTORY_QUALITY_BLOCKED: {type(error).__name__}: {error}",
              file=sys.stderr)
        raise SystemExit(2) from None
