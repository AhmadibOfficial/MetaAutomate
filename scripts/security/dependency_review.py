#!/usr/bin/env python3
"""Approve direct dependency identities before adding new third-party Python code."""
from __future__ import annotations
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs/security/approved-api-python-packages.json"
NORMALIZE = re.compile(r"[-_.]+")
REQUIREMENT = re.compile(r"^\s*([A-Za-z0-9_.-]+)(?:\[[A-Za-z0-9_,.-]+\])?\s*(?:[<>=!~].+)?$")

def canonical(value: str) -> str:
    return NORMALIZE.sub("-", value).lower()

def parse_names(lines: list[str]) -> list[str]:
    names = []
    for row in lines:
        clean = row.split("#", 1)[0].strip()
        if not clean:
            continue
        if clean.startswith("-") or "://" in clean or "@" in clean:
            raise ValueError("Unreviewed pip directives, URLs or external references")
        match = REQUIREMENT.fullmatch(clean)
        if not match:
            raise ValueError("Unreviewed or malformed requirement syntax")
        names.append(canonical(match.group(1)))
    return names

def main() -> int:
    try:
        meta = json.loads(MANIFEST.read_text("utf-8"))
        require = ROOT / meta["requirements"]
        names = parse_names(require.read_text("utf-8").splitlines())
        approved = [canonical(x) for x in meta["packages"]]
        if len(names) != len(set(names)) or len(approved) != len(set(approved)):
            raise ValueError("Repeated Python dependencies")
        if set(names) != set(approved):
            raise ValueError("Added, removed or renamed dependency requires human review")
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"BLOCKED: dependency identity review ({type(error).__name__})", file=sys.stderr)
        return 1
    print("PASS: active Python dependency identities match approved list (NOT a version lock)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
