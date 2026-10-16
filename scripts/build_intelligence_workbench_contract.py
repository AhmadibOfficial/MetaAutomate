#!/usr/bin/env python3
"""Build the exact static Intelligence Workbench fixture from validated Python."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"apps/api"))
from app.synthetic_intelligence_project_architect import SOURCE,parse_project_library

OUTPUT=ROOT/"apps/site/intelligence/data.js"


def render() -> str:
    d=parse_project_library(SOURCE.read_bytes())
    return ("/* Generated from strictly validated P2-03u fictional project templates. */\n"
            "window.MetaAutomateIntelligenceTemplates = Object.freeze("
            +json.dumps(d,sort_keys=True,separators=(",",":"),ensure_ascii=True)
            +");\n")


def main() -> int:
    p=argparse.ArgumentParser()
    p.add_argument("--check",action="store_true")
    args=p.parse_args()
    expected=render()
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != expected:
            print("FAIL: intelligence browser template contract differs from Python source",
                  file=sys.stderr)
            return 1
        print("PASS: Intelligence Workbench matches exact strict Python scenario source")
        return 0
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(expected,encoding="utf-8")
    print("Wrote source-only Intelligence Workbench browser contract")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
