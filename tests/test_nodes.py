# Copyright (C) 2026 Hardy (todo1971) <hb@308-arms.de>
# SPDX-License-Identifier: GPL-3.0-only
import http.client
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import app


class CollectorHandler(BaseHTTPRequestHandler):
    calls = []
    redirect = False

    def do_GET(self):
        self.calls.append((self.path, dict(self.headers)))
        if self.redirect:
            self.send_response(302)
            self.send_header("Location", "http://192.0.2.1/")
            self.end_headers()
            return
        self.send_response(200)
        streaming = self.path == "/api/events"
        self.send_header("Content-Type", "text/event-stream" if streaming else "application/json")
        self.end_headers()
        self.wfile.write(b"event: sample\ndata: {}\n\n" if streaming else b'{"source":"collector"}')

    def log_message(self, *args):
        pass


class NodeGatewayTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "nodes.json"
        self.settings = patch.object(app, "NODES_FILE", str(self.path))
        self.settings.start()
        self.rate_limit = patch.object(app, "allow_request", return_value=True)
        self.rate_limit.start()
        CollectorHandler.calls = []
        CollectorHandler.redirect = False
        self.collector = ThreadingHTTPServer(("127.0.0.1", 0), CollectorHandler)
        self.gateway = app.DashboardHTTPServer(("127.0.0.1", 0), app.Handler)
        for server in (self.collector, self.gateway):
            threading.Thread(target=server.serve_forever, daemon=True).start()
        self.config = {"local_name": "Primary", "nodes": [{
            "id": "other", "name": "Second node", "url": f"http://127.0.0.1:{self.collector.server_port}",
        }]}
        self.write_config()

    def tearDown(self):
        for server in (self.gateway, self.collector):
            server.shutdown()
            server.server_close()
        self.rate_limit.stop()
        self.settings.stop()
        self.directory.cleanup()

    def write_config(self):
        self.path.write_text(json.dumps(self.config), encoding="utf-8")

    def request(self, path, method="GET"):
        connection = http.client.HTTPConnection("127.0.0.1", self.gateway.server_port, timeout=5)
        try:
            connection.request(method, path, headers={"Authorization": "secret", "Cookie": "private=value"})
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def test_registry_omits_internal_addresses_and_missing_file_keeps_local(self):
        status, body = self.request("/api/nodes")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["nodes"], [{"id": "local", "name": "Primary"}, {"id": "other", "name": "Second node"}])
        self.assertNotIn(b"127.0.0.1", body)
        self.path.unlink()
        self.assertEqual(len(app.configured_nodes()), 1)

    def test_remote_data_and_query_use_only_configured_collector(self):
        status, body = self.request("/api/nodes/other/history?range=12h&timezone=Europe%2FBerlin&url=http://192.0.2.1")
        self.assertEqual((status, json.loads(body)), (200, {"source": "collector"}))
        path, headers = CollectorHandler.calls[-1]
        self.assertEqual(path, "/api/history?range=12h&timezone=Europe%2FBerlin")
        self.assertNotIn("Authorization", headers)
        self.assertNotIn("Cookie", headers)

    def test_remote_stream_is_forwarded_and_releases_slot(self):
        status, body = self.request("/api/nodes/other/events")
        self.assertEqual((status, body), (200, b"event: sample\ndata: {}\n\n"))

    def test_admin_mutations_and_unknown_nodes_never_reach_collector(self):
        for path in ("/api/nodes/other/admin/status", "/api/nodes/other/rpc", "/api/nodes/missing/dashboard", "/api/nodes/other/../dashboard"):
            self.assertEqual(self.request(path)[0], 404)
        self.assertEqual(self.request("/api/nodes/other/dashboard", "POST")[0], 404)
        self.assertEqual(CollectorHandler.calls, [])

    def test_failed_collector_has_no_local_fallback(self):
        self.config["nodes"][0]["url"] = "http://127.0.0.1:1"
        self.write_config()
        status, body = self.request("/api/nodes/other/dashboard")
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(body), {"error": "Selected node unavailable"})

    def test_invalid_configuration_and_non_loopback_urls_fail_closed(self):
        for url in ("http://192.0.2.1:8787", "http://localhost:8787", "http://user:password@127.0.0.1:8787", "http://127.0.0.1:8787/admin", "https://127.0.0.1:8787", "http://127.0.0.1"):
            with self.subTest(url=url):
                self.config["nodes"][0]["url"] = url
                self.write_config()
                self.assertEqual(self.request("/api/nodes/other/dashboard")[0], 503)
        self.assertEqual(CollectorHandler.calls, [])

    def test_redirect_does_not_leave_collector(self):
        CollectorHandler.redirect = True
        self.assertEqual(self.request("/api/nodes/other/dashboard")[0], 503)
        self.assertEqual(len(CollectorHandler.calls), 1)


if __name__ == "__main__":
    unittest.main()
