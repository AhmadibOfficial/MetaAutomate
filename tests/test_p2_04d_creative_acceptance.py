"""P2-04d source-only acceptance checks. No fake output may pass as real evidence."""
import hashlib
import json
import os
from pathlib import Path
import stat

import pytest

from app.creative_acceptance import verify
from app.creative_local_generation import GenerationBlocked

def fixture(tmp_path, kind="image"):
    folder = tmp_path / "private"
    folder.mkdir(mode=0o700)
    media = folder / ("generated.png" if kind == "image" else "generated.mp4")
    media.write_bytes(b"not real media, deliberately a fixture" * 3)
    media.chmod(0o600)
    receipt = {
        "schema_version": 1, "output_kind": kind,
        "generation_mode": "LOCAL_DIFFUSERS_REAL_INFERENCE",
        "real_ai_output_verified": True,
        "output_state": "QUARANTINED_PENDING_INDEPENDENT_SAFETY_REVIEW",
        "published": False, "customer_distribution_authorized": False,
        "content_safety_independently_verified": False,
        "rights_independently_authenticated_by_worker": False,
        "job_sha256": "a" * 64, "authorization_sha256": "b" * 64,
        "model_tree_sha256": "c" * 64,
        "output_sha256": hashlib.sha256(media.read_bytes()).hexdigest(),
        "output_bytes": media.stat().st_size,
    }
    path = folder / "receipt.json"
    path.write_text(json.dumps(receipt))
    path.chmod(0o600)
    return folder, media, path

def test_tampered_digest_rejected(tmp_path):
    folder, media, _ = fixture(tmp_path)
    media.write_bytes(b"X" * media.stat().st_size)
    with pytest.raises(GenerationBlocked, match="SHA-256 mismatch"):
        verify(folder, "image")

def test_fake_png_does_not_pass_real_acceptance(tmp_path):
    folder, _, _ = fixture(tmp_path)
    with pytest.raises(GenerationBlocked, match="Invalid PNG|Pillow unavailable"):
        verify(folder, "image")

def test_fake_mp4_does_not_pass_real_acceptance(tmp_path):
    folder, _, _ = fixture(tmp_path, "video")
    with pytest.raises(GenerationBlocked):
        verify(folder, "video")

def test_test_runner_cannot_pass(tmp_path):
    folder, _, path = fixture(tmp_path)
    receipt = json.loads(path.read_text())
    receipt["generation_mode"] = "TEST_ONLY_FAKE_RUNNER_NOT_AI"
    path.write_text(json.dumps(receipt))
    with pytest.raises(GenerationBlocked, match="not from claimed"):
        verify(folder, "image")

def test_public_media_rejected(tmp_path):
    folder, media, _ = fixture(tmp_path)
    media.chmod(0o644)
    with pytest.raises(GenerationBlocked, match="group/other"):
        verify(folder, "image")

def test_symlink_media_rejected(tmp_path):
    folder, media, _ = fixture(tmp_path)
    original = folder / "source.png"
    media.rename(original)
    media.symlink_to(original)
    with pytest.raises(GenerationBlocked, match="symlink"):
        verify(folder, "image")

def test_receipt_false_publication_rejected(tmp_path):
    folder, _, path = fixture(tmp_path)
    receipt = json.loads(path.read_text())
    receipt["published"] = True
    path.write_text(json.dumps(receipt))
    with pytest.raises(GenerationBlocked, match="not from claimed"):
        verify(folder, "image")
