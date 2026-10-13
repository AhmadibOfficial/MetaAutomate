#!/usr/bin/env python3
"""MetaAutomate global business experience: real Chromium desktop/mobile acceptance.

No cloud deployment, backend, tokens or API calls. Every request must target
the local static HTTP test server.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = "http://127.0.0.1:18080"
ART = Path("artifacts")
ART.mkdir(exist_ok=True)


def assert_no_horizontal_overflow(page, name):
    dimensions = page.evaluate(
        "() => ({scroll:document.documentElement.scrollWidth, width:innerWidth})"
    )
    assert dimensions["scroll"] <= dimensions["width"]+1, (name, dimensions)


def inspect_asset(page):
    expect(page.locator(".brand img").first).to_be_visible()
    assert page.locator(".brand img").first.evaluate(
        "(img) => img.complete && img.naturalWidth > 0"
    ), "Official MetaAutomate mark unavailable"


def main():
    bad_requests = []
    page_errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        desktop = browser.new_context(
            viewport={"width": 1440, "height": 940},
            device_scale_factor=1, reduced_motion="reduce",
            accept_downloads=True,
        )
        page = desktop.new_page()
        page.on("request", lambda request: (
            bad_requests.append(request.url)
            if not request.url.startswith(BASE) else None
        ))
        page.on("pageerror", lambda error: page_errors.append(str(error)))

        # Home: flagship brand and intelligent-system interaction.
        response = page.goto(BASE+"/", wait_until="networkidle")
        assert response.status == 200
        expect(page).to_have_title("MetaAutomate — Engineering What's Next")
        expect(page.get_by_role("heading", level=1)).to_contain_text("Build beyond")
        expect(page.locator(".service-tile")).to_have_count(6)
        expect(page.locator(".industry-card")).to_have_count(4)
        expect(page.locator(".proof-feature")).to_have_count(4)
        expect(page.locator(".statement-section")).to_contain_text("Always HALAL")
        inspect_asset(page)
        tabs=page.get_by_role("tab")
        expect(tabs).to_have_count(5)
        expect(page.locator("#operation-title")).to_have_text("Start with the objective.")
        tabs.nth(2).click()
        expect(page.locator("#operation-title")).to_have_text("Make the solution real.")
        expect(page.locator("#tab-create")).to_have_attribute("aria-selected", "true")
        tabs.nth(2).press("ArrowRight")
        expect(page.locator("#operation-title")).to_have_text("Prove what the system does.")
        expect(page.locator("#tab-verify")).to_be_focused()
        assert_no_horizontal_overflow(page, "desktop home")
        page.goto(BASE+"/", wait_until="networkidle")
        page.screenshot(path=str(ART/"metaautomate-global-home-desktop.png"), full_page=True)

        # Service catalog is addressable and routes to a real on-device brief.
        services=page.goto(BASE+"/services/", wait_until="networkidle")
        assert services.status == 200
        expect(page.locator(".discipline")).to_have_count(6)
        expect(page.locator("#software")).to_contain_text("Software &")
        inspect_asset(page)
        assert_no_horizontal_overflow(page, "desktop services")
        page.screenshot(path=str(ART/"metaautomate-global-services-desktop.png"), full_page=True)
        page.locator("#software .discipline-action").click()
        assert "/engage/" in page.url
        expect(page.locator("#brief-service")).to_have_value("Software & Digital Products")

        # Brand values and roadmap are presented without claiming shipped features.
        page.goto(BASE+"/company/", wait_until="networkidle")
        expect(page.locator(".purpose-panel")).to_have_count(2)
        expect(page.locator(".value-principles article")).to_have_count(5)
        expect(page.locator(".principle-halal")).to_contain_text("Always HALAL")
        expect(page.locator(".brand-meaning div")).to_have_count(5)
        expect(page.locator(".roadmap-entry")).to_have_count(4)
        assert_no_horizontal_overflow(page, "desktop company")
        page.screenshot(path=str(ART/"metaautomate-global-company-desktop.png"), full_page=True)

        # Project brief: form validation, no network POST, copy-safe text and download.
        page.goto(BASE+"/engage/", wait_until="networkidle")
        page.locator("#brief-form button[type=submit]").click()
        expect(page.locator("#brief-error")).to_be_visible()
        expect(page.locator("#brief-result")).to_be_hidden()
        page.locator("#brief-service").select_option(label="Cybersecurity & Quality")
        page.locator("#brief-stage").select_option(label="Existing product or system")
        page.locator("#brief-problem").fill(
            "We need an authorized API security review for our business application."
        )
        page.locator("#brief-outcome").fill(
            "A prioritized assessment report that identifies material risk."
        )
        page.locator("#brief-constraints").fill(
            "Only test our authorized staging environment. No third-party assets."
        )
        page.locator("#brief-form button[type=submit]").click()
        expect(page.locator("#brief-result")).to_be_visible()
        expect(page.locator("#brief-output")).to_contain_text(
            "Cybersecurity & Quality"
        )
        expect(page.locator("#brief-output")).to_contain_text(
            "No information was transmitted"
        )
        page.evaluate("() => { if (document.activeElement) document.activeElement.blur(); window.scrollTo(0, 0); }")
        page.wait_for_timeout(180)
        page.screenshot(path=str(ART/"metaautomate-global-project-brief.png"), full_page=True)
        with page.expect_download() as download:
            page.locator("#brief-download").click()
        assert download.value.suggested_filename == "metaautomate-project-brief.txt"
        page.locator("#brief-form button[type=reset]").click()
        expect(page.locator("#brief-result")).to_be_hidden()
        assert_no_horizontal_overflow(page, "desktop brief")

        # Mobile: navigation and all four pages, 390px and narrower 360px.
        for width in (390, 360):
            mobile = browser.new_context(
                viewport={"width": width,"height": 844},
                device_scale_factor=1, is_mobile=True, has_touch=True,
                reduced_motion="reduce",
            )
            mpage=mobile.new_page()
            mpage.on("request", lambda request: (
                bad_requests.append(request.url)
                if not request.url.startswith(BASE) else None
            ))
            mpage.on("pageerror", lambda error: page_errors.append(str(error)))
            for path in ("/","/services/","/company/","/engage/"):
                mpage.goto(BASE+path,wait_until="networkidle")
                inspect_asset(mpage)
                assert_no_horizontal_overflow(mpage, f"mobile {width} {path}")
            mpage.goto(BASE+"/",wait_until="networkidle")
            menu=mpage.locator("#menu-button")
            expect(mpage.locator("#site-navigation")).to_be_hidden()
            menu.click()
            expect(menu).to_have_attribute("aria-expanded","true")
            expect(mpage.locator("#site-navigation")).to_be_visible()
            mpage.get_by_role("link", name="Services", exact=True).first.click()
            expect(mpage).to_have_url(BASE+"/services/")
            expect(menu).to_have_attribute("aria-expanded","false")
            expect(mpage.locator("#site-navigation")).to_be_hidden()
            mpage.goto(BASE+"/",wait_until="networkidle")
            if width==390:
                mpage.screenshot(path=str(ART/"metaautomate-global-home-mobile.png"),full_page=True)
            mobile.close()

        assert not bad_requests, f"Unexpected third-party HTTP requests: {bad_requests}"
        assert not page_errors, f"Browser JavaScript errors: {page_errors}"
        browser.close()
    print("PASS: global homepage, 6 services, 4 sectors, brand, keyboard tabs, project brief, download, desktop/mobile, no external requests")


if __name__=="__main__":
    main()
