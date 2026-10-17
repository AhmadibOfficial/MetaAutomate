#!/usr/bin/env python3
"""P2-04z: in-browser user-approved handoff; no backend or AI model."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE="http://127.0.0.1:18080"
ART=Path("artifacts/validation")
ART.mkdir(parents=True,exist_ok=True)

def main():
    errors=[]
    external=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        for name,width in [("desktop",1440),("mobile",390)]:
            context=browser.new_context(viewport={"width":width,"height":880},
                                        reduced_motion="reduce")
            page=context.new_page()
            page.on("pageerror",lambda exc: errors.append(str(exc)))
            page.on("request",lambda req: external.append(req.url)
                    if not req.url.startswith(BASE) else None)
            page.goto(BASE+"/engage/",wait_until="networkidle")
            steps=[
                "Create an original 60 second educational video about better business inventory management.",
                "Teach local shop owners how to reduce daily stock recording mistakes.",
                "Small retail business owners using mobile phones.",
                "A prototype in three months.",
                "Original visuals, reviewed voice rights, and readable subtitles."
            ]
            for message in steps:
                page.locator("#project-chat-input").fill(message)
                page.locator("#project-chat-send").click()
            expect(page.locator("#project-chat-summary")).to_be_visible()
            page.locator("#project-chat-creative-format").select_option("video")
            page.locator("#project-chat-creative").click()
            page.wait_for_url("**/creative/#creative-form")
            expect(page.locator("#creative-import-notice")).to_be_visible()
            expect(page.locator("#creative-goal")).to_have_value(
                __import__("re").compile("educational video"))
            expect(page.locator("#creative-audience")).to_have_value(
                "Small retail business owners using mobile phones.")
            expect(page.locator("#creative-kind")).to_have_value("video")
            expect(page.locator("#creative-rights")).to_have_value("unknown")
            expect(page.locator("#creative-likeness")).to_have_value("unknown")
            # The one-time handoff must have been deleted immediately.
            assert page.evaluate(
                "() => sessionStorage.getItem('mat:creative:handoff:v1')") is None
            page.reload(wait_until="networkidle")
            expect(page.locator("#creative-import-notice")).to_be_hidden()
            expect(page.locator("#creative-goal")).to_have_value("")
            width_data=page.evaluate(
                "() => [window.innerWidth,document.documentElement.scrollWidth]")
            assert width_data[1]<=width_data[0]+1,width_data
            page.screenshot(path=str(ART/f"creative-handoff-{name}.png"),
                            full_page=True)
            context.close()
        browser.close()
    assert not errors,errors
    assert not external,external
    print("PASS: explicit conversation handoff, once-only browser tab storage,"
          " rights/consent HOLD, no external requests, desktop and mobile.")

if __name__=="__main__":
    main()
