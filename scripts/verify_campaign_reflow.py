#!/usr/bin/env python3
"""P2-060d: local, synthetic Chromium responsive-reflow acceptance.

Narrow CSS viewport tests are an approximation of layout at 200% zoom;
they do not certify actual browser zoom, 400% WCAG reflow or readability.
Loopback-only, read-only server; no screenshot storage, external services.
"""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_campaign_workbench_browser import (
    CSV, ensure_playwright_driver, launch_full_chromium, same_origin, serve_local
)

# 1280 physical at 200% -> 640 CSS px; 640 physical at 200% -> 320 CSS px.
# 256px is an additional severe narrow-view stress case, not WCAG certification.
WIDTHS = (1280, 640, 390, 320, 256)
CRITICAL = ("#campaign-file", "#campaign-import button[type=submit]",
            "#campaign-create", "#campaign-post", "#campaign-video-brief",
            "#campaign-png", "#campaign-confirm", "#campaign-authorize",
            "#campaign-impressions", "#campaign-metric-form button[type=submit]",
            "#campaign-evidence")


def inspect_geometry(page, width: int, selectors: tuple[str, ...]) -> None:
    data = page.evaluate("""selectors => {
      const w = document.documentElement.clientWidth;
      const overflow = document.documentElement.scrollWidth;
      const results = selectors.map(selector => {
        const el = document.querySelector(selector);
        if (!el) return {selector, missing:true};
        const box = el.getBoundingClientRect();
        const cs = getComputedStyle(el);
        return {
          selector, hidden: cs.display === 'none' || cs.visibility === 'hidden',
          left:box.left, right:box.right, width:box.width,
          height:box.height, scrollWidth:el.scrollWidth,
          clientWidth:el.clientWidth,
        };
      });
      return {w, overflow, results};
    }""", list(selectors))
    assert data["w"] == width, (width, data)
    assert data["overflow"] <= data["w"] + 2, data
    for row in data["results"]:
        assert not row.get("missing"), row
        assert not row["hidden"], row
        assert row["width"] >= 20 and row["height"] >= 20, row
        assert row["left"] >= -2 and row["right"] <= width + 2, row
        # Native file controls and textarea can internally scroll. Check the
        # actual bounding box rather than banning all internal scrollWidths.


def exercise(browser, base: str, width: int) -> None:
    from playwright.sync_api import expect

    context = browser.new_context(
        viewport={"width": width, "height": 900},
        accept_downloads=False, service_workers="block", reduced_motion="reduce"
    )
    external = []
    errors = []
    try:
        def restrict(route):
            if same_origin(route.request.url, base):
                route.continue_()
            else:
                external.append(route.request.url)
                route.abort_()
        context.route("**/*", restrict)
        page = context.new_page()
        page.on("pageerror", lambda err: errors.append(str(err)))
        response = page.goto(base + "/campaigns/", wait_until="networkidle")
        assert response and response.status == 200
        page.locator("#campaign-file").set_input_files({
            "name": "synthetic-stock.csv", "mimeType": "text/csv",
            "buffer": CSV.encode("utf-8")
        })
        page.locator("#campaign-import button[type=submit]").focus()
        page.keyboard.press("Enter")
        expect(page.locator("#results-title")).to_be_focused()
        page.locator("#campaign-brand").fill("Synthetic MetaAutomate Shop")
        page.locator("#campaign-create").focus()
        page.keyboard.press("Enter")
        expect(page.locator("#project-title")).to_be_focused()
        inspect_geometry(page, width, (
            "#campaign-file", "#campaign-import button[type=submit]",
            "#campaign-create", "#campaign-post", "#campaign-video-brief",
            "#campaign-png", "#campaign-confirm", "#campaign-authorize",
            "#campaign-impressions", "#campaign-metric-form button[type=submit]"
        ))
        # Every critical workflow control can be scrolled into view and is
        # operable without causing horizontal document overflow.
        page.locator("#campaign-confirm").focus()
        page.keyboard.press("Space")
        page.locator("#campaign-authorize").focus()
        page.keyboard.press("Enter")
        expect(page.locator("#campaign-copy")).to_be_enabled()
        page.locator("#campaign-post").fill("Edited synthetic draft; approval required.")
        expect(page.locator("#campaign-copy")).to_be_disabled()
        page.locator("#campaign-confirm").focus()
        page.keyboard.press("Space")
        page.locator("#campaign-authorize").focus()
        page.keyboard.press("Enter")
        expect(page.locator("#campaign-copy")).to_be_enabled()
        for selector, value in (
            ("#campaign-impressions", "100"), ("#campaign-clicks", "20"),
            ("#campaign-orders", "3"),
            ("#campaign-metric-source", "Synthetic only — not verified"),
        ):
            page.locator(selector).fill(value)
        page.locator("#campaign-metric-form button[type=submit]").focus()
        page.keyboard.press("Enter")
        expect(page.locator("#campaign-metrics-result")).to_contain_text(
            "Self-reported")
        inspect_geometry(page, width, CRITICAL)
        assert page.locator("#campaign-evidence").is_enabled()
        assert not errors, errors
        assert not external, external
    finally:
        context.close()


def run() -> None:
    ensure_playwright_driver()
    with serve_local() as base:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = launch_full_chromium(pw)
            try:
                for width in WIDTHS:
                    exercise(browser, base, width)
            finally:
                browser.close()
    print("DEVELOPER_LOCAL_REFLOW_AUTOMATION_PASS")
    print("Narrow CSS viewports checked: " + ", ".join(map(str, WIDTHS)))
    print("Synthetic-only, no off-origin requests, external publishing or files.")
    print("NOT independent zoom, visual pixels, screen-reader or WCAG acceptance.")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"REFLOW_AUTOMATION_BLOCKED: {type(exc).__name__}: {exc}",
              file=sys.stderr)
        raise SystemExit(2) from None
