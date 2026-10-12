#!/usr/bin/env python3
"""Browser acceptance test for the public-facing MetaAutomate static business site.

No cloud deployment, credentials, database, backend APIs or external network
calls. Tested with a localhost HTTP server in GitHub Actions.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = "http://127.0.0.1:18080"
ART = Path("artifacts")
ART.mkdir(exist_ok=True)


def assert_no_horizontal_overflow(page, label):
    dimensions = page.evaluate(
        "() => ({scroll:document.documentElement.scrollWidth, width:innerWidth})"
    )
    assert dimensions["scroll"] <= dimensions["width"] + 1, (label, dimensions)


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        desktop = browser.new_context(
            viewport={"width": 1440, "height": 960}, device_scale_factor=1,
            reduced_motion="reduce",
        )
        page = desktop.new_page()
        bad_requests = []

        def audit_request(request):
            if not request.url.startswith(BASE):
                bad_requests.append(request.url)
        page.on("request", audit_request)
        response = page.goto(BASE + "/", wait_until="networkidle")
        assert response.status == 200
        expect(page).to_have_title("MetaAutomate — Turn Your Vision Into Reality")
        expect(page.locator("h1")).to_contain_text("Turn your vision")
        expect(page.locator("#platform")).to_be_visible()
        expect(page.locator(".capability-card:visible")).to_have_count(9)
        expect(page.locator(".mission-card")).to_have_count(2)
        expect(page.locator(".sector-card")).to_have_count(4)
        expect(page.locator(".roadmap-card")).to_have_count(4)
        expect(page.locator(".principle-gold")).to_contain_text("Always HALAL")
        assert page.locator(".site-brand img").first.evaluate(
            "(img) => img.complete && img.naturalWidth > 0"
        ), "Official MetaAutomate logo did not load"

        page.locator("#platform").scroll_into_view_if_needed()
        assert_no_horizontal_overflow(page, "desktop")
        page.locator(".filter-button[data-filter=business]").click()
        expect(page.locator(".capability-card:visible")).to_have_count(4)
        expect(page.locator(".filter-button[data-filter=business]")).to_have_attribute(
            "aria-pressed", "true"
        )
        page.locator(".filter-button[data-filter=impact]").click()
        expect(page.locator(".capability-card:visible")).to_have_count(1)
        expect(page.locator(".capability-card:visible")).to_contain_text("Islamic")
        page.locator(".filter-button[data-filter=all]").click()
        expect(page.locator(".capability-card:visible")).to_have_count(9)
        page.goto(BASE + "/", wait_until="networkidle")
        page.screenshot(path=str(ART / "metaautomate-business-desktop.png"), full_page=True)
        assert not bad_requests, f"Unexpected external requests: {bad_requests}"

        mobile = browser.new_context(
            viewport={"width": 390, "height": 844}, device_scale_factor=1,
            is_mobile=True, has_touch=True, reduced_motion="reduce",
        )
        mpage = mobile.new_page()
        mpage.goto(BASE + "/", wait_until="networkidle")
        assert_no_horizontal_overflow(mpage, "mobile")
        nav = mpage.locator("#primary-navigation")
        expect(nav).to_be_hidden()
        toggle = mpage.locator("#menu-toggle")
        toggle.click()
        expect(toggle).to_have_attribute("aria-expanded", "true")
        expect(nav).to_be_visible()
        nav.get_by_role("link", name="Our mission").click()
        expect(toggle).to_have_attribute("aria-expanded", "false")
        expect(nav).to_be_hidden()
        expect(mpage).to_have_url(BASE + "/#mission")
        mpage.goto(BASE + "/", wait_until="networkidle")
        mpage.screenshot(path=str(ART / "metaautomate-business-mobile.png"), full_page=True)
        assert_no_horizontal_overflow(mpage, "mobile-fullpage")
        browser.close()
    print("PASS: desktop/mobile layout, official mark, nav, capability filters, content and no external requests")


if __name__ == "__main__":
    main()
