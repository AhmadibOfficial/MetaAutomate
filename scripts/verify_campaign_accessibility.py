#!/usr/bin/env python3
"""P2-060c: isolated browser keyboard/focus acceptance, synthetic inputs only.

Uses the same loopback-only read-only preview as P2-060b. No file artifacts,
external requests, social publishing, AI providers or live customer accounts.
A PASS is developer-local automated evidence, NOT a screen-reader/WCAG audit.
"""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_campaign_workbench_browser import (
    CSV, VIEWPORTS, ensure_playwright_driver, launch_full_chromium,
    same_origin, serve_local,
)


def focus_outline(page, selector: str, expected_color: str) -> None:
    """Browser-computed visible outline, not subjective/pixel WCAG contrast."""
    details = page.locator(selector).evaluate("""element => {
      const style = getComputedStyle(element);
      return {
        visible: element.matches(':focus-visible'),
        width: parseFloat(style.outlineWidth),
        color: style.outlineColor,
        kind: style.outlineStyle,
      };
    }""")
    assert details["visible"], (selector, details)
    assert details["width"] >= 3, (selector, details)
    assert details["kind"] not in ("none", "hidden"), (selector, details)
    assert details["color"] == expected_color, (selector, details)


def exercise_viewport(browser, base: str, label: str, width: int) -> None:
    from playwright.sync_api import expect

    context = browser.new_context(
        viewport={"width": width, "height": 900},
        reduced_motion="reduce", service_workers="block",
        accept_downloads=False,
    )
    errors: list[str] = []
    external: list[str] = []
    try:
        def restrict(route):
            if same_origin(route.request.url, base):
                route.continue_()
            else:
                external.append(route.request.url)
                route.abort()
        context.route("**/*", restrict)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        response = page.goto(base + "/campaigns/", wait_until="networkidle")
        assert response and response.status == 200
        assert page.locator("html").get_attribute("lang") == "en"
        assert page.get_by_role("navigation", name="Workspace links").count() == 1
        assert page.get_by_role("navigation", name="Campaign workflow phases").count() == 1

        # Keyboard-only skip link. A focused main landmark is a valid target.
        page.keyboard.press("Tab")
        expect(page.locator(".skip")).to_be_focused()
        focus_outline(page, ".skip", "rgb(4, 13, 32)")
        page.keyboard.press("Enter")
        expect(page.locator("main#main")).to_be_focused()

        # Every form control must have a meaningful accessible name.
        for name in ("Inventory CSV file", "Business / brand name",
                     "Planned social channel (draft only)",
                     "Editable social media post", "Review and edit the storyboard",
                     "Impressions", "Clicks", "Orders from this measured funnel",
                     "Evidence source / note"):
            assert page.get_by_label(name, exact=True).count() == 1, name

        # File dialog injection is the *only* nonkeyboard input operation
        # required; no native OS file picker is accessible to test runner.
        page.locator("#campaign-file").set_input_files({
            "name": "synthetic-inventory.csv", "mimeType": "text/csv",
            "buffer": CSV.encode("utf-8"),
        })
        page.locator("#campaign-import button[type=submit]").focus()
        page.keyboard.press("Enter")
        expect(page.locator("#campaign-results")).to_be_visible()
        expect(page.locator("#results-title")).to_be_focused()
        page.keyboard.press("Tab")
        expect(page.locator('input[name="candidate"]').first).to_be_focused()
        assert page.get_by_role("group", name="Select a stock opportunity").count() == 1

        page.locator("#campaign-brand").fill("Synthetic MetaAutomate Shop")
        # Move to the Create button by a real keyboard Tab, then assert its
        # focus-visible outline rather than relying on programmatic focus.
        page.locator("#campaign-channel").focus()
        page.keyboard.press("Tab")
        expect(page.locator("#campaign-create")).to_be_focused()
        focus_outline(page, "#campaign-create", "rgb(4, 13, 32)")
        page.keyboard.press("Enter")
        expect(page.locator("#campaign-project")).to_be_visible()
        expect(page.locator("#project-title")).to_be_focused()
        page.keyboard.press("Tab")
        expect(page.locator("#campaign-post")).to_be_focused()

        # Canvas accessibility is an actual descriptive text alternative.
        canvas = page.get_by_role("img", name="Promotional graphic preview")
        expect(canvas).to_be_visible()
        description = page.locator("#campaign-graphic-description")
        expect(description).to_contain_text("Branded Cap")
        expect(description).to_contain_text("₦8,500.00")
        expect(description).to_contain_text("Not published")
        assert canvas.get_attribute("aria-describedby") == "campaign-graphic-description"

        page.locator("#campaign-confirm").focus()
        page.keyboard.press("Space")
        assert page.locator("#campaign-confirm").is_checked()
        page.locator("#campaign-authorize").focus()
        page.keyboard.press("Enter")
        expect(page.locator("#campaign-approval-state")).to_contain_text(
            "Internal draft review recorded"
        )
        assert page.locator("#campaign-copy").is_enabled()

        # Editing invalidates existing internal approval (no publication).
        page.locator("#campaign-post").fill("Changed synthetic draft; review required.")
        assert page.locator("#campaign-copy").is_disabled()
        assert page.locator("#campaign-evidence").is_disabled()
        page.locator("#campaign-confirm").focus()
        page.keyboard.press("Space")
        page.locator("#campaign-authorize").focus()
        page.keyboard.press("Enter")
        assert page.locator("#campaign-copy").is_enabled()

        for field, value in (
            ("#campaign-impressions", "100"),
            ("#campaign-clicks", "20"),
            ("#campaign-orders", "3"),
            ("#campaign-metric-source", "Synthetic example only, no external campaign"),
        ):
            page.locator(field).fill(value)
        page.locator("#campaign-metric-form button[type=submit]").focus()
        page.keyboard.press("Enter")
        expect(page.locator("#campaign-metrics-result")).to_contain_text(
            "Self-reported"
        )
        assert page.locator("#campaign-evidence").is_enabled()
        dims = page.evaluate("""() => ({
          viewport: innerWidth, scroll: document.documentElement.scrollWidth
        })""")
        assert dims["scroll"] <= dims["viewport"] + 2, dims
        assert not errors, errors
        assert not external, external
    finally:
        context.close()


def run() -> None:
    ensure_playwright_driver()
    with serve_local() as base:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = launch_full_chromium(pw)
            try:
                for label, width in VIEWPORTS:
                    exercise_viewport(browser, base, label, width)
            finally:
                browser.close()
    print("DEVELOPER_LOCAL_ACCESSIBILITY_AUTOMATION_PASS")
    print("Keyboard transitions and visible focus checked at 1440/390/360 CSS pixels.")
    print("No screenshots saved, network egress or social publication performed.")
    print("NOT independent WCAG, screen-reader, CI, AppSec or release approval.")


if __name__ == "__main__":
    try:
        run()
    except Exception as error:
        print(f"ACCESSIBILITY_AUTOMATION_BLOCKED: {type(error).__name__}: {error}",
              file=sys.stderr)
        raise SystemExit(2) from None
