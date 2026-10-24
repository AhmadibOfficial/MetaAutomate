"""P2-060b local evidence review guard tests using only fabricated files.

No access to a real owner evidence directory, network, browsers or projects.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import zlib

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/review_p2_060_browser_evidence.py"
spec = importlib.util.spec_from_file_location("local_browser_evidence", SCRIPT)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)

UTC = "2026-10-24T12:00:00.000Z"
BRIEF = (
    "30–60 SECOND PROMOTIONAL VIDEO BRIEF — DRAFT\n"
    "Brand: Synthetic MetaAutomate Shop\n"
    "Product: Branded Cap\n"
    "No model-generated video or external publication occurs here.\n"
)
ACTIONS = [
    "Inventory CSV imported: 3 items",
    "Campaign draft prepared for CAP-01",
    "Original PNG artwork rendered locally",
    "Internal content review recorded for Instagram draft",
    "Draft edited — previous internal approval revoked",
    "Internal content review recorded for Instagram draft",
    "Self-reported campaign metrics evaluated",
]


def png(width: int, height: int) -> bytes:
    """Generate small but valid 8-bit RGBA PNGs with correct CRCs."""
    def chunk(name: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + name + data +
                struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    pixels = (b"\0" + b"\0" * (width * 4)) * height
    return (review.PNG_SIGNATURE + chunk(b"IHDR", ihdr) +
            chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b""))


def report() -> dict:
    return {
        "schemaVersion": 1, "milestone": "P2-060",
        "environment": "BROWSER_LOCAL", "classification": "USER_SUPPLIED_UNVERIFIED",
        "record": {
            "sku": "CAP-01", "product": "Branded Cap",
            "brand": "Synthetic MetaAutomate Shop", "channel": "Instagram",
            "reason": "No recorded weekly sales", "priceKobo": 850000,
        },
        "drafts": {
            "social": "Changed synthetic draft; review required.",
            "video": BRIEF,
            "originalGraphicGenerated": True,
        },
        "approval": {
            "state": "INTERNAL_DRAFT_REVIEW_RECORDED", "scope": "COPY_OR_DOWNLOAD_ONLY",
            "channel": "Instagram", "at": UTC,
        },
        "metrics": {
            "impressions": 100, "clicks": 20, "orders": 3,
            "clickThroughRatePct": 20, "clickToOrderPct": 15,
            "sourceNote": "Synthetic example only, no external campaign",
            "evidence": "SELF_REPORTED_NOT_INDEPENDENTLY_VERIFIED",
            "attribution": "Unverified; no campaign causation or revenue",
        },
        "events": [{"action": action, "at": UTC} for action in ACTIONS],
        "safeguards": {
            "publishPerformed": False, "externalRequests": False,
            "aiModelUsed": False, "financialPerformanceVerified": False,
            "providerMetricsVerified": False,
        },
    }


def write_manifest(directory: Path) -> None:
    manifest = "".join(
        hashlib.sha256((directory / name).read_bytes()).hexdigest() + "  ./" + name + "\n"
        for name in sorted(review.EXPECTED)
    )
    (directory / "SHA256SUMS.txt").write_text(manifest, encoding="ascii")


@pytest.fixture
def evidence(tmp_path):
    destination = tmp_path / "review"
    destination.mkdir()
    fixture = report()
    graphic = png(1080, 1080)
    for label, width in review.VIEWPORTS.items():
        (destination / f"campaign-{label}.png").write_bytes(graphic)
        (destination / f"campaign-workbench-{label}.png").write_bytes(png(width, 901))
        (destination / f"video-brief-{label}.txt").write_text(BRIEF, encoding="utf-8")
        (destination / f"campaign-evidence-{label}.json").write_text(
            json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
    write_manifest(destination)
    return destination


def test_review_valid_synthetic_local_evidence_never_claims_independence(evidence):
    status = review.validate(evidence)
    assert status["status"] == "DEVELOPER_LOCAL_EVIDENCE_CONSISTENT"
    assert status["artifacts"] == 12
    assert status["screenshots_visually_inspected"] is False
    assert status["accessibility_independently_verified"] is False
    assert status["appsec_independently_verified"] is False
    assert status["production_release_approved"] is False


def test_evidence_checksum_modification_fails_closed(evidence):
    path = evidence / "campaign-evidence-desktop.json"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(review.EvidenceError, match="Checksum mismatch"):
        review.validate(evidence)


def test_rehashed_false_publish_claim_still_denied(evidence):
    path = evidence / "campaign-evidence-mobile.json"
    obj = json.loads(path.read_text())
    obj["safeguards"]["publishPerformed"] = True
    path.write_text(json.dumps(obj), encoding="utf-8")
    write_manifest(evidence)
    with pytest.raises(review.EvidenceError, match="Safety safeguard"):
        review.validate(evidence)


def test_rehashed_inflated_metrics_denied(evidence):
    path = evidence / "campaign-evidence-small.json"
    obj = json.loads(path.read_text())
    obj["metrics"]["orders"] = 99
    path.write_text(json.dumps(obj), encoding="utf-8")
    write_manifest(evidence)
    with pytest.raises(review.EvidenceError, match="Invalid synthetic metric"):
        review.validate(evidence)


def test_rehashed_cropped_viewport_denied(evidence):
    (evidence / "campaign-workbench-mobile.png").write_bytes(png(380, 900))
    write_manifest(evidence)
    with pytest.raises(review.EvidenceError, match="Screenshot viewport capture"):
        review.validate(evidence)


def test_rehashed_corrupt_png_crc_denied(evidence):
    path = evidence / "campaign-desktop.png"
    raw = bytearray(path.read_bytes())
    raw[-8] ^= 1
    path.write_bytes(raw)
    write_manifest(evidence)
    with pytest.raises(review.EvidenceError, match="PNG chunk CRC"):
        review.validate(evidence)


def test_missing_extra_and_symlink_evidence_denied(evidence, tmp_path):
    rogue = evidence / "unexpected.txt"
    rogue.write_text("extra")
    with pytest.raises(review.EvidenceError, match="Expected exactly 12"):
        review.validate(evidence)
    rogue.unlink()
    graphic = evidence / "campaign-desktop.png"
    graphic.unlink()
    graphic.symlink_to(tmp_path / "other.png")
    with pytest.raises(review.EvidenceError, match="Not a regular evidence file"):
        review.validate(evidence)


def test_rehashed_video_brief_mismatch_denied(evidence):
    path = evidence / "video-brief-small.txt"
    path.write_text(BRIEF + "\nExtra text\n", encoding="utf-8")
    write_manifest(evidence)
    with pytest.raises(review.EvidenceError, match="Downloaded video brief differs"):
        review.validate(evidence)


def test_invalid_manifest_entries_denied(evidence):
    with (evidence / "SHA256SUMS.txt").open("a", encoding="ascii") as handle:
        handle.write("0" * 64 + "  ./other.txt\n")
    with pytest.raises(review.EvidenceError, match="12 entries"):
        review.validate(evidence)
