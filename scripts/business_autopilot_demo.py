#!/usr/bin/env python3
"""Local synthetic demo; never starts Docker, migrates a DB or contacts a provider."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))

from app.business_autopilot import SCENARIOS, replay, strict_json, verify_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    serve = subs.add_parser("serve", help="Open the local browser demonstration")
    serve.add_argument("--port", type=int, default=8090)
    sim = subs.add_parser("replay", help="Reproduce synthetic evidence on stdout; no server")
    sim.add_argument("--scenario", choices=SCENARIOS, default="standard")
    verify = subs.add_parser("verify", help="Compare a JSON artifact with the committed synthetic reference")
    verify.add_argument("artifact", type=Path)
    args = parser.parse_args()
    if args.command == "serve":
        import uvicorn
        from app.business_autopilot_demo import create_demo_app
        app = create_demo_app(args.port)
        print(f"MetaAutomate Business Autopilot: http://127.0.0.1:{args.port}", flush=True)
        print("Synthetic demonstration only. No real login, customer data or external execution.", flush=True)
        uvicorn.run(app, host="127.0.0.1", port=args.port,
                    proxy_headers=False, access_log=False, log_level="warning")
        return 0
    if args.command == "replay":
        run = replay(args.scenario)
        run.verify()
        print(json.dumps(run.bundle(), indent=2, ensure_ascii=False))
        return 0
    try:
        # Bounded regular local file input; never fetched from a URL.
        if not args.artifact.is_file():
            raise ValueError("Choose a regular local JSON file")
        with args.artifact.open("rb") as stream:
            candidate = strict_json(stream.read(128 * 1024 + 1))
        result = verify_bundle(candidate)
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"verified": False, "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2))
    return 0 if result["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
