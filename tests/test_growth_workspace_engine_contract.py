"""Free-access read-only browser contract must agree with tested source engine."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.synthetic_growth_orchestration import build_committed_growth_work_plan  # noqa: E402

SNAPSHOT = ROOT / "apps/site/automation/engine-snapshot.js"
HTML = ROOT / "apps/site/automation/index.html"
JS = ROOT / "apps/site/automation/workspace.js"


def _read_contract():
    raw = SNAPSHOT.read_text(encoding="utf-8")
    prefix = "window.GrowthAutopilotPreviewData = Object.freeze("
    assert prefix in raw and raw.endswith(");\n")
    return json.loads(raw.split(prefix, 1)[1].rsplit(");\n", 1)[0])


def test_offline_contract_is_deterministic_exact_engine_projection():
    result = subprocess.run([
        sys.executable, str(ROOT / "scripts/build_growth_workspace_contract.py"), "--check"
    ], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    data = _read_contract()
    assert data["schema_version"] == 1
    assert data["access"] == "FREE_EXPLORER_NO_ACCOUNT"
    assert data["amounts"] == "ILLUSTRATIVE_NOT_LIVE_USD"
    assert set(data["workspaces"]) == {"academy_demo", "bespoke_demo"}
    for goal in ("CONTRIBUTION", "RETENTION", "COMPLETED_ORDERS"):
        backend = build_committed_growth_work_plan(goal=goal)
        for workspace in backend["workspaces"]:
            projected = data["workspaces"][workspace["workspace"]]["goals"][goal]
            economic = workspace["financial_summary"]
            m = projected["metrics"]
            assert m["gross_sales"] == economic["gross_sales"]
            assert m["variable_cost"] == economic["variable_cost"]
            assert m["marketing_spend"] == economic["marketing_spend"]
            assert m["modeled_contribution"] == economic["modeled_contribution_after_marketing"]
            assert m["repeat_orders"] == economic["repeat_orders"]
            assert m["contribution_target"] == economic["monthly_contribution_target"]
            assert {p["source_event"]: p["state"] for p in workspace["workflow_proposals"]} == {
                event: state["state"] for event, state in projected["decisions"].items()
            }
            assert all(v["state"] not in {"SENT", "APPROVED", "EXECUTED"}
                       for v in projected["decisions"].values())
            assert sum(v["state"] == "SUPPRESSED_PROVIDER_OWNS"
                       for v in projected["decisions"].values()) == 1
            assert sum(v["state"] == "SUPPRESSED_CONSENT_UNVERIFIED"
                       for v in projected["decisions"].values()) == 1


def test_no_account_payment_email_or_provider_writes_in_free_explorer():
    html = HTML.read_text(encoding="utf-8")
    javascript = JS.read_text(encoding="utf-8")
    snapshot = SNAPSHOT.read_text(encoding="utf-8")
    assert "Free to explore" in html
    assert "no account or card required" in html
    assert "no sign-in or payment" in html
    assert "Figures are illustrative" in html
    assert 'id="queue-deferred"' in html
    assert html.index("/automation/engine-snapshot.js") < html.index("/automation/workspace.js")
    assert "<form" not in html.lower()
    assert "$9/mo" not in html and "$29/mo" not in html
    assert "window.GrowthAutopilotPreviewData" in javascript
    assert "DEFERRED_NOT_GOAL_RELEVANT" in javascript
    assert "SUPPRESSED_NO_MARKETING_CONSENT" in javascript
    for token in ("fetch(", "XMLHttpRequest(", "WebSocket(", "localStorage.",
                  "sessionStorage.", "document.cookie", "sendBeacon(", "postMessage(",
                  "stripe", "paypal", "api.selar.com", "api.metricool.com"):
        assert token not in javascript and token not in snapshot, token
