#!/usr/bin/env python3
"""Keep the Instagram static demo derived from strictly validated synthetic inputs."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.synthetic_instagram_lead_pipeline import (
    FIXTURE, parse_instagram_fixture, build_committed_instagram_pipeline,
)

OUTPUT=ROOT/"apps/site/intelligence-lab/instagram/data.js"


def render() -> str:
    doc = parse_instagram_fixture(FIXTURE.read_bytes())
    report = build_committed_instagram_pipeline()
    assert report["controls"]["production_go"] is False
    assert report["metrics"]["actual_messages_sent"] == 0
    assert report["metrics"]["actual_leads_captured"] == 0
    return ("/* Generated from P2-03q strictly synthetic Instagram source — no credentials or PII. */\n"
            "window.MetaAutomateInstagramScenario = Object.freeze("
            + json.dumps(doc, sort_keys=True, ensure_ascii=True,
                         separators=(",", ":")) + ");\n")


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args=parser.parse_args()
    expected=render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != expected:
            print("FAIL: Instagram source-only contract missing or stale", file=sys.stderr)
            return 1
        print("PASS: Instagram UI data matches P2-03q verified example fixture")
        return 0
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(expected,encoding="utf-8")
    print("Wrote Instagram source-only browser data")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
