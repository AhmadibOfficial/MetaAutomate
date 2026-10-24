"""P2-060d reflow source guards. Real CSS geometry is validated in Chromium."""
from pathlib import Path
import importlib.util
import pytest

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "apps/site/assets/campaign-workbench.css"
VERIFY = ROOT / "scripts/verify_campaign_reflow.py"


def test_narrow_form_columns_do_not_enforce_200px_minimum():
    css = CSS.read_text(encoding="utf-8")
    assert "@media(max-width:600px)" in css
    assert ".inline-form>.field{flex:1 1 100%;min-width:0}" in css
    assert "@media(max-width:360px)" in css
    assert ".field{min-width:0;flex-basis:100%}" in css
    assert ".media-grid,.three-fields{grid-template-columns:1fr}" in css


def test_actions_wrap_and_mobile_panels_fit_available_width():
    css = CSS.read_text(encoding="utf-8")
    assert ".inline-form>button{max-width:100%;white-space:normal" in css
    assert "button{width:100%;white-space:normal}" in css
    assert ".container{width:calc(100% - 24px)}" in css
    assert ".status{position:static}" in css
    assert "overflow-wrap:anywhere" in css


def test_new_gate_reuses_isolated_loopback_and_exact_origin_controls():
    source = VERIFY.read_text(encoding="utf-8")
    for required in (
        "ensure_playwright_driver()", "serve_local()",
        "launch_full_chromium(pw)", "same_origin(route.request.url, base)",
        'page.keyboard.press("Enter")', 'page.keyboard.press("Space")',
        "DEVELOPER_LOCAL_REFLOW_AUTOMATION_PASS",
        "NOT independent zoom",
    ):
        assert required in source, required
    for forbidden in ("requests.get(", "urlopen(", "fetch(", "subprocess.run("):
        assert forbidden not in source


def test_reflow_gate_covers_zoom_equivalent_and_narrow_css_widths():
    source = VERIFY.read_text(encoding="utf-8")
    assert "WIDTHS = (1280, 640, 390, 320, 256)" in source
    assert 'data["overflow"] <= data["w"] + 2' in source
    assert 'row["right"] <= width + 2' in source
    assert 'page.locator("#campaign-evidence").is_enabled()' in source
    assert "no off-origin requests" in source


# The real Chromium check and these fabricated geometry inputs use the
# same fail-closed rule. Source guards alone would miss a 19px checkbox bug.
def _reviewer():
    path = ROOT / "scripts/verify_campaign_reflow.py"
    spec = importlib.util.spec_from_file_location("campaign_reflow_guard", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _row(selector="#campaign-confirm", *, is_checkbox=True,
         width=19, height=19, label_width=200, label_height=28):
    return {
        "selector": selector, "hidden": False, "left": 32,
        "right": 32 + width, "width": width, "height": height,
        "isCheckbox": is_checkbox,
        "label": {
            "left": 30, "right": 30 + label_width,
            "width": label_width, "height": label_height
        } if is_checkbox else None
    }


def test_native_19px_checkbox_accepted_when_associated_label_is_clickable():
    reviewer = _reviewer()
    result = {"w": 390, "overflow": 390, "results": [_row()]}
    assert reviewer.validate_geometry_data(result, 390) is None


def test_small_checkbox_rejected_even_with_large_label():
    reviewer = _reviewer()
    result = {"w": 390, "overflow": 390,
              "results": [_row(width=12, height=12)]}
    with pytest.raises(AssertionError):
        reviewer.validate_geometry_data(result, 390)


def test_checkbox_without_visible_in_bounds_label_rejected():
    reviewer = _reviewer()
    row = _row(label_width=16)
    result = {"w": 390, "overflow": 390, "results": [row]}
    with pytest.raises(AssertionError):
        reviewer.validate_geometry_data(result, 390)
    row["label"] = None
    with pytest.raises(AssertionError):
        reviewer.validate_geometry_data(result, 390)


def test_regular_button_still_requires_minimum_geometry_and_no_overflow():
    reviewer = _reviewer()
    row = _row(selector="#campaign-authorize", is_checkbox=False)
    result = {"w": 390, "overflow": 390, "results": [row]}
    with pytest.raises(AssertionError):
        reviewer.validate_geometry_data(result, 390)
    row["width"] = row["height"] = 45
    row["right"] = 77
    assert reviewer.validate_geometry_data(result, 390) is None
    result["overflow"] = 402
    with pytest.raises(AssertionError):
        reviewer.validate_geometry_data(result, 390)
