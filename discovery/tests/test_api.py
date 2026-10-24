import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from discovery.store import DiscoveryStore
from serve import create_server


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = DiscoveryStore(Path(self.temp.name) / "results.json")
        self.store.write({"run": {"status": "idle"}, "candidates": [], "source_errors": []})
        self.server = create_server("127.0.0.1", 0, store=self.store, discovery_runner=lambda **_: {"run": {"status": "complete"}, "candidates": [], "source_errors": []})
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.temp.cleanup()

    def get_json(self, path):
        with urllib.request.urlopen(self.base + path) as response:
            return json.load(response)

    def test_reads_prospects_and_status(self):
        self.assertEqual(self.get_json("/api/prospects")["candidates"], [])
        self.assertEqual(self.get_json("/api/discovery-status")["status"], "idle")

    def test_discovery_requires_explicit_confirmation_and_is_bounded(self):
        request = urllib.request.Request(
            self.base + "/api/discover",
            data=json.dumps({"confirmed": True, "limit": 999, "categories": ["공방"]}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            body = json.load(response)
        self.assertEqual(body["accepted_limit"], 25)
        self.assertEqual(body["outbound_messages_sent"], 0)

        denied = urllib.request.Request(self.base + "/api/discover", data=b"{}", method="POST")
        with self.assertRaises(urllib.error.HTTPError) as context:
            urllib.request.urlopen(denied)
        self.assertEqual(context.exception.code, 400)

    def test_invalid_limit_returns_400_without_running_discovery(self):
        request = urllib.request.Request(
            self.base + "/api/discover",
            data=json.dumps({"confirmed": True, "limit": "many"}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with self.assertRaises(urllib.error.HTTPError) as context:
            urllib.request.urlopen(request)
        self.assertEqual(context.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
