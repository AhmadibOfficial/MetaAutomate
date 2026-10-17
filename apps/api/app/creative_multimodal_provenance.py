"""P2-04u — provenance-bound multimodal production handoff.

Integrates on-disk receipts from the gated Diffusers image/video worker and
Piper speech worker with the offline video+voice composer. Records *signed
human assertions* and file integrity; cannot prove inference occurred or
that rights/consent statements are genuine. All output stays quarantined.
"""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
import re

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from app.creative_multimodal_studio import (
    StudioHold, canonical, digest_file, validate_manifest, render,
)

SHA = re.compile(r"^[0-9a-f]{64}$")
TIME = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
FIELDS = {
    "asset_file", "asset_kind", "output_sha256", "source_receipt_sha256",
    "source_job_sha256", "model_sha256", "authorization_sha256",
    "observed_execution_record_sha256", "producer_id", "reviewer_id",
    "operator_execution_witnessed", "quality_human_checked",
    "licence_human_checked", "rights_human_checked", "consent_human_checked",
    "issued_at", "expires_at", "signature",
}
MODES = {
    "image": ("LOCAL_DIFFUSERS_REAL_INFERENCE",
              "QUARANTINED_PENDING_INDEPENDENT_SAFETY_REVIEW"),
    "video": ("LOCAL_DIFFUSERS_REAL_INFERENCE",
              "QUARANTINED_PENDING_INDEPENDENT_SAFETY_REVIEW"),
    "speech": ("OPERATOR_ATTESTED_LOCAL_MODEL",
               "QUARANTINED_PENDING_INDEPENDENT_REVIEW"),
}


def _sha(value: object, label: str) -> str:
    if type(value) is not str or SHA.fullmatch(value) is None:
        raise StudioHold(f"Invalid or missing {label} SHA-256")
    return value


def _utc(value: object) -> datetime:
    if type(value) is not str or TIME.fullmatch(value) is None:
        raise StudioHold("Signed evidence requires an exact UTC timestamp")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise StudioHold("Invalid signed evidence time") from exc


def _key(value: object, length: int) -> bytes:
    if type(value) is not str or re.fullmatch(r"[A-Za-z0-9_-]+", value) is None:
        raise StudioHold("Invalid reviewer public key or signature encoding")
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, base64.binascii.Error) as exc:
        raise StudioHold("Invalid signed evidence encoding") from exc
    if (len(raw) != length or
        base64.urlsafe_b64encode(raw).rstrip(b"=").decode() != value):
        raise StudioHold("Noncanonical Ed25519 key or signature")
    return raw


def _verify_attestation(attestation: dict, receipt: dict, kind: str,
                        name: str, media_sha: str,
                        reviewer_keys: dict, now: datetime) -> str:
    """Check registered reviewer signatures bound to exact model/media/receipt."""
    if type(attestation) is not dict or set(attestation) != FIELDS:
        raise StudioHold("Complete signed provenance attestation required")
    if kind not in MODES or type(receipt) is not dict:
        raise StudioHold("Unsupported source receipt kind")
    mode, quarantine = MODES[kind]
    is_visual = kind != "speech"
    expected = {
        "asset_file": name,
        "asset_kind": kind,
        "output_sha256": media_sha,
        "source_receipt_sha256": sha256(canonical(receipt)).hexdigest(),
        "source_job_sha256": receipt.get("job_sha256"),
        "model_sha256": receipt.get(
            "model_tree_sha256" if is_visual else "model_checkpoint_sha256"),
    }
    for key, value in expected.items():
        if type(attestation.get(key)) is not type(value) or attestation.get(key) != value:
            raise StudioHold("Provenance binding does not match its input receipt")
    for key in ("source_job_sha256", "model_sha256",
                "authorization_sha256", "observed_execution_record_sha256"):
        _sha(attestation.get(key), key)
    if is_visual:
        if (receipt.get("generation_mode") != mode or
            receipt.get("output_state") != quarantine or
            receipt.get("authorization_sha256") != attestation["authorization_sha256"] or
            receipt.get("output_kind") != kind or
            receipt.get("published") is not False or
            receipt.get("customer_distribution_authorized") is not False or
            receipt.get("real_ai_output_verified") is not True):
            raise StudioHold("Visual source was not an allowed private inference receipt")
    else:
        if (receipt.get("generation_mode") != mode or
            receipt.get("state") != quarantine or
            receipt.get("published") is not False or
            receipt.get("distribution_authorized") is not False):
            raise StudioHold("Speech source was not a private Piper inference receipt")
        # The Piper receipt lacks approval hash; this is an independently
        # witnessed *claim*, which still needs external cryptographic binding.
    producer, reviewer = attestation["producer_id"], attestation["reviewer_id"]
    if (type(producer) is not str or len(producer) < 8 or
        type(reviewer) is not str or len(reviewer) < 8 or producer == reviewer or
        type(reviewer_keys) is not dict or reviewer not in reviewer_keys):
        raise StudioHold("Independently registered reviewer identity required")
    flags = ("operator_execution_witnessed", "quality_human_checked",
             "licence_human_checked", "rights_human_checked",
             "consent_human_checked")
    if not all(attestation.get(k) is True for k in flags):
        raise StudioHold("Independent model, quality, licence and rights review incomplete")
    issued, expiry = _utc(attestation["issued_at"]), _utc(attestation["expires_at"])
    if (now.tzinfo is None or not issued <= now.astimezone(timezone.utc) < expiry
        or not timedelta(minutes=1) <= expiry - issued <= timedelta(hours=24)):
        raise StudioHold("Expired or excessive source review time window")
    payload = canonical({k: v for k, v in attestation.items() if k != "signature"})
    try:
        public_key = _key(reviewer_keys[reviewer], 32)
        signature = _key(attestation["signature"], 64)
        Ed25519PublicKey.from_public_bytes(public_key).verify(signature, payload)
    except (InvalidSignature, ValueError) as exc:
        raise StudioHold("Untrusted provenance human signature") from exc
    return sha256(payload).hexdigest()


