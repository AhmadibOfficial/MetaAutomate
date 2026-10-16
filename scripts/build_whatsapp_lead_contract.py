#!/usr/bin/env python3
"""Build or verify canonical, strictly synthetic WhatsApp lead preview data."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.synthetic_whatsapp_lead_pipeline import (
    FIXTURE, parse_whatsapp_fixture, build_committed_whatsapp_pipeline,
)

OUTPUT = ROOT / "apps/site/intelligence-lab/whatsapp/data.js"


def render():
    doc = parse_whatsapp_fixture(FIXTURE.read_bytes())
    report = build_committed_whatsapp_pipeline()
    assert not report["gates"]["messaging_active"]
    assert report["metrics"]["actual_messages_sent"] == 0
    return ("/* Only source-validated invented example leads. No phone, PII or messaging. */\n"
            "window.MetaAutomateWhatsAppScenario = Object.freeze("
            + json.dumps(doc, sort_keys=True, ensure_ascii=True,
                         separators=(",", ":")) + ");\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = render()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != expected:
            print("WhatsApp source-only browser contract stale", file=sys.stderr)
            return 1
        print("PASS: WhatsApp browser contract matches strict synthetic source")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(expected, encoding="utf-8")
    print("Wrote WhatsApp source-only browser contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
