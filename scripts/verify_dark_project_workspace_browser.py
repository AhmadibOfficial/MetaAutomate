#!/usr/bin/env python3
"""P2-057: browser acceptance of blue Chat/Work workspace and hideable navigation.

No external model download: check opt-in panel and consent only.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

BASE="http://127.0.0.1:18080"
OUT=Path("artifacts/validation")
OUT.mkdir(parents=True,exist_ok=True)

def main():
    errors=[]
    external=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        for name,width,height in (
            ("desktop",1440,960),
            ("tablet",860,900),
            ("mobile",390,844),
            ("small-mobile",360,780),
        ):
            context=browser.new_context(
                viewport={"width":width,"height":height},
                reduced_motion="reduce")
            page=context.new_page()
            page.on("pageerror",lambda error:errors.append(str(error)))
            page.on("request",lambda req:external.append(req.url)
                    if not req.url.startswith(BASE) else None)
            result=page.goto(BASE+"/engage/",wait_until="networkidle")
            assert result.status==200
            expect(page.get_by_role("heading",
                name="What would you like to build today?")).to_be_visible()
            expect(page.locator("#project-chat-messages")).to_be_visible()
            assert "gradient" in page.evaluate(
                "() => getComputedStyle(document.body).backgroundImage"
            )
            assert page.locator("#brief-form").count()==0
            assert page.locator("#project-chat-alternative").count()==0
            # Desktop and tablet both support collapse/expand via top navigation.
            if width>740:
                toggle=page.locator("#workspace-sidebar-toggle")
                expect(toggle).to_have_attribute("aria-expanded","true")
                toggle.click()
                expect(page.locator("#project-workspace-side")).to_be_hidden()
                expect(toggle).to_have_attribute("aria-expanded","false")
                toggle.click()
                expect(page.locator("#project-workspace-side")).to_be_visible()
                expect(toggle).to_have_attribute("aria-expanded","true")
            assert not external,"No external request permitted on page load"
            page.locator("#workspace-mode-work").click()
            expect(page.locator("#workspace-work-panel")).to_be_visible()
            expect(page.locator("#project-chat-messages")).to_be_hidden()
            expect(page.locator("#workspace-mode-work")).to_have_attribute(
                "aria-pressed","true")
            expect(page.get_by_role("heading",
                name="What would you like to create today?")).to_be_visible()
            assert page.locator(
                '#workspace-work-panel a[href="/creative/#instant-design"]'
            ).count()==1
            assert page.locator(
                '#workspace-work-panel a[href="/creative/#instant-video"]'
            ).count()==1
            page.locator("#workspace-work-brief").click()
            expect(page.locator("#workspace-mode-chat")).to_have_attribute(
                "aria-pressed","true")
            expect(page.locator("#project-chat-messages")).to_be_visible()
            page.locator("#project-chat-suggestions [data-project-template=automation]").click()
            expect(page.locator("#project-chat-input")).to_have_value(
                __import__("re").compile("repetitive business"))
            # The predefined intake is still fully usable.
            page.locator("#project-chat-send").click()
            expect(page.locator("#project-chat-progress")).to_contain_text("Step 2 of 5")
            page.locator("#workspace-mode-work").click()
            page.locator("#workspace-work-ai").click()
            expect(page.locator("#project-ai-experience")).to_be_visible()
            expect(page.locator("#project-ai-consent")).to_be_visible()
            assert not external,"Opening a disclosure must not download a model"
            page.locator("#project-ai-close").click()
            expect(page.locator("#project-chat-messages")).to_be_visible()
            if width<741:
                page.locator("#workspace-sidebar-toggle").click()
                expect(page.locator("#workspace-sidebar-toggle")).to_have_attribute(
                    "aria-expanded","true")
                page.locator("#workspace-search-input").fill("security")
                expect(page.locator(
                    ".project-chat-templates [data-project-template=security]"
                )).to_be_visible()
                expect(page.locator(
                    ".project-chat-templates [data-project-template=product]"
                )).to_be_hidden()
                page.keyboard.press("Escape")
                expect(page.locator("#workspace-sidebar-toggle")).to_have_attribute(
                    "aria-expanded","false")
            else:
                page.locator("#workspace-search-input").fill("automation")
                expect(page.locator(
                    ".project-chat-templates [data-project-template=automation]"
                )).to_be_visible()
                page.locator("#workspace-search-input").fill("")
            dims=page.evaluate(
                "() => ({screen:innerWidth,page:document.documentElement.scrollWidth})")
            assert dims["page"]<=dims["screen"]+1,dims
            page.screenshot(path=str(OUT/f"project-workspace-blue-{name}.png"),
                            full_page=True)
            # The existing creative tool routes remain navigable.
            image_page=page.goto(BASE+"/creative/#instant-design")
            assert image_page.status==200
            expect(page.locator("#maker-form")).to_be_visible()
            context.close()
        browser.close()
    assert not errors,errors
    assert not external,external
    print("PASS: Chat/Work modes, tools, guided intake, local AI consent, "
          "sidebar search/mobile drawer, no network and responsive viewport")

if __name__=="__main__":
    main()
