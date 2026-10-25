"""P2-060e source guards for honest inventory decisions and quality disclosure.

Pure source checks only; detailed decision regression cases are in the Node
suite and end-to-end behavior requires running real Chromium separately.
"""
from pathlib import Path
import subprocess
import shutil
import pytest

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "apps/site/assets/campaign-engine.js"
UI = ROOT / "apps/site/assets/campaign-workbench.js"
HTML = ROOT / "apps/site/campaigns/index.html"
BROWSER = ROOT / "scripts/verify_campaign_inventory_quality.py"


def test_quality_columns_are_optional_exact_and_user_supplied():
    source = ENGINE.read_text(encoding="utf-8")
    for snippet in (
        '"stock_count_status", "sales_coverage_status"',
        'const dated = matches(DATED_HEADER);',
        'const enhanced = matches(QUALITY_HEADER) || dated;',
        'if (!matches(HEADER) && !enhanced)',
        'incompleteDates ? "DATED_INCOMPLETE" : "SELF_DECLARED"',
        'quality.heldForReview = quality.issues.length > 0',
        'underlyingSignal: candidate.code',
        'quality.mode === "LEGACY_UNATTESTED"',
        '"USER_SUPPLIED_UNVERIFIED"',
    ):
        assert snippet in source, snippet


def test_cannot_bypass_quality_hold_when_creating_campaign():
    source = ENGINE.read_text(encoding="utf-8")
    assert "if (!item || !assess(item).signal.actionable)" in source
    assert 'fail("Choose an eligible in-stock product with sufficient user-supplied data")' in source


def test_quality_summary_and_holds_are_visible_to_user():
    markup = HTML.read_text(encoding="utf-8")
    js = UI.read_text(encoding="utf-8")
    for identifier in ("campaign-quality-note", "campaign-quality-held",
                       "campaign-quality-held-items", "campaign-quality-export"):
        assert f'id="{identifier}"' in markup
        assert f'el("{identifier}")' in js
    assert "Data quality has not yet been assessed." in markup
    assert 'results.held.forEach(item => text(heldList, "li"' in js
    assert 'results.legacyCount + " legacy row(s)' in js


def test_inventory_trace_is_explicit_and_discloses_missing_verification():
    markup = HTML.read_text(encoding="utf-8")
    js = UI.read_text(encoding="utf-8")
    assert "Download inventory decision trace (unverified)" in markup
    assert 'kind: "INVENTORY_DECISION_TRACE"' in js
    assert 'classification: "USER_SUPPLIED_UNVERIFIED"' in js
    assert 'inventoryIndependentlyVerified: false' in js
    assert 'financialPerformanceVerified: false' in js
    assert 'approval, metrics, events: audit.slice()' in js
    assert 'inputQuality: plan.inputQuality' in js
    assert 'el("campaign-quality-export").addEventListener("click"' in js
    for forbidden in ("fetch(", "XMLHttpRequest(", "localStorage.",
                      "sessionStorage.", "new WebSocket(", "eval("):
        assert forbidden not in js


def test_browser_quality_proof_reuses_exact_origin_local_server():
    source = BROWSER.read_text(encoding="utf-8")
    for required in (
        "serve_local()", "same_origin(route.request.url, base)",
        "launch_full_chromium(pw)", "DEVELOPER_LOCAL_INVENTORY_QUALITY_PASS",
        '"kind"] == "INVENTORY_DECISION_TRACE"',
        'assert trace["heldCount"] == 1',
        'assert old["legacyCount"] == 3',
        'assert evidence["safeguards"]["publishPerformed"] is False'
    ):
        assert required in source
    for forbidden in ("requests.get(", "urllib.request.urlopen(", "fetch(", "social_publish("):
        assert forbidden not in source


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js absent: run JS engine tests elsewhere")
def test_node_quality_decisions_and_backward_compatibility():
    result = subprocess.run(
        ["node", "--test", str(ROOT / "tests/campaign_engine.test.cjs")],
        cwd=ROOT, capture_output=True, text=True, timeout=45, check=False
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr


def test_campaign_audit_events_are_isolated_per_import_and_per_new_draft():
    source = UI.read_text(encoding="utf-8")
    assert 'audit.length = 0;' in source
    assert 'audit.splice(1);' in source
    assert 'recordEvent("Inventory CSV imported: " + records.length + " items")' in source
    assert 'recordEvent("Campaign draft prepared for " + plan.sku)' in source
