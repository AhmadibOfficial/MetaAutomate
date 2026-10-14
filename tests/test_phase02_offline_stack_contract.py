"""P2-04e pinned four-PR source-conformance catalog safety tests.

These check local contract rules in ordinary CI. The full cross-PR suite is an
optional *manual offline* Kali test, because CI's main-based checkout does not
contain private unmerged PR commit objects.
"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify_p2_04e_offline_stack.py"
MANIFEST = ROOT / "contracts/engineering/p2_04e_offline_sources.json"

spec = importlib.util.spec_from_file_location("p204e_offline", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture
def catalog():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_exact_four_locked_source_heads(catalog):
    rows = module.validate_contract(catalog)
    assert len(rows) == 4
    assert [pr for pr, _, _, _ in rows] == [32, 33, 34, 35]
    assert all(len(sha) == 40 for _, sha, _, _ in rows)
    assert len({path for _, _, path, _ in rows}) == 4
    assert len({path for _, _, _, path in rows}) == 4


@pytest.mark.parametrize("field,value", [
    ("source_only", False),
    ("requires_independent_review", False),
    ("merge_permitted", True),
    ("live_execution_permitted", True),
    ("phase01_verified_gates", 9),
    ("phase01_total_gates", 3),
    ("schema", "live"),
])
def test_false_release_claims_fail_closed(catalog, field, value):
    modified = deepcopy(catalog)
    modified[field] = value
    with pytest.raises(module.ConformanceError):
        module.validate_contract(modified)


@pytest.mark.parametrize("change", [
    lambda d: d["entries"].pop(),
    lambda d: d["entries"].append(d["entries"][0]),
    lambda d: d["entries"][1].update(sha="0" * 40),
    lambda d: d["entries"][2].update(module="../secrets/private.py"),
    lambda d: d["entries"][3].update(test="tests/other.py"),
    lambda d: d["entries"][0].update(pr=33),
    lambda d: d["entries"][0].update(pr=True),
    lambda d: d["base"].update(sha="0" * 40),
    lambda d: d.update(execution_authorized=True),
])
def test_manifest_paths_shas_and_extra_privileges_rejected(catalog, change):
    changed = deepcopy(catalog)
    change(changed)
    with pytest.raises(module.ConformanceError):
        module.validate_contract(changed)


def test_offline_check_only_reads_pinned_sources_without_execution(
    catalog, monkeypatch, capsys
):
    seen = []
    def fake_show(repo, sha, path):
        seen.append((sha, path))
        return b"# synthetic offline fixture only"
    monkeypatch.setattr(module, "_show", fake_show)
    assert module.run_offline(ROOT, check_only=True) == 0
    assert len(seen) == 9
    assert seen[0] == (
        "7144451b0ac37349c3e731bac76d14338280c42e",
        "apps/api/app/main.py",
    )
    assert "tests not executed" in capsys.readouterr().out


def test_api_import_boundary_must_remain_unwired(monkeypatch):
    def fake_show(repo, sha, path):
        if path == "apps/api/app/main.py":
            return b"from app.synthetic_delivery import SyntheticDeliveryRehearsal"
        return b"# demo"
    monkeypatch.setattr(module, "_show", fake_show)
    with pytest.raises(module.ConformanceError, match="API wiring"):
        module.run_offline(ROOT, check_only=True)


def test_full_overlay_requires_local_git_objects():
    assert "git" in SCRIPT.read_text()
    assert "show" in SCRIPT.read_text()
    assert "TemporaryDirectory" in SCRIPT.read_text()
    assert "pytest" in SCRIPT.read_text()
    assert "git merge" in SCRIPT.read_text()  # documented prohibition
    assert "http://" not in SCRIPT.read_text()
    assert "https://" not in SCRIPT.read_text()


def test_pinned_source_modules_are_not_imported_by_current_main():
    main = (ROOT / "apps/api/app/main.py").read_text(encoding="utf-8")
    for _, (_, module_path, _) in module.PINNED.items():
        assert Path(module_path).stem not in main
