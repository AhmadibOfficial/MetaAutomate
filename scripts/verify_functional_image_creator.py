#!/usr/bin/env python3
"""Actual Chromium: create and download 1080/1920px PNGs, no model calls."""
from pathlib import Path
import struct
from playwright.sync_api import sync_playwright, expect

ROOT="http://127.0.0.1:18080"
ART=Path("artifacts/validation")
ART.mkdir(parents=True,exist_ok=True)

def size_of_png(path):
    raw=Path(path).read_bytes()
    assert raw.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(raw)>1000
    return struct.unpack(">II",raw[16:24])

def main():
    errors=[];external=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        for viewport in [(1440,900),(390,844)]:
            name="desktop" if viewport[0]>500 else "mobile"
            context=browser.new_context(viewport={"width":viewport[0],"height":viewport[1]},
                                        accept_downloads=True,reduced_motion="reduce")
            page=context.new_page()
            page.on("pageerror",lambda e:errors.append(str(e)))
            page.on("request",lambda r:external.append(r.url)
                    if not r.url.startswith(ROOT) else None)
            response=page.goto(ROOT+"/creative/",wait_until="networkidle")
            assert response.status==200
            expect(page.locator("#maker-download")).to_be_enabled()
            expect(page.locator("#maker-canvas")).to_be_visible()
            for image_format,dims in [
                ("square",(1080,1080)),
                ("story",(1080,1920)),
                ("wide",(1920,1080)),
            ]:
                page.locator("#maker-format").select_option(image_format)
                expect(page.locator("#maker-download")).to_be_disabled()
                page.locator("#maker-title-input").fill(
                    "Build a better business system with original design")
                page.locator("#maker-preview").click()
                expect(page.locator("#maker-download")).to_be_enabled()
                size=page.locator("#maker-canvas").evaluate(
                    "c => [c.width, c.height]")
                assert tuple(size)==dims,(size,dims)
                with page.expect_download() as event:
                    page.locator("#maker-download").click()
                download=event.value
                assert download.suggested_filename==f"metaautomate-original-{image_format}.png"
                assert size_of_png(download.path())==dims
                expect(page.locator("#maker-status")).to_contain_text("downloaded")
            expect(page.locator("#creative-rights")).to_have_value("unknown")
            expect(page.locator("#creative-likeness")).to_have_value("unknown")
            assert page.evaluate("() => document.documentElement.scrollWidth<=innerWidth+1")
            page.screenshot(path=str(ART/f"functional-image-creator-{name}.png"),
                            full_page=True)
            context.close()
        browser.close()
    assert not errors,errors
    assert not external,external
    print("PASS real Chrome PNG outputs: 1080x1080, 1080x1920, 1920x1080; mobile + safety")

if __name__=="__main__":
    main()
