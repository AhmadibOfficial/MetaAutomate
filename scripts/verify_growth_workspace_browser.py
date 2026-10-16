#!/usr/bin/env python3
"""Chromium acceptance for local static customer Growth Autopilot demo.

Run against a local http.server only. No service API, billing, actual accounts,
customer data, subscriptions or external network requests are involved.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = "http://127.0.0.1:18080"
ART = Path("artifacts/validation")
ART.mkdir(parents=True, exist_ok=True)


def assert_no_overflow(page, width):
    metric = page.evaluate("""() => ({scroll:document.documentElement.scrollWidth,
      width:innerWidth,
      offenders:[...document.querySelectorAll("body *")].filter(el => {
        const r=el.getBoundingClientRect();
        return r.right > innerWidth+1 && getComputedStyle(el).position !== "fixed";
      }).slice(0,8).map(el=>({tag:el.tagName,className:el.className,
        right:Math.round(el.getBoundingClientRect().right)}))})""")
    assert metric["scroll"] <= metric["width"] + 1, (width, metric)


def main():
    leaks = []
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        for width in (1440, 390, 360):
            context = browser.new_context(
                viewport={"width":width,"height":900},
                device_scale_factor=1,
                reduced_motion="reduce",
            )
            page = context.new_page()
            page.on("request", lambda r: leaks.append(r.url) if not r.url.startswith(BASE) else None)
            page.on("pageerror",lambda err: errors.append(str(err)))
            res = page.goto(BASE+"/automation/",wait_until="networkidle")
            assert res and res.status == 200
            expect(page).to_have_title("Growth Autopilot — MetaAutomate | Interactive Demo")
            expect(page.locator(".brand img")).to_be_visible()
            assert page.locator(".brand img").evaluate("(el)=>el.complete && el.naturalWidth > 0")
            expect(page.locator(".notice")).to_contain_text("Not connected")
            expect(page.locator("#stat-sales")).to_have_text("25,000 DC")
            expect(page.locator("#stat-contribution")).to_have_text("14,500 DC")
            expect(page.locator("#stat-repeat")).to_have_text("1")
            expect(page.locator("#stat-queue")).to_have_text("4")
            assert_no_overflow(page,width)
            # The customer can navigate to the queue and inspect an invented workflow.
            page.locator("#open-queue").click()
            expect(page.locator("#panel-automations")).to_be_visible()
            expect(page.locator(".queue-row")).to_have_count(6)
            expect(page.locator("#queue-ready")).to_have_text("4 for review")
            expect(page.locator("#queue-suppressed")).to_have_text("2 suppressed")
            expect(page.locator(".queue-side strong.suppressed")).to_have_count(2)
            page.locator(".queue-row button").first.click()
            expect(page.locator("#inspection-panel")).to_contain_text("No network request")
            expect(page.locator("#inspection-panel")).to_contain_text("No")
            assert_no_overflow(page,width)
            # Tab roving uses keyboard controls without external requests.
            page.locator("#tab-automations").focus()
            page.keyboard.press("ArrowRight")
            expect(page.locator("#tab-value")).to_be_focused()
            expect(page.locator("#panel-value")).to_be_visible()
            expect(page.locator("#goal-target")).to_have_text("20,000 DC")
            expect(page.locator("#goal-gap")).to_have_text("5,500 DC to goal")
            page.locator("#target-slider").evaluate("(node) => { node.value = '25000'; node.dispatchEvent(new Event('input', {bubbles:true})); }")
            expect(page.locator("#goal-target")).to_have_text("25,000 DC")
            expect(page.locator("#goal-gap")).to_have_text("10,500 DC to goal")
            expect(page.locator("#goal-progress")).to_have_attribute("aria-valuenow","58")
            # Changing business recomputes figures, never claims real income.
            page.locator("#business-select").select_option("bespoke_demo")
            expect(page.locator("#stat-sales")).to_have_text("35,000 DC")
            expect(page.locator("#stat-contribution")).to_have_text("10,000 DC")
            expect(page.locator("#stat-queue")).to_have_text("4")
            expect(page.locator("#goal-target")).to_have_text("15,000 DC")
            expect(page.locator("#goal-gap")).to_have_text("5,000 DC to goal")
            page.locator("#tab-automations").click()
            expect(page.locator(".queue-row")).to_have_count(6)
            expect(page.locator("#queue-suppressed")).to_have_text("2 suppressed")
            page.locator(".queue-row button").nth(1).click()
            expect(page.locator("#inspection-panel")).to_contain_text("Selar")
            expect(page.locator("#inspection-panel")).to_contain_text("Suppressed")
            page.locator("#tab-setup").click()
            expect(page.locator("#panel-setup")).to_contain_text("Not available")
            expect(page.locator("#panel-setup")).to_contain_text("NO-GO")
            expect(page.locator("#panel-setup")).to_contain_text("3/9")
            assert_no_overflow(page,width)
            if width==1440:
                page.locator("#business-select").select_option("academy_demo")
                page.locator("#tab-overview").click()
                page.screenshot(path=str(ART/"growth-autopilot-desktop.png"),full_page=True)
            else:
                page.locator("#tab-overview").click()
                page.screenshot(path=str(ART/f"growth-autopilot-mobile-{width}.png"),full_page=True)
            context.close()
        assert not leaks, "Unexpected non-local request: " + str(leaks)
        assert not errors, "Browser JS errors: " + str(errors)
        browser.close()
    print("PASS_CUSTOMER_WORKSPACE_SYNTHETIC_ONLY: desktop+mobile, keyboard, goal controls, consent/provider suppression, no network calls")


if __name__ == "__main__":
    main()
