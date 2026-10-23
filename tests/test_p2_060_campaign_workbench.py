"""P2-060 source evidence and offline Node tests for locally processed campaigns."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "apps/site/campaigns/index.html"
ENGINE = ROOT / "apps/site/assets/campaign-engine.js"
UI = ROOT / "apps/site/assets/campaign-workbench.js"
CSS = ROOT / "apps/site/assets/campaign-workbench.css"


def test_all_workbench_components_exist():
    for file in (PAGE, ENGINE, UI, CSS, ROOT / "tests/campaign_engine.test.cjs"):
        assert file.is_file() and file.stat().st_size > 100


def test_local_only_hardened_page_and_brand_palette():
    page = PAGE.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    assert "connect-src 'none'" in page
    assert "script-src 'self'" in page
    for path in ("/assets/campaign-engine.js", "/assets/campaign-workbench.js",
                 "/assets/campaign-workbench.css"):
        assert path in page
    assert "No automatic publishing" in page
    assert "No server data retention" in page
    for color in ("#040D20", "#00A7ED", "#DCE6F1", "#EFB94F"):
        assert color in css
    assert 'name="viewport"' in page


def test_review_and_metrics_actions_are_fail_closed():
    ui = UI.read_text(encoding="utf-8")
    assert "if (!approval || !plan) return;" in ui
    assert "if (!approval)" in ui
    assert 'approval = metrics = null;' in ui
    assert 'state: "INTERNAL_DRAFT_REVIEW_RECORDED"' in ui
    assert "publishPerformed: false" in ui
    assert "aiModelUsed: false" in ui
    assert "providerMetricsVerified: false" in ui
    assert "navigator.clipboard.writeText" in ui
    assert "new Blob" in ui
    assert "toBlob" in ui
    for banned in ("fetch(", "XMLHttpRequest(", "localStorage.", "sessionStorage.",
                   "new WebSocket(", "eval("):
        assert banned not in ui


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not present; run source checks and execute node tests on a compatible machine")
def test_campaign_decision_engine_node_suite():
    run = subprocess.run(
        ["node", "--test", str(ROOT / "tests/campaign_engine.test.cjs")],
        cwd=ROOT, text=True, capture_output=True, timeout=30, check=False,
    )
    assert run.returncode == 0, run.stdout + "\n" + run.stderr
