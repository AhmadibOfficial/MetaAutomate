"""P2-04u operator evidence admission must not accept unpinned or unsafe JSON."""
import json
import subprocess
import pytest

from app.creative_multimodal_studio import StudioHold
from app import creative_multimodal_operator as operator

def test_private_source_json_requires_owner_only_permission(tmp_path):
    path=tmp_path/"evidence.json"
    path.write_text("{}")
    path.chmod(0o644)
    with pytest.raises(StudioHold,match="Private absolute"):
        operator._read_private_json(path)

def test_duplicate_json_keys_are_rejected(tmp_path):
    path=tmp_path/"evidence.json"
    path.write_text('{"source":1,"source":2}')
    path.chmod(0o600)
    with pytest.raises(StudioHold,match="Duplicate key"):
        operator._read_private_json(path)

def test_nonfinite_numbers_rejected(tmp_path):
    path=tmp_path/"evidence.json"
    path.write_text('{"output":NaN}')
    path.chmod(0o600)
    with pytest.raises(StudioHold,match="Nonfinite"):
        operator._read_private_json(path)

def test_not_a_json_mapping_rejected(tmp_path):
    path=tmp_path/"evidence.json"
    path.write_text('["invalid"]')
    path.chmod(0o600)
    with pytest.raises(StudioHold,match="JSON object"):
        operator._read_private_json(path)

def test_unpinned_checkout_fails_closed(tmp_path):
    with pytest.raises(StudioHold,match="Exact clean"):
        operator._pinned_checkout(tmp_path,"anything")

def test_actual_git_head_is_checked(tmp_path):
    repo=tmp_path/"repo"
    repo.mkdir()
    def git(*args):
        return subprocess.check_output(["git","-C",str(repo),*args],text=True).strip()
    git("init","-q")
    git("config","user.name","Fixture Tester")
    git("config","user.email","fixture@example.invalid")
    file=repo/"README.md"
    file.write_text("A synthetic test repository, no AI models")
    git("add",".")
    git("commit","-qm","source fixture")
    head=git("rev-parse","HEAD")
    operator._pinned_checkout(repo,head)
    with pytest.raises(StudioHold,match="differs"):
        operator._pinned_checkout(repo,"0"*40)
    file.write_text("Modified tracked source")
    with pytest.raises(StudioHold,match="differs"):
        operator._pinned_checkout(repo,head)

def test_real_render_never_starts_without_verified_source(monkeypatch,tmp_path,capsys):
    repo=tmp_path/"repo"
    repo.mkdir()
    def git(*args):
        return subprocess.check_output(["git","-C",str(repo),*args],text=True).strip()
    git("init","-q")
    git("config","user.name","Fixture Tester")
    git("config","user.email","fixture@example.invalid")
    (repo/"README.md").write_text("fixture")
    git("add",".")
    git("commit","-qm","fixture")
    private=tmp_path/"private"
    private.mkdir(mode=0o700)
    def data(name,value):
        path=private/name
        path.write_text(json.dumps(value))
        path.chmod(0o600)
        return path
    manifest=data("manifest.json",{"no":"actual project"})
    evidence=data("sources.json",{"source":"missing"})
    keys=data("keys.json",{})
    def blocked(*args,**kwargs):
        raise StudioHold("No independently verified media sources")
    monkeypatch.setattr(operator,"render_with_source_proofs",blocked)
    result=operator.main([
        "--repo-root",str(repo),
        "--expected-commit",git("rev-parse","HEAD"),
        "--manifest",str(manifest),"--source-evidence",str(evidence),
        "--trusted-reviewer-keys",str(keys),
        "--assets",str(private),"--quarantine",str(private),"--render",
    ])
    assert result==2
    assert "MULTIMODAL PRODUCTION HOLD" in capsys.readouterr().err
