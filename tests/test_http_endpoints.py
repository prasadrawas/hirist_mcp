"""
Integration tests for Starlette routes and HTTP middleware in hirist_mcp.
"""
import sys
from pathlib import Path

workspace_dir = str(Path(__file__).resolve().parent.parent.parent)
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

import unittest
from starlette.testclient import TestClient
from hirist_mcp.server import app


class TestHttpEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_health_endpoint(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("service"), "hirist-mcp")

    def test_root_landing_page(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Hirist MCP Server", resp.text)
        self.assertIn("Connect to Claude Web", resp.text)

    def test_root_redirect_with_token(self):
        resp = self.client.get("/?token=test_token_abc", follow_redirects=False)
        self.assertEqual(resp.status_code, 307)
        self.assertIn("/sse?token=test_token_abc", resp.headers.get("location", ""))


if __name__ == "__main__":
    unittest.main()
