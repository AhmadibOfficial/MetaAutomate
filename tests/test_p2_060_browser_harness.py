"""Source-only acceptance-harness safety tests; browser installation is optional.

No real business data, public server, cloud actions or production operations.
All HTTP requests in these tests target an ephemeral 127.0.0.1-only listener.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/verify_campaign_workbench_browser.py"
spec = importlib.util.spec_from_file_location("campaign_browser_harness", SCRIPT)
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)
opener = build_opener(ProxyHandler({}))


def response(url: str, *, method: str = "GET", host: str | None = None):
    headers = {"Host": host} if host else {}
    request = Request(url, method=method, headers=headers)
    try:
        with opener.open(request, timeout=5) as received:
            return received.status, received.read()
    except HTTPError as error:
        return error.code, error.read()


@pytest.fixture
def static_site(tmp_path):
    site = tmp_path / "site"
    (site / "campaigns").mkdir(parents=True)
    (site / "campaigns/index.html").write_text("<h1>synthetic site</h1>", encoding="utf-8")
    (site / "safe.txt").write_text("read-only local", encoding="utf-8")
    return site


def test_self_hosted_preview_only_binds_loopback_and_serves_static_files(static_site):
    with harness.serve_local(static_site) as url:
        assert url.startswith("http://127.0.0.1:")
        code, content = response(url + "/campaigns/")
        assert code == 200 and b"synthetic site" in content
        code, content = response(url + "/safe.txt")
        assert code == 200 and content == b"read-only local"


def test_static_server_denies_mutations_and_untrusted_host(static_site):
    with harness.serve_local(static_site) as url:
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            assert response(url + "/safe.txt", method=method)[0] == 405
        assert response(url + "/safe.txt", host="evil.example")[0] == 403


def test_static_server_denies_traversal_and_symlinked_files(static_site, tmp_path):
    outside = tmp_path / "outside-secret.txt"
    outside.write_text("not served", encoding="utf-8")
    (static_site / "escape.txt").symlink_to(outside)
    with harness.serve_local(static_site) as url:
        assert response(url + "/escape.txt")[0] == 403
        assert response(url + "/%2e%2e/outside-secret.txt")[0] == 403


def test_exact_origin_cannot_be_spoofed_by_url_prefix():
    base = "http://127.0.0.1:18321"
    assert harness.same_origin(base + "/campaigns/", base) is True
    for url in (
        "https://127.0.0.1:18321/campaigns/",
        "http://127.0.0.1:18322/campaigns/",
        "http://127.0.0.1.evil.example:18321/campaigns/",
        "http://localhost:18321/campaigns/",
        "data:text/html,hello",
        "http://127.0.0.1:invalid/campaigns/",
    ):
        assert harness.same_origin(url, base) is False


def test_evidence_output_is_new_private_directory_outside_checkout(tmp_path):
    destination = tmp_path / "new-browser-proof"
    result = harness.new_artifact_directory(destination)
    assert result == destination and result.is_dir()
    assert result.stat().st_mode & 0o077 == 0
    with pytest.raises(ValueError, match="NEW"):
        harness.new_artifact_directory(destination)
    assert result.is_dir()


def test_evidence_output_rejects_repo_paths_and_symlinks(tmp_path):
    with pytest.raises(ValueError, match="outside"):
        harness.new_artifact_directory(harness.ROOT / "artifacts" / "validation" / "no-create")
    target = tmp_path / "real-output"
    target.mkdir()
    alias = tmp_path / "symlink-output"
    alias.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        harness.new_artifact_directory(alias)
    assert not (harness.ROOT / "artifacts" / "validation" / "no-create").exists()


def test_site_symlink_is_rejected_before_network_bind(tmp_path):
    site = tmp_path / "site"
    site.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(site, target_is_directory=True)
    with pytest.raises(ValueError, match="non-symlink"):
        with harness.serve_local(alias):
            pass
