#!/usr/bin/env python3
"""P2-04b: local-only Chromium creative planning acceptance, no provider calls."""
from pathlib import Path
from playwright.sync_api import expect, sync_playwright

BASE="http://127.0.0.1:18080"
ART=Path("artifacts/validation")
ART.mkdir(parents=True,exist_ok=True)

def check_overflow(page,name):
    metrics=page.evaluate(
        "() => ({viewport:innerWidth,scroll:document.documentElement.scrollWidth})"
    )
    assert metrics["scroll"]<=metrics["viewport"]+1,(name,metrics)

def main():
    network_violations=[]
    script_errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        for name,viewport in (
            ("desktop",{"width":1440,"height":920}),
            ("mobile",{"width":390,"height":844}),
            ("small-mobile",{"width":360,"height":780}),
        ):
            context=browser.new_context(
                viewport=viewport,reduced_motion="reduce",
                accept_downloads=True,device_scale_factor=1,
            )
            page=context.new_page()
            page.on("request",lambda r:network_violations.append(r.url)
                    if not r.url.startswith(BASE) else None)
            page.on("pageerror",lambda e:script_errors.append(str(e)))
            response=page.goto(BASE+"/creative/",wait_until="networkidle")
            assert response.status==200
            expect(page).to_have_title("Creative Workbench — MetaAutomate")
            expect(page.get_by_role("heading",level=1)).to_contain_text(
                "Creative ideas deserve"
            )
            expect(page.locator(".brand img").first).to_be_visible()
            expect(page.locator(".brand img").first).to_have_js_property("complete",True)
            page.locator(".creative-advanced-planning summary").click()
            expect(page.locator("#creative-output")).to_be_hidden()
            expect(page.locator("#creative-video-control")).to_be_hidden()
            expect(page.locator("#creative-kind")).to_have_value("image")
            page.locator("#creative-kind").select_option("video")
            expect(page.locator("#creative-video-control")).to_be_visible()
            page.locator("#creative-duration").select_option("90")
            page.locator("#creative-goal").fill(
                "Explain how accurate inventory records can help small shop owners"
                " improve purchase decisions, without promising revenue."
            )
            page.locator("#creative-audience").fill("Local shop owners")
            page.locator("#creative-reviewer").fill("Human creative editor")
            # A review owner does not erase unknown rights or consent.
            page.get_by_role("button",name="Build the review brief").click()
            expect(page.locator("#creative-outcome")).to_contain_text("HOLD")
            expect(page.locator("#creative-checks")).to_contain_text(
                "rights to referenced assets are not established"
            )
            expect(page.locator("#creative-checks")).to_contain_text(
                "consent has not been established"
            )
            expect(page.locator("#creative-structure")).to_contain_text(
                "Scene 4"
            )
            expect(page.locator("#creative-structure")).to_contain_text(
                "90 sec"
            )
            # A licence self-declaration requires traceable evidence.
            page.locator("#creative-rights").select_option("licensed")
            page.locator("#creative-likeness").select_option("none")
            page.get_by_role("button",name="Build the review brief").click()
            expect(page.locator("#creative-outcome")).to_contain_text("HOLD")
            expect(page.locator("#creative-checks")).to_contain_text(
                "traceable permission reference"
            )
            page.locator("#creative-proof").fill("Licensing record CI-NOT-REAL-2026")
            page.get_by_role("button",name="Build the review brief").click()
            expect(page.locator("#creative-outcome")).to_contain_text(
                "READY FOR HUMAN REVIEW"
            )
            expect(page.locator("#creative-outcome")).to_contain_text(
                "NOT APPROVED"
            )
            expect(page.locator("#creative-checks")).to_contain_text(
                "NOT authenticated"
            )
            expect(page.locator("#creative-checks")).to_contain_text(
                "Generation, export of media, distribution and publishing remain disabled"
            )
            with page.expect_download() as dl:
                page.locator("#creative-export").click()
            download=dl.value
            assert download.suggested_filename=="metaautomate-creative-review-brief.txt"
            data=Path(download.path()).read_text(encoding="utf-8")
            assert "NO MEDIA GENERATED OR PUBLISHED" in data
            assert "SHORT-FORM VIDEO" in data
            assert "NOT APPROVED" in data
            assert "Scene 4" in data
            # Unknown scripts must render as literal text rather than HTML.
            page.locator("#creative-kind").select_option("image")
            page.locator("#creative-goal").fill(
                "A safe brief about inventory: <img src=x onerror=alert(1)>"
            )
            page.locator("#creative-rights").select_option("none")
            page.get_by_role("button",name="Build the review brief").click()
            expect(page.locator("#creative-video-control")).to_be_hidden()
            assert page.locator("#creative-structure img").count()==0
            expect(page.locator("#creative-structure")).to_contain_text(
                "<img src=x onerror=alert(1)>"
            )
            expect(page.locator("#creative-structure")).to_contain_text(
                "Image composition"
            )
            page.screenshot(path=str(ART/f"creative-workbench-{name}.png"),full_page=True)
            check_overflow(page,name)
            page.get_by_role("button",name="Clear form").click()
            expect(page.locator("#creative-output")).to_be_hidden()
            expect(page.locator("#creative-kind")).to_have_value("image")
            expect(page.locator("#creative-video-control")).to_be_hidden()
            context.close()
        browser.close()
    assert not network_violations,network_violations
    assert not script_errors,script_errors
    print("PASS: Creative Workbench desktop and mobile, rights/consent HOLD,"
          " reviewer-only handoff, 90-sec video plan, text export,"
          " XSS-safe rendering and no external network requests")

if __name__=="__main__":
    main()
