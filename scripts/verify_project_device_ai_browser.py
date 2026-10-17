#!/usr/bin/env python3
"""P2-04y: consent-first local AI UI, without fetching model weights in CI."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
BASE="http://127.0.0.1:18080"
ART=Path("artifacts/validation")
ART.mkdir(parents=True,exist_ok=True)

def main():
    invalid=[]
    page_errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        for name,width in (("desktop",1440),("mobile",390),("small-mobile",360)):
            context=browser.new_context(viewport={"width":width,"height":900},
                                        reduced_motion="reduce")
            # Deliberately emulate a device without GPU so no remote models
            # are imported: source functionality, not neural execution.
            context.add_init_script("""
                Object.defineProperty(navigator, 'gpu', {
                  configurable: true, value: undefined
                });
            """)
            page=context.new_page()
            page.on("request",lambda r: invalid.append(r.url)
                    if not r.url.startswith(BASE) else None)
            page.on("pageerror",lambda e: page_errors.append(str(e)))
            result=page.goto(BASE+"/engage/",wait_until="networkidle")
            assert result.status==200
            expect(page.locator("#project-ai-experience")).to_be_hidden()
            expect(page.locator("#project-chat-messages")).to_be_visible()
            expect(page.locator("#project-chat-progress")).to_contain_text("Step 1")
            assert invalid==[], "Never download model/code just by opening page"
            page.locator("#project-ai-open").click()
            expect(page.locator("#project-ai-experience")).to_be_visible()
            expect(page.locator("#project-chat-messages")).to_be_hidden()
            expect(page.locator("#project-ai-consent")).to_be_visible()
            expect(page.locator("#project-ai-send")).to_be_disabled()
            assert invalid==[], "Opening disclosure must not start model downloads"
            page.locator("#project-ai-load").click()
            expect(page.locator("#project-ai-error")).to_contain_text(
                "WebGPU is unavailable")
            assert invalid==[], "Unsupported GPU must fail before external imports"
            page.locator("#project-ai-close").click()
            expect(page.locator("#project-chat-messages")).to_be_visible()
            expect(page.locator("#project-ai-experience")).to_be_hidden()
            page.locator("#project-chat-input").fill(
                "Help us design a safer workflow for shops and customers.")
            page.locator("#project-chat-send").click()
            expect(page.locator("#project-chat-progress")).to_contain_text("Step 2")
            dimensions=page.evaluate("() => [innerWidth,document.documentElement.scrollWidth]")
            assert dimensions[1]<=dimensions[0]+1,dimensions
            page.screenshot(path=str(ART/f"device-ai-consent-{name}.png"),full_page=True)
            context.close()
        browser.close()
    assert not page_errors,page_errors
    assert not invalid,invalid
    print("PASS: opt-in only, no silent download, unsupported WebGPU fail-closed,"
          " guided workflow retained, responsive layout")
if __name__=="__main__":
    main()
