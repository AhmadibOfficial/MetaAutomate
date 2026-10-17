"""Source-only policy tests. No FFmpeg or AI inference runs."""
import hashlib
from pathlib import Path
import pytest
from app.creative_video_composition import validate, CompositionBlocked

def sample(tmp_path, n=6):
    root=tmp_path/"shots"
    root.mkdir()
    shots=[]
    for i in range(n):
        path=root/("shot%02d.mp4"%i)
        path.write_bytes(b"mock")
        shots.append({"file":path.name,"sha256":hashlib.sha256(b"mock").hexdigest(),
          "rights_evidence_sha256":"a"*64,"human_approved":True,"duration_seconds":6})
    return root,{"schema_version":1,"project_id":"film_demo",
      "reviewer_id":"reviewer_01","distribution_authorized":False,"shots":shots}

def test_reject_unapproved_shot(tmp_path):
    root,m=sample(tmp_path)
    m["shots"][0]["human_approved"]=False
    with pytest.raises(CompositionBlocked,match="rights or review"):
        validate(m,root)

def test_reject_traversal(tmp_path):
    root,m=sample(tmp_path)
    m["shots"][0]["file"]="../secret.mp4"
    with pytest.raises(CompositionBlocked,match="Unsafe"):
        validate(m,root)

def test_reject_distribution(tmp_path):
    root,m=sample(tmp_path)
    m["distribution_authorized"]=True
    with pytest.raises(CompositionBlocked,match="not eligible"):
        validate(m,root)

def test_reject_tamper(tmp_path):
    root,m=sample(tmp_path)
    m["shots"][0]["sha256"]="0"*64
    with pytest.raises(CompositionBlocked,match="integrity"):
        validate(m,root)

def test_reject_symlink(tmp_path):
    root,m=sample(tmp_path)
    original=root/m["shots"][0]["file"]
    original.rename(root/"actual.mp4")
    original.symlink_to(root/"actual.mp4")
    with pytest.raises(CompositionBlocked,match="unavailable"):
        validate(m,root)
