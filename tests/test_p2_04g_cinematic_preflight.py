"""P2-04g fail-closed cinematic preflight tests (no film render)."""
import hashlib
import pytest
from app.creative_cinematic_preflight import preflight, CinematicHold

def fixture(tmp_path):
    root=tmp_path/"media"
    root.mkdir()
    tracks=[]
    for role,filename in (("narration","voice.wav"),("music","score.wav"),("captions","titles.srt")):
        data=(role*10).encode()
        (root/filename).write_bytes(data)
        tracks.append(dict(role=role,file=filename,sha256=hashlib.sha256(data).hexdigest(),
            rights_evidence_sha256="a"*64,consent_evidence_sha256="b"*64,
            human_rights_reviewed=True,start_seconds=0,duration_seconds=60,
            gain_db=-12))
    manifest=dict(schema_version=1,project_id="sample_film",runtime_seconds=60,
        tracks=tracks,scene_continuity_reviewed=True,
        final_human_approval=False,publication_authorized=False)
    return root,manifest

def test_valid_manifest_stays_hold(tmp_path):
    root,m=fixture(tmp_path)
    result=preflight(m,root)
    assert result["status"]=="PREFLIGHT_ONLY_NOT_RENDERED"
    assert result["publication_authorized"] is False
    assert result["film_rendered"] is False

@pytest.mark.parametrize("change", [
    lambda m: m.update(publication_authorized=True),
    lambda m: m.update(final_human_approval=True),
    lambda m: m.update(scene_continuity_reviewed=False),
    lambda m: m.update(runtime_seconds=300),
    lambda m: m["tracks"][0].update(human_rights_reviewed=False),
    lambda m: m["tracks"][0].update(file="../escape.wav"),
    lambda m: m["tracks"][1].update(gain_db=0),
    lambda m: m["tracks"].pop(),
])
def test_rejected_manifests(tmp_path,change):
    root,m=fixture(tmp_path)
    change(m)
    with pytest.raises(CinematicHold):
        preflight(m,root)

def test_modified_sound_rejected(tmp_path):
    root,m=fixture(tmp_path)
    (root/"voice.wav").write_bytes(b"changed")
    with pytest.raises(CinematicHold,match="SHA-256"):
        preflight(m,root)

def test_symlink_rejected(tmp_path):
    root,m=fixture(tmp_path)
    (root/"voice.wav").unlink()
    (root/"voice.wav").symlink_to(root/"score.wav")
    with pytest.raises(CinematicHold,match="linked"):
        preflight(m,root)
