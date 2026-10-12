#!/usr/bin/env python3
"""Pre-release hygiene gate for tracked MetaAutomate OSS source.

This is a narrow current-tree check, NOT Git history or a substitute for
GitHub secret scanning, security review, or professional license review.
"""
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
required=[
    "LICENSE","README.md","CONTRIBUTING.md","SECURITY.md",
    "CODE_OF_CONDUCT.md","docs/OPEN_SOURCE.md",
    "docs/architecture/OVERVIEW.md","docs/ROADMAP.md",
    "examples/oss-demo/compose.yaml",
    "scripts/oss_demo_up.sh","scripts/oss_demo_down.sh",
]
errors=[]
for rel in required:
    if not (ROOT/rel).is_file():
        errors.append("Missing required OSS entrypoint: "+rel)
license_text=(ROOT/"LICENSE").read_text(encoding="utf-8")
if "GNU GENERAL PUBLIC LICENSE" not in license_text or "Version 2, June 1991" not in license_text:
    errors.append("Repository license changed without explicit maintainer approval")
readme=(ROOT/"README.md").read_text(encoding="utf-8")
if "Current implementation" not in readme or "Not implemented" not in readme:
    errors.append("README must accurately distinguish implemented and planned capabilities")

tracked=subprocess.check_output(["git","ls-files","-z"],cwd=ROOT).decode().split("\0")
sensitive_name=re.compile(r"(^|/)(\.env($|\.|/)|\.workspace-access-key$|id_rsa$|id_ed25519$|.+\.(pem|p12|pfx|jks|key)$)")
safe_templates={".env.example",".env.sample"}
for rel in filter(None,tracked):
    path=ROOT/rel
    if sensitive_name.search(rel) and path.name not in safe_templates:
        errors.append("Sensitive local file tracked by Git: "+rel)
    if not path.is_file() or path.stat().st_size>3_000_000:
        continue
    try:
        data=path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        continue
    if re.search(r"^-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",data,re.MULTILINE):
        errors.append("Private key block committed in "+rel)

if errors:
    for item in errors:
        print("FAIL:",item)
    raise SystemExit(1)
print("PASS: OSS docs, existing license, truthful README and current tracked-file hygiene")
print("NOTE: This cannot prove historical commits never contained secrets.")
