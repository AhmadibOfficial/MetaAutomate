#!/usr/bin/env python3
"""MetaAutomate global business experience: real Chromium desktop/mobile acceptance.

No cloud deployment, backend, tokens or API calls. Every request must target
the local static HTTP test server.
"""
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
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
        # Official social presence: exact addresses, secure external-link behavior.
        expected_socials = {
            "YouTube": "https://youtube.com/@MetaAutomate",
            "LinkedIn": "https://www.linkedin.com/company/meta-automate",
            "Instagram": "https://instagram.com/meta_automate",
            "X / Twitter": "https://twitter.com/MetaAutomate",
            "Facebook": "https://facebook.com/MetaAutomate",
            "TikTok": "https://tiktok.com/@metaautomate",
            "WhatsApp Channel": "https://whatsapp.com/channel/0029VbDSQMdBqbr1vqRyYR2U",
            "Telegram": "https://t.me/Meta_Automate",
        }
        expect(page.locator(".social-card")).to_have_count(8)
        for label, url in expected_socials.items():
            card = page.get_by_role("link", name=f"Visit MetaAutomate on {label} — opens in a new tab")
            expect(card).to_have_attribute("href", url)
            expect(card).to_have_attribute("target", "_blank")
            expect(card).to_have_attribute("rel", "noopener noreferrer")
        expect(page.locator(".footer-social-link")).to_have_count(8)
        for page_path in ("/services/", "/company/", "/engage/"):
            page.goto(BASE + page_path, wait_until="networkidle")
            footer_links=page.locator(".footer-social-link")
            expect(footer_links).to_have_count(8)
            assert sorted(footer_links.evaluate_all("(links)=>links.map(link=>link.href)")) == sorted(expected_socials.values())
            contact = page.locator(".footer-contact-email")
            expect(contact).to_have_count(1)
            expect(contact).to_contain_text("metaautomating@gmail.com")
            expect(contact).to_have_attribute(
                "href", "mailto:metaautomating@gmail.com?subject=MetaAutomate%20%7C%20Business%20inquiry"
            )

        page.goto(BASE + "/", wait_until="networkidle")
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
        # The owner-provided address opens a draft, not an automatic submission.
        direct_email = page.locator(".brief-direct-contact a")
        expect(direct_email).to_have_attribute(
            "href", "mailto:metaautomating@gmail.com?subject=MetaAutomate%20%7C%20Business%20inquiry"
        )
        draft_link = page.locator("#brief-email")
        expect(draft_link).to_be_visible()
        href = draft_link.get_attribute("href")
        assert href.startswith("mailto:metaautomating@gmail.com?")
        assert len(href) <= 1850, len(href)
        parts = urlsplit(href)
        assert parts.path == "metaautomating@gmail.com"
        draft = parse_qs(parts.query)
        assert draft["subject"] == ["MetaAutomate | Project discovery inquiry"]
        assert "Cybersecurity & Quality" in draft["body"][0]
        assert "We need an authorized API security review" in draft["body"][0]
        assert chr(10) in draft["body"][0]
        assert (chr(92) + "n") not in draft["body"][0], "Use real newlines in the draft"
        expect(page.locator("#brief-email-note")).to_contain_text("Nothing has been sent")

        # Large briefs must be exportable in full and email drafts remain bounded.
        page.locator("#brief-problem").fill("A" * 1700)
        page.locator("#brief-outcome").fill("B" * 1150)
        page.locator("#brief-form button[type=submit]").click()
        long_href = draft_link.get_attribute("href")
        assert len(long_href) <= 1850, len(long_href)
        long_body = parse_qs(urlsplit(long_href).query)["body"][0]
        assert "Remaining details omitted" in long_body
        assert "A" * 1700 in page.locator("#brief-output").inner_text()
        expect(page.locator("#brief-email-note")).to_contain_text("abbreviated")
        # Restore a short brief before capturing the normal project inquiry UI.
        page.locator("#brief-problem").fill(
            "We need an authorized API security review for our business application."
        )
        page.locator("#brief-outcome").fill(
            "A prioritized assessment report that identifies material risk."
        )
        page.locator("#brief-form button[type=submit]").click()
        expect(page.locator("#brief-email-note")).to_contain_text("Nothing has been sent")

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
                expect(mpage.locator(".footer-contact-email")).to_have_count(1)
                social_links = mpage.locator(".footer-social-link")
                expect(social_links).to_have_count(8)
                assert sorted(social_links.evaluate_all(
                    "(links) => links.map(link => link.href)"
                )) == sorted(expected_socials.values())
                if path == "/":
                    expect(mpage.locator(".social-card")).to_have_count(8)


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
