#!/usr/bin/env python3
"""P2-060f exact-origin Chromium proof of dated, unverified inventory quality.

Only synthetic stock. No external requests, persistent test artifacts, customer
identity, cloud services, publishing, AI or model-based forecasting.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_campaign_workbench_browser import (
    CSV, ensure_playwright_driver, launch_full_chromium, same_origin, serve_local
)


def fixtures() -> tuple[str, str]:
    today = datetime.now(timezone.utc).date()
    iso = lambda offset: (today + timedelta(days=offset)).isoformat()
    header = (
        "sku,name,stock,weekly_sales,unit_price_kobo,stock_count_status,"
        "sales_coverage_status,stock_observed_on,sales_period_start,sales_period_end\n"
    )
    rows = [
        f"CAP-01,Branded Cap,18,0,850000,counted,complete,{iso(0)},{iso(-6)},{iso(0)}",
        f"FAB-02,Stale Stock,24,3,3500000,counted,complete,{iso(-8)},{iso(-6)},{iso(0)}",
        f"SLOW-03,Stale Sales,18,0,900000,counted,complete,{iso(0)},{iso(-14)},{iso(-8)}",
        f"MISMATCH-04,Wrong Period,25,2,3000000,counted,complete,{iso(0)},{iso(-5)},{iso(0)}",
        f"SHOE-05,Low Stock,1,5,1400000,counted,complete,{iso(0)},{iso(-6)},{iso(0)}",
    ]
    return header + "\n".join(rows) + "\n", today.isoformat()


def import_csv(page, csv: str) -> None:
    page.locator("#campaign-file").set_input_files({
        "name": "synthetic-dated.csv", "mimeType": "text/csv",
        "buffer": csv.encode("utf-8")
    })
    page.locator("#campaign-import button[type=submit]").click()


def download_json(page, button: str) -> dict:
    with page.expect_download() as download:
        page.locator(button).click()
    temporary_file = download.value.path()
    assert temporary_file is not None
    return json.loads(Path(temporary_file).read_text(encoding="utf-8"))


def exercise(browser, base: str, width: int) -> None:
    from playwright.sync_api import expect

    context = browser.new_context(
        viewport={"width": width, "height": 900}, accept_downloads=True,
        reduced_motion="reduce", service_workers="block"
    )
    errors: list[str] = []
    outbound: list[str] = []
    try:
        def restrict(route):
            if same_origin(route.request.url, base):
                route.continue_()
            else:
                outbound.append(route.request.url)
                route.abort()
        context.route("**/*", restrict)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        response = page.goto(base + "/campaigns/", wait_until="networkidle")
        assert response and response.status == 200

        csv, assessment_date = fixtures()
        import_csv(page, csv)
        expect(page.locator("#campaign-count")).to_have_text("5")
        expect(page.locator("#campaign-flagged")).to_have_text("1")
        expect(page.locator("#campaign-quality-note")).to_contain_text("3 candidate(s) held")
        expect(page.locator("#campaign-quality-note")).to_contain_text("5 dated row(s)")
        expect(page.locator("#campaign-date-note")).to_contain_text(assessment_date)
        expect(page.locator("#campaign-quality-held")).to_be_visible()
        assert page.locator('input[name="candidate"]').count() == 1
        assert page.locator('input[name="candidate"]').first.get_attribute("value") == "CAP-01"

        trace = download_json(page, "#campaign-quality-export")
        assert trace["classification"] == "USER_SUPPLIED_UNVERIFIED"
        assert trace["asOfDate"] == assessment_date
        assert (trace["candidateCount"], trace["heldCount"]) == (1, 3)
        assert (trace["datedCount"], trace["undatedCount"]) == (5, 0)
        records = {row["sku"]: row for row in trace["records"]}
        assert records["CAP-01"]["decision"] == "no-sales"
        assert records["CAP-01"]["stockObservedOn"] == assessment_date
        assert records["FAB-02"]["decision"] == "quality-hold"
        assert records["FAB-02"]["quality"]["inventoryAgeDays"] == 8
        assert records["SLOW-03"]["quality"]["salesEndAgeDays"] == 8
        assert records["MISMATCH-04"]["decision"] == "quality-hold"
        assert records["SHOE-05"]["decision"] == "low-stock"
        assert trace["safeguards"]["inventoryIndependentlyVerified"] is False

        page.locator("#campaign-brand").fill("Synthetic MetaAutomate Shop")
        page.locator("#campaign-create").click()
        expect(page.locator("#project-title")).to_be_focused()
        expect(page.locator("#campaign-reason")).to_contain_text("self-declared")
        page.locator("#campaign-confirm").check()
        page.locator("#campaign-authorize").click()
        evidence = download_json(page, "#campaign-evidence")
        assert evidence["inputQuality"]["mode"] == "DATED_SELF_DECLARED"
        assert evidence["inputQuality"]["stockObservedOn"] == assessment_date
        assert evidence["inputQuality"]["basis"] == "USER_SUPPLIED_UNVERIFIED"
        assert evidence["safeguards"]["publishPerformed"] is False
        assert evidence["safeguards"]["aiModelUsed"] is False

        # Old file format still works but does not acquire invented dates.
        import_csv(page, CSV)
        expect(page.locator("#campaign-flagged")).to_have_text("2")
        expect(page.locator("#campaign-quality-note")).to_contain_text("3 undated row(s)")
        legacy = download_json(page, "#campaign-quality-export")
        assert legacy["datedCount"] == 0 and legacy["legacyCount"] == 3
        assert all(row["stockObservedOn"] is None for row in legacy["records"])

        assert not errors, errors
        assert not outbound, outbound
        dims = page.evaluate(
            "() => ({width:innerWidth,scroll:document.documentElement.scrollWidth})"
        )
        assert dims["scroll"] <= dims["width"] + 2, dims
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
    print("DEVELOPER_LOCAL_TEMPORAL_EVIDENCE_PASS")
    print("Dated stock/weekly-sales holds, exact UTC periods, trace, and legacy import checked.")
    print("Synthetic only; NO independently authenticated inventory, CI, model or publication.")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"TEMPORAL_EVIDENCE_BLOCKED: {type(exc).__name__}: {exc}",
              file=sys.stderr)
        raise SystemExit(2) from None
