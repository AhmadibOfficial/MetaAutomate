#!/usr/bin/env python3
"""Offline, fail-closed scanner of Git-index or changed-commit files. Never echo secrets."""
from __future__ import annotations
import argparse
import re
import subprocess
import sys

MAX_BYTES=2_000_000
DENY_PATHS=tuple(re.compile(p,re.I) for p in (
 r"(^|/)\.env($|\.)",r"(^|/)\.envrc$",r"(^|/)(secrets?|credentials?)/",
 r"(^|/)(\.npmrc|\.pypirc)$",r"(^|/)id_(rsa|ed25519|ecdsa)(\.pub)?$",
 r"\.(pem|p12|pfx|key|jks|keystore|kdbx)$",r"(^|/)settings\.local\.json$"
))
PATTERNS={
 "private_key":re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----"),
 "github_token":re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{30,})\b"),
 "aws_access_key":re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
 "google_api_key":re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"),
 "slack_token":re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{12,}\b"),
 "stripe_key":re.compile(r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}\b"),
 "openai_key":re.compile(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{24,}\b"),
 "auth_header":re.compile(r"(?i)\bAuthorization\s*:\s*Bearer\s+[A-Za-z0-9_./+=-]{24,}"),
 "secret_assignment":re.compile(r"(?im)\b(?:password|passwd|secret_key|client_secret|api_key|access_token|auth_token)\b\s*[:=]\s*[\"']?([A-Za-z0-9_./+=@!%-]{16,})")
}
SAMPLE_WORDS=("example","dummy","placeholder","redacted","synthetic","changeme")
def git(*args: str)->bytes:
    process=subprocess.run(["git",*args],capture_output=True,check=False)
    if process.returncode: raise RuntimeError("Git unavailable or invalid reference")
    return process.stdout
def inspect(path:str,raw:bytes)->list[tuple[str,int]]:
    problems=[]
    if any(rule.search(path) for rule in DENY_PATHS):problems.append(("restricted_path",0))
    if len(raw)>MAX_BYTES:return problems+[("oversize_uninspected",0)]
    if b"\0" in raw[:4096]:return problems
    try: body=raw.decode("utf-8")
    except UnicodeDecodeError:return problems+[("invalid_utf8",0)]
    for number,line in enumerate(body.splitlines(),1):
        for name,pattern in PATTERNS.items():
            hit=pattern.search(line)
            if hit:
                if name=="secret_assignment" and any(w in hit.group(1).lower() for w in SAMPLE_WORDS):continue
                problems.append((name,number))
    return problems
def main()->int:
    parser=argparse.ArgumentParser()
    exclusive=parser.add_mutually_exclusive_group(required=True)
    exclusive.add_argument("--staged",action="store_true")
    exclusive.add_argument("--base")
    args=parser.parse_args()
    try:
        if args.base and not re.fullmatch(r"[0-9a-fA-F]{40}",args.base):
            raise ValueError("Not a full base SHA")
        raw=git("diff","--cached" if args.staged else "--name-only") if False else (
            git("diff","--cached","--name-only","--diff-filter=ACMR","-z") if args.staged
            else git("diff","--name-only","--diff-filter=ACMR","-z",args.base+"..HEAD")
        )
        names=sorted(set(x.decode("utf-8") for x in raw.split(b"\0") if x))
        findings=[]
        for path in names:
            if path.startswith("/") or ".." in path.split("/"):
                findings.append((path,"invalid_path",0))
                continue
            try:
                content=git("show",(":"+path) if args.staged else ("HEAD:"+path))
            except RuntimeError:
                findings.append((path,"unreadable_object",0))
                continue
            findings.extend((path,name,line) for name,line in inspect(path,content))
    except (RuntimeError,ValueError,UnicodeDecodeError):
        print("BLOCKED: preflight failed; no changed files authorized",file=sys.stderr)
        return 2
    for path,name,line in findings:
        print(f"BLOCKED: {path}:{line} {name}",file=sys.stderr)
    print(f"AI-security preflight: {len(names)} files; {len(findings)} findings")
    return 1 if findings else 0
if __name__=="__main__":raise SystemExit(main())
