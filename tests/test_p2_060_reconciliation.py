"""P2-060g offline source and Node regression gates.

Chromium, visual/WCAG, data authenticity and independent CI remain separate.
No network, real customer data, Docker, cloud services or financial claims.
"""
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "apps/site/campaigns/index.html"
DOMAIN = ROOT / "apps/site/assets/campaign-reconcile-engine.js"
UI = ROOT / "apps/site/assets/campaign-reconciliation.js"
CSS = ROOT / "apps/site/assets/campaign-workbench.css"
NODE = ROOT / "tests/campaign_reconciliation.test.cjs"
BROWSER = ROOT / "scripts/verify_campaign_reconciliation.py"


def test_reconciliation_files_and_strict_local_only_page():
    for filename in (PAGE, DOMAIN, UI, CSS, NODE, BROWSER):
        assert filename.is_file() and filename.stat().st_size > 250
    html = PAGE.read_text(encoding="utf-8")
    for script in (
        "/assets/campaign-engine.js",
        "/assets/campaign-reconcile-engine.js",
        "/assets/campaign-workbench.js",
        "/assets/campaign-reconciliation.js",
    ):
        assert html.count(script) == 1, script
    assert "connect-src 'none'" in html
    assert "script-src 'self'" in html
    assert "Stock" in html and "No automatic publishing" in html


def test_comparison_must_have_dated_snapshots_and_exact_ledger_periods():
    source = DOMAIN.read_text(encoding="utf-8")
    for required in (
        "campaign.DATED_HEADER.join",
        "const MOVEMENT_HEADER",
        "Stock observation interval must be 1 to 90",
        "Movement ledger dates do not cover exactly",
        "CURRENT_MAX_AGE_DAYS = 7",
        "Previous stock + received + customer returns",
        "MISSING_MOVEMENT_LEDGER",
        "INPUTS_NOT_COMPARABLE",
    ):
        assert required in source, required


def test_sales_conflicts_requires_same_reporting_window_and_complete_coverage():
    source = DOMAIN.read_text(encoding="utf-8")
    for required in (
        'c.salesCoverageStatus === "complete"',
        "c.salesPeriodStart === m.periodStart",
        "c.salesPeriodEnd === m.periodEnd",
        "daysBetween(m.periodStart, m.periodEnd) === 6",
        "salesComparable && c.weeklySales !== m.soldUnits",
        "ARITHMETIC_ONLY_SALES_NOT_COMPARABLE",
        "SALES_COUNT_CONFLICT",
    ):
        assert required in source, required


def test_no_false_zeros_for_new_or_missing_products():
    source = DOMAIN.read_text(encoding="utf-8")
    assert '"MISSING_CURRENT_SKU"' in source
    assert '"NEW_CURRENT_SKU"' in source
    assert "expectedStock: null, differenceUnits: null" in source
    assert "do not interpret as a sale or zero inventory" in source


def test_report_has_unverified_provenance_and_only_deterministic_data():
    source = DOMAIN.read_text(encoding="utf-8")
    for phrase in (
        'kind: "STOCK_SNAPSHOT_RECONCILIATION"',
        'classification: "USER_SUPPLIED_UNVERIFIED"',
        'sourceIntegrity: "UNAUTHENTICATED_USER_IMPORTS"',
        "sourceRecordsVerified: false",
        "businessRevenueVerified: false",
        "marketingAttributionVerified: false",
        "reportDigitallySigned: false",
        'return JSON.stringify(result, null, 2) + "\\n";',
    ):
        assert phrase in source, phrase
    for banned in ("fetch(", "XMLHttpRequest(", "localStorage.", "sessionStorage.",
                   "new WebSocket(", "eval("):
        assert banned not in source


def test_explicit_private_report_export_and_invalidation():
    html, ui = PAGE.read_text(encoding="utf-8"), UI.read_text(encoding="utf-8")
    for identifier in (
        "reconcile-previous", "reconcile-current", "reconcile-ledger",
        "reconcile-date", "reconcile-export", "reconcile-state",
        "reconcile-results", "reconcile-items",
    ):
        assert f'id="{identifier}"' in html, identifier
    for required in (
        "generation++;",
        'el("reconcile-export").disabled = true;',
        'el("reconcile-results").hidden = true;',
        'report = null;',
        'crypto.subtle.digest("SHA-256", data)',
        "authenticatesSources: false, digitallySigned: false",
        "reconcile(",
    ):
        assert required in ui, required
    for banned in ("fetch(", "XMLHttpRequest(", "localStorage.",
                   "sessionStorage.", "new WebSocket("):
        assert banned not in ui


def test_real_browser_proof_requires_same_origin_and_actual_sha256():
    src = BROWSER.read_text(encoding="utf-8")
    for required in (
        "serve_local()", "same_origin(route.request.url, base)",
        "launch_full_chromium(pw)", "DEVELOPER_LOCAL_RECONCILIATION_PASS",
        'wrapper["fingerprint"]["sha256"] == hashlib.sha256(',
        'rows["FAB-02"]["status"] == "STOCK_ARITHMETIC_CONFLICT"',
        'rows["SHOE-03"]["status"] == "SALES_COUNT_CONFLICT"',
        'rows["NEW-05"]["status"] == "NEW_CURRENT_SKU"',
        'expect(page.locator("#reconcile-export")).to_be_disabled()',
    ):
        assert required in src, required


@pytest.mark.skipif(shutil.which("node") is None,
                    reason="Node.js absent: use isolated Node on a compatible machine")
def test_offline_node_reconciliation_suite():
    result = subprocess.run(
        ["node", "--test", str(NODE)], cwd=ROOT, capture_output=True,
        text=True, timeout=40, check=False
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
