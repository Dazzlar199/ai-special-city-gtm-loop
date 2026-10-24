#!/usr/bin/env python3
import argparse
import contextlib
import http.server
import json
import os
import socketserver
import subprocess
import threading
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from discovery.discover import run_discovery
from discovery.store import DiscoveryStore


HOST = "127.0.0.1"
PORT = 4177
ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_STORE = DiscoveryStore(Path(ROOT) / "data" / "discovery-results.json")


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    store = DEFAULT_STORE
    discovery_runner = staticmethod(run_discovery)
    discovery_lock = threading.Lock()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def _json(self, status, payload):
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"ok")
            return
        if path == "/api/prospects":
            try:
                self._json(200, self.store.read())
            except ValueError as error:
                self._json(500, {"error": str(error)})
            return
        if path == "/api/discovery-status":
            try:
                payload = self.store.read()
                self._json(200, {**payload.get("run", {}), "source_errors": payload.get("source_errors", [])})
            except ValueError as error:
                self._json(500, {"status": "failed", "error": str(error)})
            return
        super().do_GET()

    def do_POST(self):
        if urlparse(self.path).path != "/api/discover":
            self._json(404, {"error": "not found"})
            return
        try:
            length = min(int(self.headers.get("Content-Length", "0")), 16_384)
            body = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._json(400, {"error": "invalid JSON"})
            return
        if body.get("confirmed") is not True:
            self._json(400, {"error": "explicit confirmation is required"})
            return
        try:
            limit = max(1, min(int(body.get("limit", 12)), 25))
        except (TypeError, ValueError):
            self._json(400, {"error": "limit must be an integer from 1 to 25"})
            return
        categories = body.get("categories") if isinstance(body.get("categories"), list) else None
        if not self.discovery_lock.acquire(blocking=False):
            self._json(409, {"error": "discovery is already running"})
            return
        try:
            payload = self.discovery_runner(limit=limit, categories=categories)
            payload.setdefault("run", {})["outbound_messages_sent"] = 0
            self.store.write(payload)
            self._json(200, {
                "status": payload["run"].get("status", "complete"),
                "accepted_limit": limit,
                "found": payload["run"].get("found", len(payload.get("candidates", []))),
                "outbound_messages_sent": 0,
            })
        except Exception as error:
            self._json(502, {"status": "failed", "error": str(error)[:500], "outbound_messages_sent": 0})
        finally:
            self.discovery_lock.release()

    def log_message(self, format, *args):
        return


class ReusableTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def create_server(host=HOST, port=PORT, store=None, discovery_runner=None):
    handler = type("ConfiguredDashboardHandler", (DashboardHandler,), {})
    if store is not None:
        handler.store = store
    if discovery_runner is not None:
        handler.discovery_runner = staticmethod(discovery_runner)
    handler.discovery_lock = threading.Lock()
    return ReusableTCPServer((host, port), handler)


def open_window(url):
    chrome = "/Applications/Google Chrome.app"
    if os.path.exists(chrome):
        subprocess.Popen(["open", "-na", "Google Chrome", "--args", f"--app={url}"])
    else:
        subprocess.Popen(["open", url])


def server_is_running():
    with contextlib.suppress(Exception):
        with urllib.request.urlopen(f"http://{HOST}:{PORT}/health", timeout=0.4) as response:
            return response.read() == b"ok"
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()
    url = f"http://{HOST}:{PORT}/"

    if server_is_running():
        if not args.no_open:
            open_window(url)
        return

    with create_server(HOST, PORT) as server:
        if not args.no_open:
            threading.Thread(target=lambda: (time.sleep(0.35), open_window(url)), daemon=True).start()
        server.serve_forever()


if __name__ == "__main__":
    main()
