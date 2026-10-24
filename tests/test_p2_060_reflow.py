"""P2-060d CSS-width reflow regression guards (source-only, no browser needed)."""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "apps/site/assets/campaign-workbench.css"
UI = ROOT / "apps/site/assets/campaign-workbench.js"
PAGE = ROOT / "apps/site/campaigns/index.html"
SCRIPT = ROOT / "scripts/verify_campaign_reflow.py"

spec = importlib.util.spec_from_file_location("campaign_reflow", SCRIPT)
reflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reflow)


def test_zoom_width_equivalence_is_labeled_as_approximation():
    scenarios = {(case[0], case[1], case[2], case[3]) for case in reflow.CASES}
    assert ("zoom200-effective-640", 640, 360, "200%-layout-approximation") in scenarios
    assert ("reflow-320", 320, 640, "320-css-px-reflow") in scenarios
    assert {width for _, width, _, _ in scenarios} == {1280, 640, 390, 360, 320}


def test_box_overlap_logic_only_fails_on_actual_both_axis_intersection():
    first = {"left": 0, "right": 200, "top": 0, "bottom": 40}
    touching = {"left": 0, "right": 200, "top": 40, "bottom": 90}
    overlapping = {"left": 150, "right": 300, "top": 20, "bottom": 80}
    adjacent = {"left": 201, "right": 400, "top": 0, "bottom": 40}
    assert not reflow.box_overlap(first, touching)
    assert not reflow.box_overlap(first, adjacent)
    assert reflow.box_overlap(first, overlapping)


def test_narrow_css_reflows_fields_and_disables_obscuring_sticky_status():
    css = CSS.read_text(encoding="utf-8")
    assert ".field{display:flex;flex-direction:column;gap:7px;min-width:0;" in css
    assert "@media(max-width:760px)" in css
    assert ".status{position:static}" in css
    assert ".inline-form>.field{flex-basis:100%}" in css
    assert "@media(max-width:360px)" in css
    assert "overflow-wrap:anywhere" in css
    assert "button{max-width:100%;white-space:normal" in css


def test_source_keeps_brand_and_private_rules_only_workflow():
    page = PAGE.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    ui = UI.read_text(encoding="utf-8")
    assert "connect-src 'none'" in page
    assert "No automatic publishing" in page
    for color in ("#040D20", "#00A7ED", "#DCE6F1", "#EFB94F"):
        assert color in css
    assert "publishPerformed: false" in ui
    assert "aiModelUsed: false" in ui
    assert "providerMetricsVerified: false" in ui


def test_live_chromium_gate_is_synthetic_and_has_no_false_wcg_claims():
    source = SCRIPT.read_text(encoding="utf-8")
    ast.parse(source)
    for required in (
        "new_artifact_directory(output)",
        "ensure_playwright_driver()",
        "launch_full_chromium(pw)",
        "same_origin(route.request.url, base)",
        "page.screenshot(path=str(image_file), full_page=True)",
        "item.click(trial=True",
        "scrollWidth",
        "box_overlap(left, right)",
        "screenReaderVerified",
        '"actualBrowserZoomVerified": False',
        '"independentWCAGConformance": False',
        '"externalPublishingPerformed": False',
        "DEVELOPER_LOCAL_REFLOW_AUTOMATION_PASS",
    ):
        assert required in source, required
    for forbidden in ("requests.get(", "urllib.request", "subprocess.run(", "os.system("):
        assert forbidden not in source


def test_reflow_milestone_outputs_are_outside_repository_and_opt_in():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "new_artifact_directory" in source
    assert "new_artifact_directory(output)" in source
    assert "SHA256SUMS.txt" in source
    assert "REFLOW_AUTOMATION_BLOCKED" in source
    assert "No customer data" in source
