"""P2-062: offline source and security guards for unified workspace preview."""
from __future__ import annotations

import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "apps/site/workspace/index.html"
JS = ROOT / "apps/site/assets/unified-workspace.js"
CSS = ROOT / "apps/site/assets/unified-workspace.css"
ENGINE = ROOT / "apps/site/assets/campaign-engine.js"


class Elements(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.scripts: list[dict[str, str]] = []
        self.forms: list[dict[str, str]] = []
        self.routes: list[tuple[str, str]] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            assert a["id"] not in self.ids, "duplicate ID: " + a["id"]
            self.ids.add(a["id"])
        if tag == "a":
            self.links.append(a.get("href", ""))
            if "data-route" in a:
                self.routes.append((a["data-route"], a.get("href", "")))
        if tag == "script":
            self.scripts.append(a)
        if tag == "form":
            self.forms.append(a)


@pytest.fixture(scope="module")
def page_source():
    assert all(p.is_file() and p.stat().st_size > 100 for p in (HTML, JS, CSS, ENGINE))
    return HTML.read_text("utf-8"), JS.read_text("utf-8"), CSS.read_text("utf-8")


def test_linked_files_and_no_inline_executable_code(page_source):
    html, js, css = page_source
    parser = Elements()
    parser.feed(html)
    assert len(parser.ids) > 35
    assert len(parser.ids) == len(set(parser.ids))
    assert {s.get("src") for s in parser.scripts} == {
        "/assets/campaign-engine.js", "/assets/unified-workspace.js"
    }
    assert all("src" in s and "onload" not in s for s in parser.scripts)
    assert "/assets/unified-workspace.css" in html
    assert "connect-src 'none'" in html
    assert "form-action 'none'" in html
    assert "frame-src 'none'" in html
    assert "Content-Security-Policy" in html
    for color in ("#040d20", "#00a7ed", "#dce6f1", "#efb94f"):
        assert color in css.lower()


def test_all_view_routes_and_dom_selectors_resolve(page_source):
    html, js, _ = page_source
    parser = Elements()
    parser.feed(html)
    views = {"overview", "inventory", "campaign", "evidence", "modules", "readiness"}
    for name in views:
        assert "view-" + name in parser.ids
        assert (name, "#" + name) in parser.routes
    js_ids = set(re.findall(r'\$\("([a-z0-9-]+)"\)', js))
    assert js_ids <= parser.ids, f"JS references missing HTML IDs: {sorted(js_ids - parser.ids)}"
    for route, href in parser.routes:
        assert route in views and href == "#" + route
    assert all("action=" not in form and "method=" not in form for form in parser.forms)


def test_no_network_persistence_or_unreviewed_draft_export(page_source):
    html, js, _ = page_source
    for dangerous in ("fetch(", "XMLHttpRequest", "WebSocket(", "localStorage",
                      "sessionStorage", ".innerHTML", "eval(", "new Function("):
        assert dangerous not in js, dangerous
    for necessary in ('TextDecoder("utf-8", { fatal: true })', "engine.parseCSV(csv)",
                      "engine.analyze(parsed)", "engine.makeCampaign(",
                      "if (!approved || !plan) return;", "function revokeApproval()",
                      "thirdPartySourceAuthenticated: false", "aiModelUsed: false",
                      "independentlyVerified: false", "signed: false"):
        assert necessary in js, necessary
    assert "No publication" in html or "No automatic" in html or "nothing is published" in html
    assert "Subscriptions" in html or "subscriptions" in html


def test_inflight_file_reads_cannot_restore_stale_approvals(page_source):
    _, js, _ = page_source
    assert "let importGeneration = 0" in js
    assert "importGeneration++;" in js
    assert "const generation = ++importGeneration;" in js
    assert js.count('generation !== importGeneration || $("inventory-file").files?.[0] !== file') == 2
    assert "resetPlan();" in js


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js unavailable")
def test_workspace_js_syntax_and_reused_campaign_engine():
    for path in (JS, ENGINE):
        result = subprocess.run(["node", "--check", str(path)],
                                cwd=ROOT, capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stdout + result.stderr
    result = subprocess.run(
        ["node", "--test", str(ROOT / "tests/campaign_engine.test.cjs")],
        cwd=ROOT, capture_output=True, text=True, timeout=40
    )
    assert result.returncode == 0, result.stdout + result.stderr
