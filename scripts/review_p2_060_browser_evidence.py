#!/usr/bin/env python3
"""Read-only P2-060b evidence consistency gate for a *saved local copy*.

Never uploads artifacts, edits the directory, follows symlinks, or claims an
independent accessibility, design, security or commercial validation.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
VIEWPORTS = {"desktop": 1440, "mobile": 390, "small": 360}
EXPECTED = frozenset(
    [f"campaign-{name}.png" for name in VIEWPORTS]
    + [f"campaign-workbench-{name}.png" for name in VIEWPORTS]
    + [f"campaign-evidence-{name}.json" for name in VIEWPORTS]
    + [f"video-brief-{name}.txt" for name in VIEWPORTS]
)
MAX_BYTES = 8 * 1024 * 1024
MANIFEST_LINE = re.compile(r"([0-9a-f]{64})  \./([A-Za-z0-9_.-]+)\Z")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class EvidenceError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceError(message)


def private_files(directory: Path) -> dict[str, bytes]:
    directory = directory.expanduser().absolute()
    require(not any(p.is_symlink() for p in (directory, *directory.parents)),
            "Evidence directory or ancestor is symlinked")
    require(directory.is_dir(), "Evidence directory does not exist")
    require(not directory.resolve().is_relative_to(ROOT.resolve()),
            "Review input must be outside the source repository")
    found = {p.name: p for p in directory.iterdir()}
    require(set(found) == EXPECTED | {"SHA256SUMS.txt"},
            "Expected exactly 12 artifacts plus SHA256SUMS.txt, no extra files")
    output = {}
    for name, path in found.items():
        require(path.is_file() and not path.is_symlink(), "Not a regular evidence file: " + name)
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        try:
            info = os.fstat(fd)
            require(stat.S_ISREG(info.st_mode), "Not a regular evidence file: " + name)
            require(0 < info.st_size <= MAX_BYTES, "Unexpected evidence size: " + name)
            with os.fdopen(fd, "rb") as handle:
                fd = -1
                data = handle.read(MAX_BYTES + 1)
                require(len(data) <= MAX_BYTES, "Oversized evidence: " + name)
                output[name] = data
        finally:
            if fd != -1:
                os.close(fd)
    return output


def verify_manifest(files: dict[str, bytes]) -> dict[str, str]:
    manifest = files["SHA256SUMS.txt"]
    require(len(manifest) <= 4096, "Oversized checksum manifest")
    try:
        lines = manifest.decode("ascii").splitlines()
    except UnicodeDecodeError as exc:
        raise EvidenceError("Checksum manifest is not ASCII") from exc
    require(len(lines) == len(EXPECTED), "Checksum manifest must have 12 entries")
    digests = {}
    for line in lines:
        matched = MANIFEST_LINE.fullmatch(line)
        require(matched is not None, "Malformed checksum manifest line")
        digest, name = matched.groups()
        require(name in EXPECTED and name not in digests,
                "Unexpected or duplicate checksum filename: " + name)
        digests[name] = digest
        require(hashlib.sha256(files[name]).hexdigest() == digest,
                "Checksum mismatch: " + name)
    require(set(digests) == EXPECTED, "Checksum manifest incomplete")
    return digests


def png_dimensions(raw: bytes, name: str) -> tuple[int, int]:
    require(raw.startswith(PNG_SIGNATURE), "Not a PNG: " + name)
    offset, width, height = len(PNG_SIGNATURE), None, None
    found_idat = False
    found_end = False
    first = True
    while offset < len(raw):
        require(len(raw) - offset >= 12, "Truncated PNG chunk: " + name)
        length = struct.unpack_from(">I", raw, offset)[0]
        end = offset + 12 + length
        require(length <= MAX_BYTES and end <= len(raw), "Oversized/truncated PNG chunk: " + name)
        typ = raw[offset + 4:offset + 8]
        data = raw[offset + 8:offset + 8 + length]
        checksum = struct.unpack_from(">I", raw, offset + 8 + length)[0]
        require(zlib.crc32(typ + data) & 0xFFFFFFFF == checksum,
                "PNG chunk CRC mismatch: " + name)
        if first:
            require(typ == b"IHDR" and length == 13, "Missing PNG IHDR: " + name)
            width, height = struct.unpack_from(">II", data)
            require(1 <= width <= 5000 and 1 <= height <= 5000,
                    "Invalid PNG dimensions: " + name)
            first = False
        elif typ == b"IDAT":
            found_idat = True
        elif typ == b"IEND":
            require(length == 0, "Invalid PNG trailer")
            found_end = True
            require(end == len(raw), "Trailing PNG data")
            break
        offset = end
    require(found_idat and found_end, "Incomplete PNG structure: " + name)
    return width, height


def iso_datetime(value, label):
    require(isinstance(value, str) and value.endswith("Z"),
            "Missing UTC event timestamp: " + label)
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError("Invalid event timestamp: " + label) from exc


def verify_report(raw: bytes, viewport: str) -> dict:
    try:
        report = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError("Invalid JSON report: " + viewport) from exc
    require(isinstance(report, dict), "Evidence report must be an object")
    for key, expected in {
        "schemaVersion": 1,
        "milestone": "P2-060",
        "environment": "BROWSER_LOCAL",
        "classification": "USER_SUPPLIED_UNVERIFIED",
    }.items():
        require(type(report.get(key)) is type(expected) and report[key] == expected,
                "Unapproved evidence classification: " + key)
    record = report.get("record")
    require(isinstance(record, dict), "Missing campaign record")
    for key, expected in {
        "sku": "CAP-01",
        "product": "Branded Cap",
        "brand": "Synthetic MetaAutomate Shop",
        "channel": "Instagram",
        "priceKobo": 850000,
        "reason": "No recorded weekly sales",
    }.items():
        require(type(record.get(key)) is type(expected) and record[key] == expected,
                "Unapproved synthetic campaign record: " + key)
    drafts = report.get("drafts")
    require(isinstance(drafts, dict), "Missing drafts")
    require(drafts.get("originalGraphicGenerated") is True, "Original graphic not reported")
    require(drafts.get("social") == "Changed synthetic draft; review required.",
            "Unexpected final social copy: expected re-reviewed synthetic revision")
    brief = drafts.get("video")
    require(isinstance(brief, str) and "VIDEO BRIEF" in brief and
            "Synthetic MetaAutomate Shop" in brief and "Branded Cap" in brief and
            "No model-generated video" in brief,
            "Video brief does not contain expected synthetic scope/disclaimers")
    approval = report.get("approval")
    require(isinstance(approval, dict) and
            approval.get("state") == "INTERNAL_DRAFT_REVIEW_RECORDED" and
            approval.get("scope") == "COPY_OR_DOWNLOAD_ONLY" and
            approval.get("channel") == "Instagram", "Invalid internal approval scope")
    iso_datetime(approval.get("at"), "approval")
    metrics = report.get("metrics")
    require(isinstance(metrics, dict), "Missing self-reported metrics")
    for key, value in {
        "impressions": 100, "clicks": 20, "orders": 3,
        "clickThroughRatePct": 20, "clickToOrderPct": 15,
    }.items():
        require(type(metrics.get(key)) in (int, float) and metrics[key] == value,
                "Invalid synthetic metric: " + key)
    require(metrics.get("sourceNote") == "Synthetic example only, no external campaign" and
            metrics.get("evidence") == "SELF_REPORTED_NOT_INDEPENDENTLY_VERIFIED" and
            "Unverified" in metrics.get("attribution", ""),
            "Metrics falsely presented as independently sourced")
    guards = report.get("safeguards")
    require(isinstance(guards, dict), "Missing safeguards")
    for key in ("publishPerformed", "externalRequests", "aiModelUsed",
                "financialPerformanceVerified", "providerMetricsVerified"):
        require(guards.get(key) is False, "Safety safeguard not false: " + key)
    events = report.get("events")
    require(isinstance(events, list) and 5 <= len(events) <= 200,
            "Invalid campaign audit event count")
    actions = []
    for i, event in enumerate(events):
        require(isinstance(event, dict) and isinstance(event.get("action"), str),
                "Malformed campaign audit event")
        iso_datetime(event.get("at"), f"event-{i}")
        actions.append(event["action"])
    needed = ("Inventory CSV imported", "Campaign draft prepared",
              "Draft edited", "Internal content review recorded",
              "Self-reported campaign metrics evaluated")
    require(all(any(action.startswith(term) for action in actions) for term in needed),
            "Expected import, draft, review, revision or metrics event missing")
    require(any(action.startswith("Draft edited") for action in actions) and
            sum("Internal content review recorded" in a for a in actions) >= 2,
            "Draft review revocation and re-review not demonstrated")
    return report


def validate(directory: Path) -> dict:
    files = private_files(directory)
    digests = verify_manifest(files)
    reports = {}
    for label, width in VIEWPORTS.items():
        png = f"campaign-{label}.png"
        require(png_dimensions(files[png], png) == (1080, 1080),
                "Promotional graphic dimensions differ from 1080x1080: " + label)
        screenshot = f"campaign-workbench-{label}.png"
        size = png_dimensions(files[screenshot], screenshot)
        require(size[0] == width and size[1] >= 900,
                "Screenshot viewport capture dimensions invalid: " + label)
        brief_file = f"video-brief-{label}.txt"
        try:
            brief = files[brief_file].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise EvidenceError("Video brief is not UTF-8: " + label) from exc
        require("Synthetic MetaAutomate Shop" in brief and "Branded Cap" in brief and
                "VIDEO BRIEF" in brief and "No model-generated video" in brief,
                "Video brief content mismatches synthetic scenario: " + label)
        reports[label] = verify_report(files[f"campaign-evidence-{label}.json"], label)
        require(reports[label]["drafts"]["video"] == brief,
                "Downloaded video brief differs from evidence JSON: " + label)
    require(len({digests[f"campaign-{label}.png"] for label in VIEWPORTS}) == 1,
            "Campaign design inconsistent across viewports")
    reference = reports["desktop"]
    for label in ("mobile", "small"):
        for field in ("record", "drafts", "metrics", "safeguards"):
            require(reports[label][field] == reference[field],
                    "Inconsistent same-fixture JSON field: " + field + " / " + label)
    return {
        "status": "DEVELOPER_LOCAL_EVIDENCE_CONSISTENT",
        "artifacts": len(EXPECTED),
        "sha256_manifest_verified_against_local_copy": True,
        "synthetic_inputs_only": True,
        "png_structure_crc_and_dimensions_checked": True,
        "json_synthetic_safeguards_checked": True,
        "screenshots_visually_inspected": False,
        "accessibility_independently_verified": False,
        "appsec_independently_verified": False,
        "github_ci_verified": False,
        "production_release_approved": False,
        "commercial_traction_verified": False,
        "note": "Manifest is owner-generated; match does not prove independent provenance.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True,
                        help="Existing, preserved private evidence directory outside Git")
    args = parser.parse_args(argv)
    try:
        verdict = validate(args.directory)
    except (EvidenceError, OSError) as exc:
        print("DEVELOPER_LOCAL_EVIDENCE_BLOCKED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(verdict, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
