#!/usr/bin/env python3
"""P2-060g isolated Chromium proof: dated stock reconciliation, no network egress.

The whole run uses synthetic inventory, loopback read-only site and no cloud
operations or production customer data. Checks arithmetic, conflicting sales
windows, missing SKUs, exported SHA-256 digest and download invalidation.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_campaign_workbench_browser import (
    ensure_playwright_driver, launch_full_chromium, same_origin, serve_local
)

HEADER = (
    "sku,name,stock,weekly_sales,unit_price_kobo,stock_count_status,"
    "sales_coverage_status,stock_observed_on,sales_period_start,sales_period_end"
)
LEDGER = (
    "sku,period_start,period_end,received_units,customer_returns_units,"
    "adjustment_units,sold_units"
)


def sample():
    today = datetime.now(timezone.utc).date()
    fmt = lambda days: (today + timedelta(days=days)).isoformat()
    earlier, first, last = fmt(-7), fmt(-6), fmt(0)
    before = [
        f"CAP-01,Branded Cap,10,2,850000,counted,complete,{earlier},{fmt(-13)},{earlier}",
        f"FAB-02,Classic Kaftan,8,1,3500000,counted,complete,{earlier},{fmt(-13)},{earlier}",
        f"SHOE-03,Shoes,12,2,1500000,counted,complete,{earlier},{fmt(-13)},{earlier}",
        f"REM-04,Discontinued Item,4,0,100000,counted,complete,{earlier},{fmt(-13)},{earlier}",
    ]
    after = [
        f"CAP-01,Branded Cap,11,3,850000,counted,complete,{last},{first},{last}",
        f"FAB-02,Classic Kaftan,10,1,3500000,counted,complete,{last},{first},{last}",
        f"SHOE-03,Shoes,10,3,1500000,counted,complete,{last},{first},{last}",
        f"NEW-05,New Product,2,0,150000,counted,complete,{last},{first},{last}",
    ]
    moves = [
        f"CAP-01,{first},{last},4,1,-1,3",
        f"FAB-02,{first},{last},2,0,0,1",
        f"SHOE-03,{first},{last},0,0,0,2",
    ]
    return ("\n".join([HEADER, *before]) + "\n",
            "\n".join([HEADER, *after]) + "\n",
            "\n".join([LEDGER, *moves]) + "\n", today.isoformat())


def upload(page, selector: str, data: str) -> None:
    page.locator(selector).set_input_files({
        "name": "synthetic-source.csv",
        "mimeType": "text/csv", "buffer": data.encode("utf-8")
    })


def exercise(browser, base: str, width: int) -> None:
    from playwright.sync_api import expect

    context = browser.new_context(
        viewport={"width": width, "height": 900},
        accept_downloads=True, service_workers="block", reduced_motion="reduce"
    )
    off_origin: list[str] = []
    page_errors: list[str] = []
    try:
        def restrict(route):
            if same_origin(route.request.url, base):
                route.continue_()
            else:
                off_origin.append(route.request.url)
                route.abort()
        context.route("**/*", restrict)
        page = context.new_page()
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        result = page.goto(base + "/campaigns/", wait_until="networkidle")
        assert result and result.status == 200

        previous, current, movement, reference = sample()
        upload(page, "#reconcile-previous", previous)
        upload(page, "#reconcile-current", current)
        upload(page, "#reconcile-ledger", movement)
        page.locator("#reconcile-date").fill(reference)
        page.locator("#reconcile-run").click()
        expect(page.locator("#reconcile-results-title")).to_be_focused()
        expect(page.locator("#reconcile-summary")).to_contain_text("5 SKU(s) reviewed")
        expect(page.locator("#reconcile-summary")).to_contain_text("1 stock conflict(s)")
        expect(page.locator("#reconcile-summary")).to_contain_text("1 comparable sales conflict(s)")
        assert page.locator("#reconcile-items li").count() == 5
        expect(page.locator("#reconcile-export")).to_be_enabled()

        with page.expect_download() as dl:
            page.locator("#reconcile-export").click()
        artifact = dl.value.path()
        assert artifact is not None
        wrapper = json.loads(Path(artifact).read_text(encoding="utf-8"))
        assert wrapper["kind"] == "OWNER_GENERATED_RECONCILIATION_REPORT"
        assert wrapper["provenance"] == "USER_SUPPLIED_UNVERIFIED"
        assert wrapper["fingerprint"]["authenticatesSources"] is False
        assert wrapper["fingerprint"]["digitallySigned"] is False
        payload = wrapper["payload"]
        # P2-060h: fingerprints must match the *exact* imported UTF-8 CSV bytes,
        # not only the derived stock calculations. No source authentication.
        manifest = wrapper["inputManifest"]
        assert manifest["classification"] == "USER_SUPPLIED_UNVERIFIED"
        assert manifest["sourceAuthenticated"] is False
        assert manifest["consentVerified"] is False
        assert manifest["timestampAuthenticated"] is False
        assert manifest["includesOriginalFiles"] is False
        for entry, role, raw in zip(manifest["inputs"],
                                    ("previous_snapshot", "current_snapshot", "movement_ledger"),
                                    (previous, current, movement)):
            assert entry["role"] == role
            assert entry["byteLength"] == len(raw.encode("utf-8"))
            assert entry["sha256"] == hashlib.sha256(raw.encode("utf-8")).hexdigest()
        binding = wrapper["sourceBinding"]
        assert binding["authenticatesSources"] is False
        assert binding["digitallySigned"] is False
        bundle = json.dumps({"inputManifest": manifest, "payload": payload},
                            ensure_ascii=False, indent=2) + "\n"
        assert binding["sha256"] == hashlib.sha256(bundle.encode("utf-8")).hexdigest()
        assert payload["asOfDate"] == reference
        assert payload["counts"] == {
            "totalSkus": 5, "declaredArithmeticMatches": 1,
            "stockConflicts": 1, "salesConflicts": 1, "reviewRequired": 4
        }
        rows = {row["sku"]: row for row in payload["rows"]}
        assert rows["CAP-01"]["status"] == "DECLARED_ARITHMETIC_MATCH"
        assert rows["CAP-01"]["expectedStock"] == 11
        assert rows["CAP-01"]["comparedWeeklySales"] is True
        assert rows["FAB-02"]["status"] == "STOCK_ARITHMETIC_CONFLICT"
        assert rows["FAB-02"]["differenceUnits"] == 1
        assert rows["SHOE-03"]["status"] == "SALES_COUNT_CONFLICT"
        assert rows["NEW-05"]["status"] == "NEW_CURRENT_SKU"
        assert rows["REM-04"]["status"] == "MISSING_CURRENT_SKU"
        assert payload["safeguards"]["sourceRecordsVerified"] is False
        assert payload["safeguards"]["businessRevenueVerified"] is False
        canonical = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        assert wrapper["fingerprint"]["sha256"] == hashlib.sha256(
            canonical.encode("utf-8")).hexdigest()

        # Changing date immediately invalidates the previously computed
        # report; the user must recalculate before downloading again.
        page.locator("#reconcile-date").fill(
            (datetime.now(timezone.utc).date() + timedelta(days=1)).isoformat()
        )
        expect(page.locator("#reconcile-export")).to_be_disabled()
        expect(page.locator("#reconcile-results")).to_be_hidden()
        expect(page.locator("#reconcile-state")).to_contain_text("Inputs changed")
        # A changed source file also invalidates the previous export.
        upload(page, "#reconcile-ledger", movement.replace(",4,1,-1,3", ",5,1,-1,3"))
        expect(page.locator("#reconcile-export")).to_be_disabled()
        expect(page.locator("#reconcile-results")).to_be_hidden()

        dims = page.evaluate(
            "() => ({width:innerWidth,scroll:document.documentElement.scrollWidth})"
        )
        assert dims["scroll"] <= dims["width"] + 2, dims
        assert not off_origin, off_origin
        assert not page_errors, page_errors
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
    print("DEVELOPER_LOCAL_RECONCILIATION_PASS")
    print("Snapshot stock arithmetic, sales conflict, missing SKU, SHA-256 and invalidation checked.")
    print("Synthetic, loopback only. NOT genuine source provenance, CI, AppSec or production approval.")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"RECONCILIATION_BLOCKED: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2) from None
