#!/usr/bin/env python3
"""Block sensitive tracked/staged file paths without reading or logging file contents."""
from __future__ import annotations
import argparse
from pathlib import Path, PurePosixPath
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SENSITIVE_DIRS = {"secrets", "credentials", ".aws", ".ssh", ".kube"}
SENSITIVE_NAMES = {".env", ".envrc", ".npmrc", ".pypirc", ".netrc", ".workspace-access-key", "id_rsa", "id_ed25519", "id_ecdsa", "google-services.json", "googleService-info.plist".lower()}
SENSITIVE_ENDINGS = (".pem", ".key", ".p12", ".pfx", ".mobileprovision", ".tfstate")
SAFE_TEMPLATES = {".env.example", ".env.sample", ".env.template"}

def sensitive(path: str) -> bool:
    p = PurePosixPath(path.replace("\\", "/"))
    parts = p.parts
    if not parts or ".." in parts or "." in parts:
        return True
    if any(part.lower() in SENSITIVE_DIRS for part in parts[:-1]):
        return True
    name = parts[-1].lower()
    if name in SAFE_TEMPLATES:
        return False
    return (
        name in SENSITIVE_NAMES
        or name.startswith(".env.")
        or name.endswith(SENSITIVE_ENDINGS)
        or ".tfstate." in name
        or (name.startswith(("service-account", "service_account")) and name.endswith(".json"))
        or path == ".claude/settings.local.json"
    )

def tracked(mode: str) -> list[str]:
    cmd = (["git", "ls-files", "-z"] if mode == "tracked" else
           ["git", "diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR"])
    output = subprocess.check_output(cmd, cwd=ROOT, stderr=subprocess.DEVNULL)
    return [x.decode("utf-8", "surrogateescape") for x in output.split(b"\0") if x]

def main() -> int:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--tracked", action="store_true")
    modes.add_argument("--staged", action="store_true")
    args = parser.parse_args()
    try:
        failures = [p for p in tracked("tracked" if args.tracked else "staged") if sensitive(p)]
    except (OSError, subprocess.CalledProcessError):
        print("BLOCKED: unable to check Git paths", file=sys.stderr)
        return 2
    if failures:
        print(f"BLOCKED: {len(failures)} sensitive paths tracked/staged (names withheld from CI logs)", file=sys.stderr)
        return 1
    print("PASS: no prohibited sensitive paths tracked/staged")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
