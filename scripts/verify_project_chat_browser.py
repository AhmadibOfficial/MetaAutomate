#!/usr/bin/env python3
"""P2-04w desktop/mobile chat project discovery, no model or network calls."""
from pathlib import Path
import re

from playwright.sync_api import expect, sync_playwright

BASE = "http://127.0.0.1:18080"
ART = Path("artifacts/validation")
ART.mkdir(parents=True, exist_ok=True)

def no_overflow(page):
    dimensions = page.evaluate(
        "() => ({width: innerWidth, content: document.documentElement.scrollWidth})")
    assert dimensions["content"] <= dimensions["width"] + 1, dimensions

def main():
    external_requests = []
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for name, width, height in (
            ("desktop", 1440, 960),
            ("mobile", 390, 844),
            ("small-mobile", 360, 780),
        ):
            ctx = browser.new_context(
                viewport={"width": width, "height": height},
                reduced_motion="reduce",accept_downloads=True
            )
            page = ctx.new_page()
            page.on("request", lambda req: external_requests.append(req.url)
                    if not req.url.startswith(BASE) else None)
            page.on("pageerror", lambda err: errors.append(str(err)))
            response = page.goto(BASE+"/engage/",wait_until="networkidle")
            assert response.status == 200
            expect(page).to_have_title("Start a Project — MetaAutomate")
            expect(page.get_by_role("heading",
                                    name="What would you like to build today?")).to_be_visible()
            expect(page.locator("#project-chat-messages")).to_be_visible()
            expect(page.locator("#project-chat-summary")).to_be_hidden()
            expect(page.locator("#project-chat-progress")).to_contain_text("Step 1 of 5")
            expect(page.locator("#brief-form")).to_be_hidden()
            # User remains in control: example only fills composer, no auto submit.
            page.locator("#project-chat-suggestions [data-project-template=creative]").click()
            expect(page.locator("#project-chat-input")).to_have_value(
                re.compile("original visuals and narrated video"))
            expect(page.locator("#project-chat-progress")).to_contain_text("Step 1")
            page.locator("#project-chat-send").click()
            expect(page.locator("#project-chat-progress")).to_contain_text("Step 2 of 5")
            expect(page.locator("#project-chat-messages")).to_contain_text(
                "What would success look like")
            # Edit an answer; do not lose script safety or reply ordering.
            page.locator("#project-chat-edit").click()
            expect(page.locator("#project-chat-progress")).to_contain_text("Step 1 of 5")
            first = "Plan original educational videos about business workflow " \
                    "improvements with <img src=x onerror=alert(1)> as literal text."
            page.locator("#project-chat-input").fill(first)
            page.locator("#project-chat-input").press("Enter")
            expect(page.locator("#project-chat-progress")).to_contain_text("Step 2 of 5")
            expect(page.locator("#project-chat-messages")).to_contain_text("<img src=x")
            assert page.locator("#project-chat-messages img").count() == 0
            for content in (
                "A clear user journey and a verified sample, with no false income claims.",
                "Small business owners and teams using mobile devices.",
                "A practical first prototype within three months.",
                "Only properly licensed media and reviewed project content.",
            ):
                page.locator("#project-chat-input").fill(content)
                page.locator("#project-chat-send").click()
            expect(page.locator("#project-chat-summary")).to_be_visible()
            expect(page.locator("#project-chat-summary-text")).to_contain_text(
                "PROJECT DISCOVERY BRIEF")
            expect(page.locator("#project-chat-summary-text")).to_contain_text(
                "Nothing was automatically transmitted")
            expect(page.locator("#project-chat-email")).to_have_attribute(
                "href",re.compile(r"^mailto:metaautomating@gmail\.com"))
            with page.expect_download() as dl:
                page.locator("#project-chat-download").click()
            download = dl.value
            assert download.suggested_filename == "metaautomate-project-discovery.txt"
            data = Path(download.path()).read_text("utf-8")
            assert "Plan original educational videos" in data
            assert "not a contract" in data
            no_overflow(page)
            page.screenshot(path=str(ART/f"start-project-chat-{name}.png"),
                            full_page=True)
            page.locator("#project-chat-new").click()
            expect(page.locator("#project-chat-summary")).to_be_hidden()
            expect(page.locator("#project-chat-progress")).to_contain_text("Step 1 of 5")
            # Old deep link and service pre-selection remain accessible.
            page.goto(BASE+"/engage/?service=Product%20Design%20%26%20Experience#brief-form")
            expect(page.locator("#brief-form")).to_be_visible()
            expect(page.locator("#brief-service")).to_have_value(
                "Product Design & Experience")
            ctx.close()
        browser.close()
    assert not errors,errors
    assert not external_requests,external_requests
    print("PASS: chat-first desktop/mobile/360px, editable state, safe DOM,"
          " local download, deep link, browser-only privacy and no JS errors.")

if __name__=="__main__":
    main()
