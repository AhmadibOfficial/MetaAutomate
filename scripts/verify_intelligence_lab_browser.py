#!/usr/bin/env python3
"""Source-only browser acceptance: 12 module views, simulation, tasks, mobile, screenshots.

Uses an in-process local static server and refuses third-party requests.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:18181"
ART = ROOT / "artifacts/validation"


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    handler = partial(SimpleHTTPRequestHandler, directory=str(ROOT / "apps/site"))
    server = ThreadingHTTPServer(("127.0.0.1", 18181), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    issues = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            for width in (1440, 390, 360):
                ctx = browser.new_context(viewport={"width": width, "height": 900},
                                          reduced_motion="reduce", device_scale_factor=1)
                page = ctx.new_page()
                page.on("pageerror", lambda err: issues.append(str(err)))
                page.on("request", lambda req: issues.append("External request: " + req.url)
                        if not req.url.startswith(BASE + "/") else None)
                response = page.goto(BASE + "/intelligence-lab/", wait_until="networkidle")
                assert response and response.status == 200
                expect(page).to_have_title("Business Intelligence Lab — MetaAutomate (Source Preview)")
                expect(page.locator(".module-nav")).to_have_count(12)
                expect(page.locator(".engine")).to_have_count(5)
                expect(page.locator(".kpi").nth(0)).to_contain_text("25,000")
                expect(page.locator(".kpi").nth(2)).to_contain_text("12,300")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), width
                if width == 1440:
                    page.screenshot(path=str(ART / "intelligence-lab-desktop.png"), full_page=True)
                else:
                    page.screenshot(path=str(ART / f"intelligence-lab-mobile-{width}.png"), full_page=True)
                for module in ("objective","value","decision","growth","crm","inventory",
                               "finance","marketing","commerce","workflow","operations","executive"):
                    button = page.locator('.module-nav[data-module="' + module + '"]')
                    button.click()
                    expect(button).to_have_attribute("aria-pressed", "true")
                    expect(page.locator("#module-content")).not_to_be_empty()
                page.locator('[data-module="decision"]').click()
                before = page.locator("#module-content").inner_text()
                page.locator("#price").fill("1000")
                page.locator("#price").dispatch_event("change")
                after = page.locator("#module-content").inner_text()
                assert after != before and "10%" in after
                expect(page.locator("#module-content")).to_contain_text("not demand predictions")
                page.locator('[data-module="workflow"]').click()
                page.locator('[data-add="TARGET_GAP"]').click()
                expect(page.locator("[data-step]")).to_have_count(1)
                for text in ("Mark reviewed","Start work","Mark completed"):
                    btn = page.locator("[data-step]")
                    expect(btn).to_have_text(text)
                    btn.click()
                expect(page.locator("#module-content")).to_contain_text("COMPLETED")
                page.locator("#goal").select_option("RETENTION")
                page.locator("#business").select_option("bespoke_demo")
                expect(page.locator(".kpi").nth(0)).to_contain_text("35,000")
                expect(page.locator(".kpi").nth(2)).to_contain_text("4,700")
                page.locator('[data-module="growth"]').click()
                expect(page.locator("#module-content")).to_contain_text("Suppressed proposals")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), width
                page.locator('[data-module="executive"]').focus()
                assert page.locator('[data-module="executive"]').evaluate("(e)=>document.activeElement===e")
                ctx.close()
            browser.close()
        assert not issues, issues
    finally:
        server.shutdown()
        server.server_close()
    print("PASS: 12 modules, five engines, simulated decisions, tasks, keyboard and 3 viewports")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
