"""P2-060h: offline, source-only proof that source-byte hashing is wired.

Does not assert GitHub Actions CI, real browser, external data authenticity,
digital signatures or Qatar commercial readiness. Run separately on Kali.
"""
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "apps/site/campaigns/index.html"
PROOF = ROOT / "apps/site/assets/campaign-import-proof.js"
UI = ROOT / "apps/site/assets/campaign-reconciliation.js"
NODE = ROOT / "tests/campaign_import_proof.test.cjs"
BROWSER = ROOT / "scripts/verify_campaign_reconciliation.py"


def test_source_files_present_and_strict_browser_csp():
    for path in (PAGE, PROOF, UI, NODE, BROWSER):
        assert path.is_file() and path.stat().st_size > 100
    html = PAGE.read_text(encoding="utf-8")
    assert html.count('<script defer src="/assets/campaign-import-proof.js"></script>') == 1
    assert html.index('src="/assets/campaign-import-proof.js"') < html.index(
        'src="/assets/campaign-reconciliation.js"')
    assert "connect-src 'none'" in html
    assert "script-src 'self'" in html


def test_exact_import_bytes_are_hashed_and_strict_utf8_is_decoded():
    src = PROOF.read_text(encoding="utf-8")
    for token in (
        '["previous_snapshot", "current_snapshot", "movement_ledger"]',
        'bytes instanceof Uint8Array',
        'new TextDecoder("utf-8", { fatal: true })',
        'subtle.digest("SHA-256", bytes)',
        'byteLength: bytes.byteLength, sha256',
        'sourceAuthenticated: false',
        'consentVerified: false',
        'timestampAuthenticated: false',
        'includesOriginalFiles: false',
    ):
        assert token in src, token


def test_reconciliation_uses_the_same_bytes_it_fingerprints():
    src = UI.read_text(encoding="utf-8")
    for token in (
        'new Uint8Array(await file.arrayBuffer())',
        'proof.inspectInputs([',
        'texts.previous_snapshot, texts.current_snapshot, texts.movement_ledger',
        'reportManifest = inputManifest',
        'reportManifest = null',
        'proof.bindReport(manifest, current, crypto.subtle)',
        'inputManifest: manifest',
        'sourceBinding,',
        'reportManifest !== manifest',
    ):
        assert token in src, token


def test_report_provenance_does_not_claim_authentication_or_signing():
    src = PROOF.read_text(encoding="utf-8")
    html = PAGE.read_text(encoding="utf-8")
    for token in (
        'classification: "USER_SUPPLIED_UNVERIFIED"',
        'authenticatesSources: false',
        'digitallySigned: false',
        'independentSourceAuthentication: false',
        'canonicalBundle(inputManifest, payload)',
    ):
        assert token in src, token
    assert "cannot prove business authenticity" in html
    for forbidden in ("fetch(", "XMLHttpRequest", "localStorage", "sessionStorage",
                      "document.cookie", "WebSocket(", "provider.publish"):
        assert forbidden not in src


def test_chromium_acceptance_verifies_source_and_bundle_hashes():
    src = BROWSER.read_text(encoding="utf-8")
    for token in (
        'manifest = wrapper["inputManifest"]',
        'entry["byteLength"] == len(raw.encode("utf-8"))',
        'entry["sha256"] == hashlib.sha256(raw.encode("utf-8")).hexdigest()',
        'binding["sha256"] == hashlib.sha256(bundle.encode("utf-8")).hexdigest()',
        'expect(page.locator("#reconcile-export")).to_be_disabled()',
        'same_origin(route.request.url, base)',
    ):
        assert token in src, token


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required")
def test_import_proof_node_suite():
    result = subprocess.run(
        ["node", "--test", str(NODE)], cwd=ROOT,
        capture_output=True, text=True, timeout=40, check=False
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
