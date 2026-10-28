"""Source-level checks for P2-064 interactive cross-industry workspace.

These checks validate committed UI source contracts only; they do not prove
real Chromium execution, AI inference, live integrations or production security.
"""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "apps/site"
HTML = (SITE / "workspace/index.html").read_text("utf-8")
JS = (SITE / "assets/unified-workspace.js").read_text("utf-8")
CSS = (SITE / "assets/unified-workspace.css").read_text("utf-8")
CATALOG = json.loads((ROOT / "contracts/domains/v2/domain-packs.v1.json").read_text("utf-8"))
HOME = (SITE / "index.html").read_text("utf-8")


def test_five_interactive_objectives_and_state_controls():
    assert len(re.findall(r'<button[^>]*data-goal="[^"]+"', HTML)) == 5
    for key in ("customer", "operations", "finance", "automation", "insights"):
        assert 'data-goal="' + key + '"' in HTML
        assert '"' + key + '":' in JS
    assert 'id="more-industries"' in HTML
    assert 'aria-pressed' in HTML and 'aria-pressed' in JS
    assert 'selectedGoal' in JS
    assert 'objectiveFamilies[selectedGoal].steps.map' in JS


def test_all_catalog_sectors_covered_without_backend_activation():
    for pack in CATALOG["profiles"]:
        assert pack["enabled"] is False
        assert pack["production_ready"] is False
        if pack["id"] not in {
            "sales_customer_service", "healthcare_administration",
            "real_estate", "retail", "cloud_it",
        }:
            assert '<option value="' + pack["id"] + '">' in HTML
            assert '"' + pack["id"] + '"' in JS
    assert "Object.assign(industries, extraIndustries)" in JS
    assert len(re.findall(r'<button[^>]*data-sector="', HTML)) == 5
    assert len(re.findall(r'<option value="[^"]+"', HTML)) >= 17


def test_review_and_local_only_trust_boundaries_intact():
    assert "connect-src 'none'" in HTML
    assert 'id="complete-plan" disabled' in HTML
    assert "plan.steps.every(step=>step.done)" in JS
    assert "plan.reviewed=true" in JS
    assert "outsideActionsPerformed:false" in JS
    assert "aiModelUsed:false" in JS
    assert 'id="clear-session"' in HTML
    assert "No live AI, customer accounts or external integrations" in HTML
    assert "Customer experience" in HTML
    assert "Business operations" in HTML
    assert "Intelligent automation" in HTML
    assert "Every industry. One simple starting point." in HOME


def test_brand_design_responsive_and_accessible():
    for token in ("--navy:", "--blue:", "--gold:", "--silver:"):
        assert token in CSS
    assert ".goal-card[aria-pressed=true]" in CSS
    assert ".sector-extend" in CSS
    assert "prefers-reduced-motion:reduce" in CSS
    assert 'aria-label="Choose an objective"' in HTML
    ids = re.findall(r'\bid="([^"]+)"', HTML)
    assert len(ids) == len(set(ids))