def verify_source_bundle(manifest: dict, asset_root: Path,
                         evidence: dict, *, reviewer_keys: dict,
                         now: datetime | None = None) -> dict:
    """One image, one short video and one speech provenance required.

    This read-only gate checks cryptographic *claims*, not observed physical
    model execution or legal rights. It never returns an AI-proof PASS.
    """
    accepted = validate_manifest(manifest, asset_root)
    if (type(evidence) is not dict or
        set(evidence) != {"schema_version", "project_id", "sources"} or
        type(evidence["schema_version"]) is not int or
        evidence["schema_version"] != 1 or
        evidence["project_id"] != manifest["project_id"] or
        type(evidence["sources"]) is not dict):
        raise StudioHold("Invalid production provenance evidence bundle")
    required = {
        scene["file"]: scene["kind"] for scene in manifest["scenes"]
    }
    required[manifest["voice"]["file"]] = "speech"
    if len(required) != len(manifest["scenes"]) + 1:
        raise StudioHold("Duplicate audio and visual source filenames")
    if set(evidence["sources"]) != set(required):
        raise StudioHold("Every visual and voice source needs provenance")
    if not {"image", "video", "speech"}.issubset(set(required.values())):
        raise StudioHold("Full AI proof project needs an image, short video and speech")
    current = now or datetime.now(timezone.utc)
    approvals = {}
    for name, kind in required.items():
        source = evidence["sources"][name]
        if type(source) is not dict or set(source) != {"receipt", "review"}:
            raise StudioHold("Complete source receipt and independent review required")
        if kind == "speech":
            file_sha = manifest["voice"]["sha256"]
        else:
            file_sha = next(x["sha256"] for x in manifest["scenes"]
                            if x["file"] == name)
        _sha(file_sha, "media")
        digest = _verify_attestation(source["review"], source["receipt"],
                                     kind, name, file_sha, reviewer_keys, current)
        approvals[name] = digest
    return {
        "schema_version": 1,
        "project_id": manifest["project_id"],
        "manifest_sha256": sha256(canonical(manifest)).hexdigest(),
        "source_evidence_sha256": sha256(canonical(evidence)).hexdigest(),
        "registered_review_claims_sha256": approvals,
        "runtime_seconds": accepted["runtime"],
        "status": "SOURCE_HASHES_AND_SIGNED_HUMAN_CLAIMS_VALIDATED",
        "inference_independently_verified_by_code": False,
        "legal_rights_authenticated_by_code": False,
        "video_voice_quality_independently_verified": False,
        "final_review_signed": False,
        "distribution_authorized": False,
        "published": False,
    }


def render_with_source_proofs(manifest: dict, asset_root: Path,
                              quarantine_root: Path, evidence: dict,
                              *, reviewer_keys: dict) -> dict:
    """Run cinematic composer only after signed source evidence check."""
    source = verify_source_bundle(manifest, asset_root, evidence,
                                  reviewer_keys=reviewer_keys)
    receipt = render(manifest, asset_root, quarantine_root)
    if (receipt.get("final_human_approval") is not False or
        receipt.get("published") is not False or
        receipt.get("status") != "QUARANTINED_PENDING_INDEPENDENT_FINAL_REVIEW" or
        receipt.get("manifest_sha256") != source["manifest_sha256"]):
        raise StudioHold("Unexpected cinematic receipt or premature release state")
    # Do not write to the published pipeline. A separate signed final review
    # is required after independently viewing the exact final film.
    return {
        "schema_version": 1,
        "project_id": manifest["project_id"],
        "source_evidence_sha256": source["source_evidence_sha256"],
        "source_signed_claims": source["registered_review_claims_sha256"],
        "final_sha256": receipt["final_sha256"],
        "render_status": receipt["status"],
        "native_ai_image_inference_independently_proven": False,
        "native_ai_video_inference_independently_proven": False,
        "neural_voice_inference_independently_proven": False,
        "independent_final_human_review": False,
        "publication_authorized": False,
        "published": False,
    }
