#!/usr/bin/env python3
"""Check changed Python with Bandit and high-confidence JavaScript hazards locally."""
from __future__ import annotations
import argparse
import re
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SHA = re.compile(r"^[0-9a-f]{40}$")
JS_BAD = (
    ("dynamic code execution", re.compile(r"\beval\s*\(|\bnew\s+Function\s*\(")),
    ("HTML injection sink", re.compile(r"\.innerHTML\s*=(?!=)|\.outerHTML\s*=(?!=)|document\.write\s*\(")),
    ("unreviewed child process", re.compile(r"""(?:require\s*\(\s*['"]child_process['"]\s*\)|\bexecSync\s*\()""")),
)

def changed(base: str, head: str) -> list[str]:
    if not SHA.fullmatch(base) or not SHA.fullmatch(head):
        raise ValueError("Expected full 40-character hexadecimal commit SHAs")
    output = subprocess.check_output(
        ["git", "diff", "--name-only", "--diff-filter=ACMR", "-z", base, head],
        cwd=ROOT, stderr=subprocess.DEVNULL)
    return [p.decode("utf-8", "surrogateescape") for p in output.split(b"\0") if p]

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    args = parser.parse_args()
    try:
        python_paths = []
        issues = 0
        for path in changed(args.base, args.head):
            if path.startswith("/") or ".." in Path(path).parts:
                raise ValueError("Unsafe relative path")
            target = (ROOT / path).resolve()
            if not target.is_relative_to(ROOT):
                raise ValueError("Path outside workspace")
            if not target.is_file() or target.is_symlink():
                continue
            if path.endswith(".py"):
                python_paths.append(path)
            if path.endswith((".js", ".mjs", ".cjs")) and path.startswith(("apps/", "workers/")):
                code = target.read_text("utf-8")
                for label, rule in JS_BAD:
                    if rule.search(code):
                        print(f"BLOCKED: {label} in changed JavaScript {path}", file=sys.stderr)
                        issues += 1
        if python_paths:
            cmd = [sys.executable, "-m", "bandit", "-q", "-ll", "-ii", *python_paths]
            result = subprocess.run(cmd, cwd=ROOT, check=False)
            if result.returncode != 0:
                print("BLOCKED: changed Python files failed security analysis", file=sys.stderr)
                issues += 1
        else:
            print("SKIP: no changed Python files")
        if issues:
            return 1
        print("PASS: changed-source SAST")
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError, UnicodeError) as error:
        print(f"BLOCKED: scanner could not complete ({type(error).__name__})", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
