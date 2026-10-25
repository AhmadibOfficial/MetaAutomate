"""P2-060f source safeguards for dated, owner-supplied inventory evidence.

No network/browser needed for this file. Node and Chromium tests exercise
the actual engine and DOM independently in their respective gates.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "apps/site/assets/campaign-engine.js"
UI = ROOT / "apps/site/assets/campaign-workbench.js"
HTML = ROOT / "apps/site/campaigns/index.html"
NODE = ROOT / "tests/campaign_engine.test.cjs"
BROWSER = ROOT / "scripts/verify_campaign_temporal_evidence.py"


def test_three_exact_backward_compatible_inventory_schemas():
    source = ENGINE.read_text(encoding="utf-8")
    assert "const HEADER =" in source
    assert "const QUALITY_HEADER =" in source
    assert 'const DATED_HEADER = [...QUALITY_HEADER, "stock_observed_on"' in source
    assert "const dated = matches(DATED_HEADER);" in source
    assert "const enhanced = matches(QUALITY_HEADER) || dated;" in source
    assert "MAX_BYTES = 128000, MAX_ROWS = 400" in source


def test_exact_utc_calendar_dates_and_freshness_required_for_dated_rows():
    source = ENGINE.read_text(encoding="utf-8")
    for clause in (
        'Date.parse(value + "T00:00:00Z")',
        'new Date(time).toISOString().slice(0, 10) !== value',
        "const MAX_AGE_DAYS = 7;",
        "(endTime - startTime) / dayMs !== 6",
        "quality.inventoryAgeDays > MAX_AGE_DAYS",
        "quality.salesEndAgeDays > MAX_AGE_DAYS",
        "quality.inventoryAgeDays < 0",
        "quality.salesEndAgeDays < 0",
        'quality.issues.push("Partial dated fields are not accepted',
        'quality.mode = dated ? "DATED_SELF_DECLARED"',
        "quality.heldForReview = quality.issues.length > 0",
        "if (!item || !assess(item).signal.actionable)",
    ):
        assert clause in source, clause


def test_browser_presents_utc_reference_and_cautious_legacy_labels():
    html = HTML.read_text(encoding="utf-8")
    js = UI.read_text(encoding="utf-8")
    assert "stock_observed_on,sales_period_start,sales_period_end" in html
    assert 'id="campaign-date-note"' in html
    assert 'el("campaign-date-note").textContent' in js
    assert "results.datedCount" in js
    assert "results.undatedCount" in js
    assert '"USER_SUPPLIED_UNVERIFIED"' in js
    assert '"Legacy unconfirmed inputs"' in js
    assert "Dates, completeness and counts are self-declared" in ENGINE.read_text(encoding="utf-8")


def test_local_decision_trace_has_date_and_provenance_without_public_upload():
    ui = UI.read_text(encoding="utf-8")
    for part in (
        "asOfDate: results.asOfDate",
        "datedCount: results.datedCount",
        "undatedCount: results.undatedCount",
        "stockObservedOn: item.stockObservedOn ?? null",
        "salesPeriodStart: item.salesPeriodStart ?? null",
        "salesPeriodEnd: item.salesPeriodEnd ?? null",
        "inventoryIndependentlyVerified: false",
        "financialPerformanceVerified: false",
        "inputQuality: plan.inputQuality",
        "engine.DATED_HEADER.join",
    ):
        assert part in ui, part
    for forbidden in ("fetch(", "XMLHttpRequest(", "localStorage.",
                      "sessionStorage.", "new WebSocket(", "eval("):
        assert forbidden not in ui


def test_browser_gate_reuses_no_egress_full_chromium_and_old_format():
    src = BROWSER.read_text(encoding="utf-8")
    for token in (
        "serve_local()", "same_origin(route.request.url, base)",
        "launch_full_chromium(pw)", "ensure_playwright_driver()",
        'assert trace["asOfDate"] == assessment_date',
        'assert (trace["datedCount"], trace["undatedCount"]) == (5, 0)',
        'assert legacy["datedCount"] == 0',
        'assert evidence["safeguards"]["publishPerformed"] is False',
        "DEVELOPER_LOCAL_TEMPORAL_EVIDENCE_PASS",
    ):
        assert token in src, token
    for forbidden in ("requests.get(", "urllib.request.urlopen(", "fetch("):
        assert forbidden not in src


def test_node_suite_exercises_invalid_dates_and_direct_bypass_attempts():
    source = NODE.read_text(encoding="utf-8")
    for label in (
        "dated rows use exactly seven calendar dates",
        "stale stock or sales observation is held",
        "future inventory and sales dates fail closed",
        "invalid dates and incomplete 8 or 9 column CSV",
        "direct engine callers cannot bypass missing date fields",
        "current dated campaigns disclose declared inputs",
    ):
        assert label in source, label


def test_changing_campaign_settings_revokes_review_without_erasing_inventory_basis():
    source = UI.read_text(encoding="utf-8")
    assert 'function resetDownstream({ preserveQuality = false } = {})' in source
    assert 'if (!preserveQuality) {' in source
    assert 'resetDownstream({ preserveQuality: true });' in source
    assert 'el("campaign-evidence").disabled = true;' in source
    assert 'el("campaign-quality-export").disabled = true;' in source
    browser = BROWSER.read_text(encoding="utf-8")
    assert 'page.locator("#campaign-channel").select_option("TikTok")' in browser
    assert 'assert retained["heldCount"] == 3' in browser
