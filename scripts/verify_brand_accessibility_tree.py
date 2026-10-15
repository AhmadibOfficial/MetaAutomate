#!/usr/bin/env python3
"""Phase-independent, LOCAL browser accessibility-tree and keyboard walkthrough.

Chromium's Accessibility.getFullAXTree is useful automated semantic evidence;
it does NOT simulate an actual Orca, NVDA, JAWS or VoiceOver human session.
All form values are fabricated. No network requests outside local host.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright

BASE = "http://127.0.0.1:18080"
OUT = Path("artifacts") / "metaautomate-accessibility-tree-report.json"
OUT.parent.mkdir(exist_ok=True)


def snapshot(page) -> list[dict]:
    session = page.context.new_cdp_session(page)
    try:
        full = session.send("Accessibility.getFullAXTree", {"depth": -1})
    finally:
        session.detach()
    return [
        {
            "role": n.get("role", {}).get("value", ""),
            "name": n.get("name", {}).get("value", ""),
            "properties": {
                prop["name"]: prop.get("value", {}).get("value")
                for prop in n.get("properties", [])
                if prop.get("name") in ("pressed", "selected", "focused", "invalid", "required")
            },
        }
        for n in full.get("nodes", [])
        if not n.get("ignored", False)
    ]


def verify_role(nodes: list[dict], role: str, fragment: str | None = None) -> dict:
    found = [
        x for x in nodes if x["role"] == role
        and (fragment is None or fragment.lower() in x["name"].lower())
    ]
    assert found, f"Missing accessibility-tree {role!r}/{fragment!r}"
    return found[0]


def no_overflow(page, name: str) -> None:
    dims = page.evaluate(
        "() => ({viewport: innerWidth, scroll: document.documentElement.scrollWidth})"
    )
    assert dims["scroll"] <= dims["viewport"] + 1, (name, dims)


def test_home(browser, evidence: dict) -> None:
    context = browser.new_context(viewport={"width": 1440, "height": 940}, reduced_motion="reduce")
    page = context.new_page()
    assert page.goto(BASE + "/", wait_until="networkidle").status == 200
    nodes = snapshot(page)
    for role in ("banner", "navigation", "main", "contentinfo"):
        verify_role(nodes, role)
    verify_role(nodes, "heading", "Business challenges deserve")
    verify_role(nodes, "link", "Skip to content")
    verify_role(nodes, "link", "Discuss your project")
    verify_role(nodes, "group", "Objective Workspace example steps")
    verify_role(nodes, "image", "Illustrative dependency graph")
    verify_role(nodes, "button", "Define the objective")
    verify_role(nodes, "button", "Map dependencies")
    verify_role(nodes, "button", "Record a review")
    verify_role(nodes, "status")
    verify_role(nodes, "tablist", "Explore the MetaAutomate system approach")
    verify_role(nodes, "tabpanel", "Understand")

    # Real keyboard traversal, not synthetic DOM element.click() or focusing.
    page.keyboard.press("Tab")
    expect(page.locator(".skip-link")).to_be_focused()
    page.keyboard.press("Enter")
    assert urlsplit(page.url).fragment == "main"
    page.goto(BASE + "/", wait_until="networkidle")
    first = page.locator('[data-workspace-step="define"]')
    first.focus()  # find the starting position; next actions use only keys
    page.keyboard.press("Tab")
    expect(page.locator('[data-workspace-step="map"]')).to_be_focused()
    page.keyboard.press("Enter")
    expect(page.locator("#workspace-stage-title")).to_have_text(
        "Identify what needs to happen first."
    )
    expect(page.locator('[data-workspace-step="map"]')).to_have_attribute("aria-pressed", "true")
    page.keyboard.press("Tab")
    expect(page.locator('[data-workspace-step="review"]')).to_be_focused()
    page.keyboard.press("Space")
    expect(page.locator("#workspace-stage-description")).to_contain_text(
        "No supplier message"
    )
    expect(page.locator('[data-workspace-step="review"]')).to_have_attribute("aria-pressed", "true")
    after = snapshot(page)
    pressed = verify_role(after, "button", "Record a review").get("properties", {}).get("pressed")
    assert pressed in ("true", True), ("Missing AX pressed state", pressed)
    verify_role(after, "status")
    tabs = page.get_by_role("tab")
    tabs.nth(0).focus()
    page.keyboard.press("ArrowRight")
    expect(tabs.nth(1)).to_be_focused()
    expect(tabs.nth(1)).to_have_attribute("aria-selected", "true")
    no_overflow(page, "home desktop")
    evidence["home"] = {
        "landmarks": ["banner", "navigation", "main", "contentinfo"],
        "illustrative_graph_label": True,
        "workspace_status_and_pressed_state": True,
        "skip_link_keyboard": True,
        "workspace_enter_space_and_tab_keyboard": True,
        "operating_principles_arrow_navigation": True,
        "actual_screen_reader_used": False,
    }
    context.close()


def test_mobile_menu(browser, evidence: dict) -> None:
    context = browser.new_context(
        viewport={"width": 390, "height": 844}, is_mobile=True,
        has_touch=True, reduced_motion="reduce",
    )
    page = context.new_page()
    page.goto(BASE + "/", wait_until="networkidle")
    page.keyboard.press("Tab")
    expect(page.locator(".skip-link")).to_be_focused()
    page.keyboard.press("Tab")
    expect(page.locator(".site-header .brand")).to_be_focused()
    page.keyboard.press("Tab")
    menu = page.locator("#menu-button")
    expect(menu).to_be_focused()
    page.keyboard.press("Enter")
    expect(menu).to_have_attribute("aria-expanded", "true")
    verify_role(snapshot(page), "navigation", "Primary navigation")
    page.keyboard.press("Escape")
    expect(menu).to_have_attribute("aria-expanded", "false")
    expect(menu).to_be_focused()
    page.keyboard.press("Enter")
    page.keyboard.press("Tab")
    expect(page.get_by_role("navigation", name="Primary navigation").get_by_role("link", name="Solutions", exact=True)).to_be_focused()
    no_overflow(page, "mobile menu")
    evidence["mobile_menu"] = {
        "skip_brand_menu_tab_order": True,
        "enter_opens_menu": True,
        "escape_closes_and_restores_focus": True,
        "keyboard_reaches_first_menu_item": True,
        "actual_screen_reader_used": False,
    }
    context.close()


def test_enquiry(browser, evidence: dict) -> None:
    context = browser.new_context(
        viewport={"width": 1240, "height": 950},
        reduced_motion="reduce",
        accept_downloads=True,
    )
    page = context.new_page()
    page.goto(BASE + "/engage/", wait_until="networkidle")
    before = snapshot(page)
    verify_role(before, "heading", "Tell us your business challenge")
    verify_role(before, "link", "Email a project question")
    verify_role(before, "combobox", "Service area")
    verify_role(before, "combobox", "Project stage")
    verify_role(before, "textbox", "What business challenge are you tackling")
    verify_role(before, "textbox", "What value would a successful outcome create")
    verify_role(before, "button", "Prepare my enquiry")
    assert not any(
        "Ready for the next conversation." in node["name"]
        for node in before
    ), "Hidden result must not be exposed to assistive technology"

    page.get_by_role("button", name="Prepare my enquiry").click()
    expect(page.locator("#brief-error")).to_be_visible()
    expect(page.locator("#brief-service")).to_be_focused()
    verify_role(snapshot(page), "alert")
    expect(page.locator("#brief-error")).to_contain_text("Complete the required fields")

    # Fabricated inputs only. The form prepares a mailto and does not submit.
    page.get_by_label("Service area").select_option(label="Cybersecurity & Quality")
    page.get_by_label("Project stage").select_option(label="Existing product or system")
    page.get_by_label("What business challenge are you tackling?").fill(
        "A fictional business wants to review an invented software application's API security."
    )
    page.get_by_label("What value would a successful outcome create?").fill(
        "A clear list of hypothetical API risks and proposed improvements."
    )
    page.get_by_role("button", name="Prepare my enquiry").click()
    expect(page.locator("#brief-result")).to_be_visible()
    expect(page.locator("#brief-result-title")).to_be_focused()
    nodes = snapshot(page)
    verify_role(nodes, "heading", "Ready for the next conversation")
    verify_role(nodes, "link", "Compose email to MetaAutomate")
    verify_role(nodes, "button", "Copy brief")
    verify_role(nodes, "button", "Download .txt")
    verify_role(nodes, "status")
    mailto = page.locator("#brief-email").get_attribute("href")
    assert mailto.startswith("mailto:metaautomating@gmail.com?")
    assert not page.locator("form").get_attribute("action")
    no_overflow(page, "enquiry desktop")
    evidence["enquiry"] = {
        "all_required_fields_named_in_accessibility_tree": True,
        "invalid_submit_alert_and_first_invalid_focus": True,
        "hidden_result_not_exposed": True,
        "brief_result_heading_receives_focus": True,
        "mailto_generated_without_form_post": True,
        "actual_screen_reader_used": False,
    }
    context.close()


def main() -> None:
    evidence = {
        "scope": "LOCAL_CHROMIUM_ACCESSIBILITY_TREE_AND_KEYBOARD_ONLY",
        "status": "AUTOMATED_SEMANTIC_CHECKS_NOT_SCREEN_READER_CERTIFICATION",
        "owner_human_screen_reader_session": "NOT_PERFORMED",
        "tested_on_actual_production_site": False,
        "real_customer_data": False,
        "external_network_used": False,
        "cases": {},
    }
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            test_home(browser, evidence["cases"])
            test_mobile_menu(browser, evidence["cases"])
            test_enquiry(browser, evidence["cases"])
        finally:
            browser.close()
    OUT.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print("PASS: Chromium AX tree, desktop+mobile keyboard, dynamic status, form focus, local-only no-post")
    print("ACCESSIBILITY_CERTIFICATION=NOT_PERFORMED; ACTUAL_SCREEN_READER=NOT_PERFORMED")
    print(f"ACCESSIBILITY_REPORT={OUT}")


if __name__ == "__main__":
    main()
