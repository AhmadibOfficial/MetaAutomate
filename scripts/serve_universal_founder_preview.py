#!/usr/bin/env python3
"""Safe founder preview for static site; free ephemeral loopback port.

Read-only HTTP server. Does not edit repositories, create customer accounts,
run migrations, start background jobs, buy services, or expose a public port.
"""
from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "apps/site"

class PreviewHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

def main():
    if not (SITE / "universal" / "index.html").is_file():
        raise SystemExit("STOP: Universal workspace source is missing")
    handler=partial(PreviewHandler,directory=str(SITE))
    try:
        with ThreadingHTTPServer(("127.0.0.1",0),handler) as server:
            port=server.server_address[1]
            print("MetaAutomate Founder Preview",flush=True)
            print(f"Homepage:  http://127.0.0.1:{port}/",flush=True)
            print(f"Workspace: http://127.0.0.1:{port}/universal/",flush=True)
            print("Press Ctrl+C to stop. No external services are connected.",flush=True)
            server.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt:
        print("\nFounder preview stopped.",flush=True)
    except OSError as error:
        raise SystemExit(f"STOP: Cannot start local preview: {error}") from error

if __name__=="__main__":
    main()
