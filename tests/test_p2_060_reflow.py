"""P2-060d reflow source guards. Real CSS geometry is validated in Chromium."""
from pathlib import Path

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
