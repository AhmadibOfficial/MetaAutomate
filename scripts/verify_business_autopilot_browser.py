#!/usr/bin/env python3
"""Real Chromium acceptance of the standalone synthetic Business Autopilot demo."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import urlopen

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.business_autopilot import strict_json, verify_bundle


def prepare_plan(page):
    page.get_by_role("button", name="Assess the synthetic business →", exact=True).click()
    expect(page.get_by_role("heading", name="Understand the operational gap.")).to_be_visible()
    page.get_by_role("button", name="Create the proposed plan →", exact=True).click()
    expect(page.get_by_role("heading", name="A plan you can inspect.")).to_be_visible()
    page.get_by_role("button", name="Review this plan →", exact=True).click()
    expect(page.get_by_role("button", name="Approve simulation →", exact=True)).to_be_disabled()


def approve_and_simulate(page):
    page.get_by_role("checkbox").check()
    page.get_by_role("button", name="Approve simulation →", exact=True).click()
    page.get_by_role("button", name="Simulate the approved drafts →", exact=True).click()
    expect(page.get_by_role("heading", name="Inspect what actually happened.")).to_be_visible()


def verify(page):
    page.get_by_role("button", name="Verify the evidence →", exact=True).click()
    expect(page.get_by_role("heading", name="An outcome with evidence behind it.")).to_be_visible()
    expect(page.locator("#download")).to_be_enabled()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=ROOT / "artifacts/business-autopilot")
    args = parser.parse_args()
    args.artifacts.mkdir(parents=True, exist_ok=True)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    server = subprocess.Popen([sys.executable, str(ROOT / "scripts/business_autopilot_demo.py"),
        "serve", "--port", str(port)], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if server.poll() is not None:
                raise AssertionError(server.stderr.read().decode())
            try:
                with urlopen(origin, timeout=.4) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(.1)
        else:
            raise AssertionError("Local demonstration did not start")

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            context = browser.new_context(viewport={"width":1440, "height":1050}, accept_downloads=True)
            page = context.new_page()
            errors, external = [], []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)

            def boundary(route):
                if route.request.url.startswith(origin + "/"):
                    route.continue_()
                else:
                    external.append(route.request.url)
                    route.abort()
            context.route("**/*", boundary)
            page.goto(origin)
            expect(page.locator("#download")).to_be_disabled()
            expect(page.get_by_role("button", name="Assess the synthetic business →", exact=True)).to_be_enabled()
            page.screenshot(path=str(args.artifacts / "scenario-desktop.png"), full_page=True)
            prepare_plan(page)
            approve_and_simulate(page)
            verify(page)
            with page.expect_download() as download:
                page.locator("#download").click()
            artifact = args.artifacts / "synthetic-evidence.json"
            download.value.save_as(artifact)
            assert verify_bundle(strict_json(artifact.read_bytes()))["verified"]
            expect(page.locator("#download")).to_be_focused()
            assert page.locator(".skip").evaluate("n => n.getBoundingClientRect().bottom <= 0"), "Skip link unexpectedly visible"
            assert page.evaluate("localStorage.length + sessionStorage.length") == 0
            assert context.cookies() == []
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(args.artifacts / "verified-desktop.png"), full_page=True)
            page.set_viewport_size({"width":390, "height":844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Mobile page overflows"
            page.wait_for_function("""() => {
                const nav = document.getElementById('journey').getBoundingClientRect();
                const step = document.querySelector('[aria-current="step"]').getBoundingClientRect();
                return step.left >= nav.left && step.right <= nav.right;
            }""")
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(args.artifacts / "verified-mobile.png"), full_page=True)

            # Keyboard approval rejection preserves the boundary.
            page.set_viewport_size({"width":1440, "height":1050})
            page.locator("#restart").click()
            prepare_plan(page)
            reject = page.get_by_role("button", name="Reject plan", exact=True)
            reject.focus(); reject.press("Enter")
            expect(page.get_by_text("Proposal rejected", exact=True)).to_be_visible()
            expect(page.get_by_role("button", name="Simulate the approved drafts →", exact=True)).to_have_count(0)
            expect(page.locator("#download")).to_be_disabled()

            page.locator("#scenario").select_option("partial_failure")
            prepare_plan(page)
            approve_and_simulate(page)
            expect(page.get_by_text("One step needs review", exact=True)).to_be_visible()
            verify(page)
            expect(page.locator("#kpi-drafts")).to_have_text("1")
            expect(page.locator("#kpi-value")).to_have_class("negative")

            page.locator("#scenario").select_option("high_cost")
            prepare_plan(page)
            approve_and_simulate(page)
            verify(page)
            expect(page.get_by_text("The model does not justify this cost", exact=True)).to_be_visible()
            expect(page.locator("#kpi-value")).to_contain_text("32.00")
            assert not errors, errors
            assert not external, external
            browser.close()
        print(json.dumps({"passed":True, "browser":"Chromium", "cases":[
            "complete flow and verified download", "mobile layout", "keyboard rejection",
            "blocked step", "negative estimated value", "no external requests or browser storage"]}))
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill(); server.wait(timeout=5)


if __name__ == "__main__":
    main()
