#!/usr/bin/env python3
"""P2-03p offline WhatsApp lead lab: browser, responsive and policy refusal checks."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:18282"
ART = ROOT / "artifacts/validation"


def main() -> int:
    ART.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(
        ("127.0.0.1", 18282),
        partial(SimpleHTTPRequestHandler, directory=str(ROOT / "apps/site")),
    )
    Thread(target=server.serve_forever, daemon=True).start()
    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for width in (1440, 390, 360):
                ctx = browser.new_context(
                    viewport={"width": width, "height": 900},
                    reduced_motion="reduce", device_scale_factor=1,
                )
                page = ctx.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("request", lambda r: errors.append("External URL: " + r.url)
                        if not r.url.startswith(BASE + "/") else None)
                resp = page.goto(BASE + "/intelligence-lab/whatsapp/", wait_until="networkidle")
                assert resp and resp.status == 200
                expect(page).to_have_title(
                    "WhatsApp Lead Pipeline — MetaAutomate | Offline Preview"
                )
                expect(page.locator(".wa-stage")).to_have_count(4)
                expect(page.locator("#lead-select option")).to_have_count(3)
                expect(page.locator("#decision-status")).to_have_text("Service reply review")
                expect(page.locator("#policy-ledger")).to_contain_text("Messages sent")
                expect(page.locator("#policy-ledger")).to_contain_text("Not verified")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), width
                if width == 1440:
                    page.screenshot(path=str(ART / "whatsapp-leads-desktop.png"), full_page=True)
                else:
                    page.screenshot(path=str(ART / f"whatsapp-leads-mobile-{width}.png"), full_page=True)
                # Opt-out always takes priority, even inside 24 hours.
                page.locator("#lead-select").select_option("SIM-LEAD-EDU-02")
                expect(page.locator("#decision-status")).to_have_text("Communication suppressed")
                # Outside service window without marketing opt-in: no follow-up.
                page.locator("#lead-select").select_option("SIM-LEAD-EDU-03")
                expect(page.locator("#decision-status")).to_contain_text("Hold")
                # New business and a template-path review, never automatic delivery.
                page.locator("#business-select").select_option("bespoke_demo")
                expect(page.locator("#lead-select option")).to_have_count(2)
                expect(page.locator("#decision-status")).to_have_text("Approved-template review")
                page.locator("#lead-select").select_option("SIM-LEAD-FAS-02")
                expect(page.locator("#decision-status")).to_have_text("No conversation yet")
                # Qualification changes are purely local; inbound remains absent.
                page.locator("#budget_band").select_option("MEDIUM")
                page.locator("#timeline").select_option("SOON")
                expect(page.locator("#decision-status")).to_have_text("No conversation yet")
                page.locator("#restore").click()
                expect(page.locator("#budget_band")).to_have_value("UNKNOWN")
                page.locator("#restore").focus()
                expect(page.locator("#restore")).to_be_focused()
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), width
                ctx.close()
            # Visible route from the unified CRM module
            ctx = browser.new_context(viewport={"width": 1440, "height": 900})
            page = ctx.new_page()
            page.goto(BASE + "/intelligence-lab/", wait_until="networkidle")
            page.locator('[data-module="crm"]').click()
            expect(page.locator('a[href="/intelligence-lab/whatsapp/"]')).to_be_visible()
            page.locator('[data-module="growth"]').click()
            expect(page.locator('a[href="/intelligence-lab/whatsapp/"]')).to_be_visible()
            ctx.close()
            browser.close()
        assert not errors, errors
    finally:
        server.shutdown()
        server.server_close()
    print("PASS: 4-stage WhatsApp policy lab, opt-outs, consent, 24h, 3 layouts, CRM/Growth link")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
