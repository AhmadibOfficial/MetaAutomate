#!/usr/bin/env python3
"""P3-08 local source review packet. Never validates real reviewer approval.

Run on an exact approved SOURCE checkout. All outputs are NO_GO regardless
of Python tests; humans must independently verify reviewer and live evidence.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))

from app.phase03_review_readiness import (  # noqa: E402
    EXPECTED_PARENT_SHA, ReviewReadinessDenied, build_review_preparation,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expect-reviewed-source",
        required=True, help="Exact immutable P3-07 PR #53 parent SHA",
    )
    args = parser.parse_args(argv)
    if args.expect_reviewed_source != EXPECTED_PARENT_SHA:
        print("REVIEW_READINESS=DENIED: Wrong expected parent source", file=sys.stderr)
        return 2
    try:
        prepared = build_review_preparation(ROOT)
    except ReviewReadinessDenied as exc:
        print(f"REVIEW_READINESS=DENIED: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(asdict(prepared), sort_keys=True, indent=2))
    return 0  # success generating NO_GO report, NOT approval


if __name__ == "__main__":
    raise SystemExit(main())
