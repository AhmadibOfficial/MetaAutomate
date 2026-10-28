#!/usr/bin/env python3
"""Live-source website acceptance for the P2-064 static MetaAutomate release.

Local 127.0.0.1 origin only. Tests actual Chromium, UI controls, keyboard access,
mobile overflow, privacy, and retained service pages. Not a screen reader audit.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit
from playwright.sync_api import expect, sync_playwright

BASE = "http://127.0.0.1:18080"
ART = Path("artifacts")
ART.mkdir(exist_ok=True)
SAFE = ("http://127.0.0.1:18080/",)

def no_overflow(page, label):
    dims = page.evaluate("({viewport: innerWidth, scroll: document.documentElement.scrollWidth})")
    assert dims["scroll"] <= dims["viewport"] + 2, (label, dims)

def local_route(route, external):
    url = urlsplit(route.request.url)
    if url.scheme != "http" or url.netloc != "127.0.0.1:18080":
        external.append(route.request.url)
        route.abort()
    else:
        route.continue_()

def has_ax_role(page, role, fragment=None):
    session = page.context.new_cdp_session(page)
    try:
        nodes = session.send("Accessibility.getFullAXTree", {"depth": -1})["nodes"]
    finally:
        session.detach()
    for node in nodes:
        if node.get("ignored"):
            continue
        if node.get("role", {}).get("value") != role:
            continue
        name = node.get("name", {}).get("value", "")
        if fragment is None or fragment.lower() in name.lower():
            return True
    raise AssertionError(f"Missing AX role {role!r} / {fragment!r}")

def assert_mark(page, selector):
    img = page.locator(selector).first
    expect(img).to_be_visible()
    assert img.evaluate("(img) => img.complete && img.naturalWidth > 0")

def test_desktop(browser, errors, external, observations):
    context = browser.new_context(viewport={"width": 1440, "height": 940},
                                  reduced_motion="reduce", accept_downloads=True)
    page = context.new_page()
    page.route("**/*", lambda route: local_route(route, external))
    page.on("pageerror", lambda err: errors.append(str(err)))

    assert page.goto(BASE + "/", wait_until="load").status == 200
    expect(page).to_have_title("MetaAutomate — Solve real business challenges")
    expect(page.get_by_role("heading", level=1)).to_contain_text("Real business challenges.")
    expect(page.locator("#solutions .solution")).to_have_count(5)
    expect(page.locator(".how li")).to_have_count(3)
    expect(page.locator('a[href="/workspace/"]').first).to_be_visible()
    assert_mark(page, ".logo img")
    has_ax_role(page, "banner")
    has_ax_role(page, "navigation")
    has_ax_role(page, "main")
    has_ax_role(page, "heading", "Real business challenges")
    has_ax_role(page, "contentinfo")
    expect(page.locator("a.skip")).to_have_count(1)
    page.keyboard.press("Tab")
    expect(page.locator("a.skip")).to_be_focused()
    page.keyboard.press("Enter")
    assert urlsplit(page.url).fragment == "main"
    no_overflow(page, "desktop homepage")
    page.screenshot(path=str(ART / "metaautomate-global-home-desktop.png"), full_page=True)
    observations["home"] = {"five_sector_shortcuts": True, "skip_link_keyboard": True}

    assert page.goto(BASE + "/workspace/", wait_until="load").status == 200
    expect(page.locator("[data-goal]")).to_have_count(5)
    expect(page.locator("[data-sector]")).to_have_count(5)
    expect(page.locator('#more-industries option')).to_have_count(18)
    expect(page.locator(".sidebar-nav a")).to_have_count(4)
    has_ax_role(page, "main")
    has_ax_role(page, "navigation", "Main navigation")
    has_ax_role(page, "button", "Intelligent automation")
    # Keyboard activation of a real objective button, not simulated JavaScript dispatch.
    automation = page.locator('[data-goal="automation"]')
    automation.focus()
    page.keyboard.press("Enter")
    expect(automation).to_have_attribute("aria-pressed", "true")
    expect(page.locator('[data-goal="operations"]')).to_have_attribute("aria-pressed", "false")
    page.locator("#more-industries").select_option("custom_operations")
    expect(page.locator("#selected-sector-title")).to_have_text("Custom Organization Workflow")
    page.locator("#challenge").fill("Improve staff handoff for non-sensitive requests")
    page.locator('#new-work-form button[type="submit"]').click()
    expect(page.locator("#view-work")).to_be_visible()
    expect(page.locator("#plan-list .plan-button")).to_have_count(1)
    expect(page.locator("#plan-steps input[type=checkbox]")).to_have_count(4)
    expect(page.locator("#complete-plan")).to_be_disabled()
    for i in range(4):
        page.locator("#plan-steps input[type=checkbox]").nth(i).check()
    expect(page.locator("#complete-plan")).to_be_disabled()
    page.locator("#plan-review").check()
    expect(page.locator("#complete-plan")).to_be_enabled()
    page.locator("#complete-plan").click()
    expect(page.locator("#plan-status")).to_contain_text("reviewed locally")
    page.locator('.sidebar-nav a[data-route="results"]').click()
    expect(page.locator("#results-plans")).to_have_text("1")
    expect(page.locator("#results-reviewed")).to_have_text("1")
    expect(page.locator("#results-steps")).to_have_text("4")
    with page.expect_download() as download:
        page.locator("#export-evidence").click()
    report = json.loads(Path(download.value.path()).read_text(encoding="utf-8"))
    assert report["independentlyVerified"] is False
    assert report["outsideActionsPerformed"] is False
    assert report["aiModelUsed"] is False
    page.locator('.sidebar-nav a[data-route="settings"]').click()
    page.locator("#clear-session").click()
    page.locator('.sidebar-nav a[data-route="results"]').click()
    expect(page.locator("#results-plans")).to_have_text("0")
    expect(page.locator("#results-reviewed")).to_have_text("0")
    no_overflow(page, "desktop workspace")
    page.screenshot(path=str(ART / "metaautomate-global-workspace-desktop.png"), full_page=True)
    observations["workspace"] = {
        "objectives": 5, "expanded_sector_options": 17,
        "review_gate": True, "reset": True, "unverified_report": True
    }

    # These working pages must stay available, not be replaced by decorative dead links.
    for path in ("/services/", "/company/", "/engage/", "/creative/"):
        response = page.goto(BASE + path, wait_until="load")
        assert response and response.status == 200, path
        has_ax_role(page, "main")
        no_overflow(page, path)
        observations[path] = {"reachable": True}
    page.goto(BASE + "/company/", wait_until="load")
    expect(page.locator(".principle-halal")).to_contain_text("Always HALAL")
    expect(page.locator(".roadmap-entry")).to_have_count(4)
    page.goto(BASE + "/engage/", wait_until="load")
    expect(page.locator("#project-chat-input")).to_be_visible()
    expect(page.locator("#project-chat-send")).to_be_visible()
    expect(page.locator("#brief-form")).to_have_count(0)
    page.goto(BASE + "/creative/", wait_until="load")
    expect(page.locator("#maker-canvas")).to_have_count(1)
    expect(page.locator("#video-maker-form")).to_have_count(1)
    observations["legacy_critical_tools_preserved"] = True
    context.close()

def test_mobile(browser, errors, external, observations):
    for width in (390, 360):
        context = browser.new_context(viewport={"width": width, "height": 844},
                                      is_mobile=True, has_touch=True,
                                      reduced_motion="reduce")
        page = context.new_page()
        page.route("**/*", lambda route: local_route(route, external))
        page.on("pageerror", lambda err: errors.append(str(err)))
        assert page.goto(BASE + "/", wait_until="load").status == 200
        expect(page.locator("#solutions .solution")).to_have_count(5)
        no_overflow(page, f"home {width}px")
        assert page.goto(BASE + "/workspace/", wait_until="load").status == 200
        expect(page.locator("#menu-toggle")).to_be_visible()
        menu = page.locator("#menu-toggle")
        menu.click()
        expect(menu).to_have_attribute("aria-expanded", "true")
        page.locator('.sidebar-nav a[data-route="work"]').click()
        expect(page.locator("#view-work")).to_be_visible()
        expect(menu).to_have_attribute("aria-expanded", "false")
        menu.click()
        page.locator('.sidebar-nav a[data-route="home"]').click()
        page.locator('[data-goal="customer"]').click()
        expect(page.locator('[data-goal="customer"]')).to_have_attribute("aria-pressed", "true")
        no_overflow(page, f"workspace {width}px")
        page.screenshot(path=str(ART / f"metaautomate-global-workspace-{width}.png"), full_page=True)
        observations[f"mobile_{width}"] = {"no_overflow": True, "drawer": True, "goal_selection": True}
        context.close()

def main():
    errors, external, observations = [], [], {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            test_desktop(browser, errors, external, observations)
            test_mobile(browser, errors, external, observations)
        finally:
            browser.close()
    assert not errors, errors
    assert not external, external
    result = {
        "scope": "LOCAL_ONLY_STATIC_WEBSITE",
        "actual_screen_reader_used": False,
        "production_deploy_verified": False,
        "customer_data_used": False,
        "external_request_attempts": external,
        "page_errors": errors,
        "observations": observations
    }
    out = ART / "metaautomate-accessibility-tree-report.json"
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("PASS: real Chromium desktop/mobile, local-only, accessibility tree and interactive workflow")
    print(f"EVIDENCE_FILE={out}")

if __name__ == "__main__":
    main()
