#!/usr/bin/env python3
"""P2-060 local Chromium evidence: synthetic data, no provider or production calls.

Starts an ephemeral loopback-only static server and keeps downloaded artifacts
in a new private directory outside the repository. This is developer-local
acceptance, NOT an independent CI, real customer or release approval.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import tempfile
from threading import Thread
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "apps/site"
CSV = ("sku,name,stock,weekly_sales,unit_price_kobo\n"
       "CAP-01,Branded Cap,18,0,850000\n"
       "FAB-02,Classic Kaftan,24,3,3500000\n"
       "SHOE-03,Low Stock Shoes,1,5,1400000\n")
VIEWPORTS = (("desktop", 1440), ("mobile", 390), ("small", 360))


class ReadOnlySiteHandler(SimpleHTTPRequestHandler):
    """Deny other Hosts, HTTP mutations, traversal and filesystem symlinks."""

    def send_head(self):
        if self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}":
            self.send_error(403, "Unexpected local Host")
            return None
        raw_path = unquote(urlsplit(self.path).path)
        if ".." in raw_path.split("/") or "\x00" in raw_path or "\\" in raw_path:
            self.send_error(403, "Unsafe static path")
            return None
        root = Path(self.directory).resolve()
        candidate = Path(super().translate_path(self.path))
        if not candidate.resolve(strict=False).is_relative_to(root):
            self.send_error(403, "Static path escapes site")
            return None
        current = candidate
        while current != root:
            if current.is_symlink():
                self.send_error(403, "Symlinked static path")
                return None
            current = current.parent
        return super().send_head()

    def do_POST(self):
        self.send_error(405, "Read-only static preview")

    do_PUT = do_POST
    do_PATCH = do_POST
    do_DELETE = do_POST

    def log_message(self, _format, *_args):
        # No inventory, query strings or private fixtures in server logs.
        pass


@contextmanager
def serve_local(site: Path = SITE):
    site = site.absolute()
    if site.is_symlink() or not site.is_dir():
        raise ValueError("Expected a local non-symlink site directory")
    handler = partial(ReadOnlySiteHandler, directory=str(site))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    thread = Thread(target=server.serve_forever, name="meta-campaign-preview", daemon=True)
    try:
        thread.start()
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        if thread.is_alive():
            thread.join(timeout=5)


def same_origin(url: str, base: str) -> bool:
    try:
        actual, expected = urlsplit(url), urlsplit(base)
        return (actual.scheme, actual.hostname, actual.port) == (
            expected.scheme, expected.hostname, expected.port
        ) and actual.scheme == "http" and actual.hostname == "127.0.0.1"
    except ValueError:
        return False


def new_artifact_directory(requested: Path | None = None) -> Path:
    if requested is None:
        return Path(tempfile.mkdtemp(prefix="meta-campaign-browser-"))
    destination = requested.expanduser().absolute()
    if destination.resolve(strict=False).is_relative_to(ROOT.resolve()):
        raise ValueError("Browser proof output must remain outside the Git repository")
    if destination.exists() or destination.is_symlink() or not destination.parent.is_dir():
        raise ValueError("Choose a NEW directory with an existing parent; no overwrite or symlink")
    destination.mkdir(mode=0o700)
    return destination


def require_playwright_driver(cli_path: Path) -> None:
    """Check the Node CLI entrypoint without starting subprocesses or listeners.

    Some Debian/Kali python3-playwright packages import successfully while
    the separately packaged Node driver is absent. Detect that failure before
    calling sync_playwright(), which otherwise emits misleading async errors.
    """
    if not cli_path.is_file():
        raise RuntimeError(
            "Playwright Node driver missing: " + str(cli_path) +
            ". Browser acceptance NOT RUN. Use an isolated Python venv with "
            "the official playwright wheel and its matching Chromium; "
            "do not repair this by changing system Python or GitHub CI."
        )


def ensure_playwright_driver() -> None:
    try:
        from playwright._impl._driver import compute_driver_executable
    except ImportError as exc:
        raise RuntimeError(
            "Playwright Node driver metadata unavailable; browser acceptance NOT RUN. "
            "Use an isolated venv with the official playwright wheel."
        ) from exc
    _node_path, cli_path = compute_driver_executable()
    require_playwright_driver(Path(cli_path))


def run(requested_output: Path | None = None) -> Path:
    # Fail before importing the sync API or opening a socket. This also makes
    # the negative preflight test independent of Playwright being installed.
    ensure_playwright_driver()
    try:
        from playwright.sync_api import sync_playwright, expect
    except ImportError as exc:
        raise RuntimeError("Playwright Python package is missing; browser acceptance NOT RUN") from exc

    with serve_local() as base, sync_playwright() as playwright:
        # A missing Chromium installation must fail instead of inventing proof.
        browser = playwright.chromium.launch(headless=True)
        try:
            out = new_artifact_directory(requested_output)
            for label, width in VIEWPORTS:
                errors, external_requests = [], []
                context = browser.new_context(
                    viewport={"width": width, "height": 900},
                    accept_downloads=True, reduced_motion="reduce",
                    service_workers="block")
                try:
                    def restrict(route):
                        if same_origin(route.request.url, base):
                            route.continue_()
                        else:
                            external_requests.append(route.request.url)
                            route.abort()
                    context.route("**/*", restrict)
                    page = context.new_page()
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.on("request", lambda request: external_requests.append(request.url)
                            if not same_origin(request.url, base) else None)
                    res = page.goto(base + "/campaigns/", wait_until="networkidle")
                    assert res is not None and res.status == 200
                    expect(page.get_by_role("heading", name="Work with your own stock records.")).to_be_visible()
                    page.locator("#campaign-file").set_input_files({
                        "name": "synthetic-inventory.csv", "mimeType": "text/csv",
                        "buffer": CSV.encode("utf-8")
                    })
                    page.locator("#campaign-import button[type=submit]").click()
                    expect(page.locator("#campaign-count")).to_have_text("3")
                    expect(page.locator("#campaign-flagged")).to_have_text("2")
                    expect(page.locator("#campaign-results")).to_be_visible()
                    assert page.locator('input[name="candidate"]').count() == 2
                    page.locator("#campaign-brand").fill("Synthetic MetaAutomate Shop")
                    page.locator("#campaign-create").click()
                    expect(page.locator("#campaign-project")).to_be_visible()
                    expect(page.locator("#campaign-post")).to_have_value(re.compile("Branded Cap"))
                    expect(page.locator("#campaign-approval")).to_be_visible()
                    assert page.locator("#campaign-copy").is_disabled()
                    expect(page.locator("#campaign-canvas")).to_have_attribute("width", "1080")
                    with page.expect_download() as download_info:
                        page.locator("#campaign-png").click()
                    png = download_info.value
                    assert png.suggested_filename.endswith(".png")
                    png.save_as(out / f"campaign-{label}.png")
                    assert (out / f"campaign-{label}.png").stat().st_size > 5000
                    with page.expect_download() as download_info:
                        page.locator("#campaign-video-download").click()
                    brief = download_info.value
                    assert brief.suggested_filename.endswith(".txt")
                    brief.save_as(out / f"video-brief-{label}.txt")
                    assert (out / f"video-brief-{label}.txt").stat().st_size > 100
                    assert page.locator('a[href="/creative/#instant-video"]').count() == 1
                    page.locator("#campaign-confirm").check()
                    page.locator("#campaign-authorize").click()
                    expect(page.locator("#campaign-approval-state")).to_contain_text("Internal draft review recorded")
                    assert page.locator("#campaign-copy").is_enabled()
                    page.locator("#campaign-post").fill("Changed synthetic draft; review required.")
                    assert page.locator("#campaign-copy").is_disabled()
                    page.locator("#campaign-confirm").check()
                    page.locator("#campaign-authorize").click()
                    page.locator("#campaign-impressions").fill("100")
                    page.locator("#campaign-clicks").fill("20")
                    page.locator("#campaign-orders").fill("3")
                    page.locator("#campaign-metric-source").fill("Synthetic example only, no external campaign")
                    page.locator("#campaign-metric-form button[type=submit]").click()
                    expect(page.locator("#campaign-metrics-result")).to_contain_text("Self-reported")
                    with page.expect_download() as download_info:
                        page.locator("#campaign-evidence").click()
                    evidence = download_info.value
                    path = out / f"campaign-evidence-{label}.json"
                    evidence.save_as(path)
                    report = json.loads(path.read_text(encoding="utf-8"))
                    assert report["safeguards"]["publishPerformed"] is False
                    assert report["safeguards"]["aiModelUsed"] is False
                    assert report["metrics"]["evidence"] == "SELF_REPORTED_NOT_INDEPENDENTLY_VERIFIED"
                    assert report["approval"]["scope"] == "COPY_OR_DOWNLOAD_ONLY"
                    dims = page.evaluate("() => ({width: innerWidth, scroll: document.documentElement.scrollWidth})")
                    assert dims["scroll"] <= dims["width"] + 2, dims
                    page.screenshot(path=str(out / f"campaign-workbench-{label}.png"), full_page=True)
                    assert not errors, errors
                    assert not external_requests, external_requests
                finally:
                    context.close()
        finally:
            browser.close()
    print("DEVELOPER_LOCAL_BROWSER_PASS: synthetic import -> prioritization -> PNG/brief -> review -> metrics")
    print("Checked 1440/390/360px; no off-origin requests or external publishing.")
    print(f"Artifacts (private, outside Git checkout): {out}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, help="NEW private directory outside the repository")
    args = parser.parse_args()
    try:
        run(args.output_dir)
        return 0
    except (RuntimeError, ValueError, AssertionError, OSError) as exc:
        print(f"BROWSER_ACCEPTANCE_BLOCKED: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
