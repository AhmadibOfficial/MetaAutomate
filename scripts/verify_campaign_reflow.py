#!/usr/bin/env python3
"""P2-060d private Chromium reflow evidence (synthetic inventory only).

An effective 640 CSS-px width models the layout space available at 200%
browser zoom on a nominal 1280px desktop. THIS DOES NOT CHANGE REAL CHROME
BROWSER ZOOM: actual browser-zoom, visual, screen-reader and WCAG review
remain separate manual gates. No customer data, publishing or cloud calls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_campaign_workbench_browser import (
    CSV, ensure_playwright_driver, launch_full_chromium,
    new_artifact_directory, same_origin, serve_local,
)

CASES = (
    ("desktop-1280", 1280, 720, "100%-baseline"),
    ("zoom200-effective-640", 640, 360, "200%-layout-approximation"),
    ("mobile-390", 390, 844, "mobile-layout"),
    ("mobile-360", 360, 780, "mobile-layout"),
    ("reflow-320", 320, 640, "320-css-px-reflow"),
)
CHECK_TARGETS = (
    "#campaign-file", "#campaign-import button[type=submit]",
    "#campaign-sample", "#campaign-create", "#campaign-post",
    "#campaign-copy", "#campaign-canvas", "#campaign-png",
    "#campaign-video-brief", "#campaign-video-download",
    "#campaign-confirm", "#campaign-authorize",
    "#campaign-impressions", "#campaign-clicks",
    "#campaign-orders", "#campaign-metric-source",
    "#campaign-metric-form button[type=submit]", "#campaign-evidence",
)
# Pairs whose actual occupied boxes must not intersect.
PAIR_GROUPS = (
    ("#campaign-import .field", "#campaign-import button[type=submit]",
     "#campaign-sample"),
    ("#campaign-results .field", "#campaign-create"),
    ("#campaign-media .media-pane:first-child",
     "#campaign-media .media-pane:last-child"),
    ("#campaign-measure .three-fields .field:nth-child(1)",
     "#campaign-measure .three-fields .field:nth-child(2)",
     "#campaign-measure .three-fields .field:nth-child(3)"),
)


def box_overlap(a: dict, b: dict, tolerance: float = 1.0) -> bool:
    """Whether two visible rectangles overlap in *both* directions."""
    overlap_x = min(a["right"], b["right"]) - max(a["left"], b["left"])
    overlap_y = min(a["bottom"], b["bottom"]) - max(a["top"], b["top"])
    return overlap_x > tolerance and overlap_y > tolerance


def evaluate_layout(page) -> dict:
    """Read-only DOM geometry after all conditional campaign sections appear.

    Checks horizontal page overflow, important control bounds, clipped text,
    sibling control overlap, and sticky-status obstruction risks. Screenshots
    remain necessary for nuanced pixel overlap and readable typography.
    """
    from playwright.sync_api import expect

    report = page.evaluate("""({selectors, groups}) => {
      const box = el => {
        const r = el.getBoundingClientRect();
        return {left:r.left,top:r.top,right:r.right,bottom:r.bottom,
                width:r.width,height:r.height};
      };
      const excluded = el => {
        const s = getComputedStyle(el);
        return s.display === 'none' || s.visibility === 'hidden';
      };
      const viewport = innerWidth;
      const fields = selectors.map(selector => {
        const el = document.querySelector(selector);
        if (!el || excluded(el)) return {selector, missing:true};
        const r = box(el);
        return {selector, ...r, disabled:el.matches(':disabled')};
      });
      const peers = groups.map(group => group.map(selector => {
        const el = document.querySelector(selector);
        return {selector, ...(el ? box(el) : {}),
                missing:!el || excluded(el)};
      }));
      const textSelectors = [
        '.hero h1', '.hero .intro', '.notice', '#import-title',
        '#results-title', '#project-title', '#media-title',
        '#approval-title', '#measure-title',
        '.check', '#campaign-graphic-description',
        '#campaign-approval-state', '#campaign-metrics-result'
      ];
      const textNodes = textSelectors.map(selector => {
        const el = document.querySelector(selector);
        if (!el || excluded(el)) return {selector, missing:true};
        const s = getComputedStyle(el);
        return {selector, size:parseFloat(s.fontSize),
          horizontalClip:el.scrollWidth > el.clientWidth + 2,
          verticalClip:el.scrollHeight > el.clientHeight + 2,
          rect:box(el)};
      });
      const status = document.querySelector('#campaign-status');
      return {
        viewport, documentWidth:document.documentElement.scrollWidth,
        bodyWidth:document.body.scrollWidth, fields, peers, textNodes,
        statusPosition:getComputedStyle(status).position,
      };
    }""", {"selectors": list(CHECK_TARGETS), "groups": [list(g) for g in PAIR_GROUPS]})

    width = report["viewport"]
    assert report["documentWidth"] <= width + 2, ("page overflow", report)
    assert report["bodyWidth"] <= width + 2, ("body overflow", report)
    for item in report["fields"]:
        assert not item.get("missing"), ("control missing", item)
        assert item["width"] >= 18 and item["height"] >= 18, ("tiny control", item)
        assert item["left"] >= -2 and item["right"] <= width + 2, (
            "control clipped horizontally", width, item)
    for item in report["textNodes"]:
        assert not item.get("missing"), ("text missing", item)
        assert item["size"] >= 11, ("tiny text", item)
        assert not item["horizontalClip"] and not item["verticalClip"], (
            "text clipped", item)
        assert item["rect"]["left"] >= -2 and item["rect"]["right"] <= width + 2, (
            "text outside CSS viewport", width, item)
    for group in report["peers"]:
        for item in group:
            assert not item.get("missing"), ("layout sibling missing", item)
        for i, left in enumerate(group):
            for right in group[i+1:]:
                assert not box_overlap(left, right), ("overlapping elements", left, right)
    if width <= 760:
        assert report["statusPosition"] != "sticky", (
            "status may cover controls when zoomed", report["statusPosition"])
    return report


def keyboard_and_hit_target_checks(page) -> None:
    """Avoid author-only geometry success; test actual browser hit targets."""
    from playwright.sync_api import expect

    page.locator("#campaign-post").focus()
    page.keyboard.press("Tab")
    expect(page.locator("#campaign-copy")).to_be_focused()
    for selector in (
        "#campaign-import button[type=submit]", "#campaign-create",
        "#campaign-png", "#campaign-video-download", "#campaign-authorize",
        "#campaign-metric-form button[type=submit]", "#campaign-evidence",
    ):
        item = page.locator(selector)
        assert item.is_enabled(), (selector, "expected enabled")
        # trial=True scrolls to the target and tests unobstructed actionability,
        # without clicking or downloading a file.
        item.click(trial=True, timeout=6000)


def exercise_case(browser, base: str, case: tuple, out: Path) -> dict:
    from playwright.sync_api import expect

    label, width, height, classification = case
    context = browser.new_context(
        viewport={"width": width, "height": height},
        accept_downloads=False, reduced_motion="reduce",
        service_workers="block",
    )
    failures = []
    external = []
    try:
        def only_origin(route):
            if same_origin(route.request.url, base):
                route.continue_()
            else:
                external.append(route.request.url)
                route.abort()
        context.route("**/*", only_origin)
        page = context.new_page()
        page.on("pageerror", lambda error: failures.append(str(error)))
        page.on("request", lambda request: external.append(request.url)
                if not same_origin(request.url, base) else None)
        response = page.goto(base + "/campaigns/", wait_until="networkidle")
        assert response and response.status == 200
        expect(page.get_by_role("heading", name="Work with your own stock records.")).to_be_visible()
        page.locator("#campaign-file").set_input_files({
            "name": "synthetic-inventory.csv",
            "mimeType": "text/csv", "buffer": CSV.encode("utf-8"),
        })
        page.locator("#campaign-import button[type=submit]").click()
        expect(page.locator("#campaign-count")).to_have_text("3")
        expect(page.locator("#campaign-flagged")).to_have_text("2")
        page.locator("#campaign-brand").fill("Synthetic MetaAutomate Shop")
        page.locator("#campaign-create").click()
        expect(page.locator("#campaign-project")).to_be_visible()
        expect(page.locator("#campaign-media")).to_be_visible()
        expect(page.locator("#campaign-canvas")).to_have_attribute("width", "1080")
        page.locator("#campaign-confirm").check()
        page.locator("#campaign-authorize").click()
        expect(page.locator("#campaign-approval-state")).to_contain_text(
            "Internal draft review recorded")
        for selector, value in (
            ("#campaign-impressions", "100"),
            ("#campaign-clicks", "20"),
            ("#campaign-orders", "3"),
            ("#campaign-metric-source", "Synthetic example only, no external campaign"),
        ):
            page.locator(selector).fill(value)
        page.locator("#campaign-metric-form button[type=submit]").click()
        expect(page.locator("#campaign-metrics-result")).to_contain_text("Self-reported")
        keyboard_and_hit_target_checks(page)
        geometry = evaluate_layout(page)
        # Scroll to top for a consistent full-page synthetic visual record.
        page.evaluate("() => window.scrollTo(0, 0)")
        image_file = out / f"campaign-reflow-{label}.png"
        page.screenshot(path=str(image_file), full_page=True)
        assert image_file.stat().st_size > 3000
        assert not external and not failures, (external, failures)
        return {
            "case": label,
            "cssViewport": {"width": width, "height": height},
            "classification": classification,
            "horizontalOverflow": False,
            "controlsChecked": len(CHECK_TARGETS),
            "textBlocksChecked": len(geometry["textNodes"]),
            "siblingOverlapDetected": False,
            "stickyStatus": geometry["statusPosition"] == "sticky",
            "offOriginRequests": 0,
            "pageErrors": 0,
            "screenshot": image_file.name,
        }
    finally:
        context.close()


def run(output: Path | None = None) -> Path:
    ensure_playwright_driver()
    from playwright.sync_api import sync_playwright
    with serve_local() as base, sync_playwright() as pw:
        browser = launch_full_chromium(pw)
        try:
            out = new_artifact_directory(output)
            cases = [exercise_case(browser, base, case, out) for case in CASES]
        finally:
            browser.close()
    report = {
        "schemaVersion": 1,
        "milestone": "P2-060d",
        "status": "DEVELOPER_LOCAL_REFLOW_AUTOMATION_PASS",
        "fixture": "SYNTHETIC_NO_CUSTOMER_DATA",
        "method": "Effective CSS viewport width; NOT actual browser zoom",
        "actualBrowserZoomVerified": False,
        "screenshotsIndependentlyReviewed": False,
        "screenReaderVerified": False,
        "independentWCAGConformance": False,
        "independentAppSecVerified": False,
        "hostedCIVerified": False,
        "productionApproved": False,
        "externalPublishingPerformed": False,
        "modelInferencePerformed": False,
        "cases": cases,
    }
    (out / "reflow-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    files = sorted(p for p in out.iterdir() if p.is_file())
    hashes = "".join(
        hashlib.sha256(p.read_bytes()).hexdigest() + "  ./" + p.name + "\n"
        for p in files
    )
    (out / "SHA256SUMS.txt").write_text(hashes, encoding="ascii")
    print("DEVELOPER_LOCAL_REFLOW_AUTOMATION_PASS")
    print("CSS widths 1280/640/390/360/320; synthetic workflow, no off-origin requests.")
    print("640 CSS px approximates 200% zoom at a nominal 1280px desktop; NOT actual zoom.")
    print(f"Artifacts (private, outside Git checkout): {out}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        help="NEW private directory outside repository; no overwrites")
    args = parser.parse_args()
    try:
        run(args.output_dir)
    except Exception as exc:
        print(f"REFLOW_AUTOMATION_BLOCKED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
