"""
Unit tests for hirist_mcp.
"""
import sys
from pathlib import Path

workspace_dir = str(Path(__file__).resolve().parent.parent.parent)
if workspace_dir not in sys.path:
    sys.path.insert(0, workspace_dir)

import unittest
import base64
from hirist_mcp.server import mcp
from hirist_mcp import auth


class TestHiristMCP(unittest.TestCase):
    def test_mcp_initialization(self):
        self.assertEqual(mcp.name, "hirist-mcp")
        self.assertEqual(len(mcp._tool_manager._tools), 6)

    def test_tool_names(self):
        tools = mcp._tool_manager._tools
        expected_tools = [
            "manage_profile",
            "search_jobs",
            "get_job_details",
            "manage_job_pipeline",
            "manage_account",
            "manage_session",
        ]
        self.assertEqual(len(tools), 6)
        for tool_name in expected_tools:
            self.assertIn(tool_name, tools, f"Missing tool: {tool_name}")

    def test_decode_jwt(self):
        header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip("=")
        payload = base64.urlsafe_b64encode(b'{"id":"1234567","domain":"hirist.com","status":1}').decode().rstrip("=")
        dummy_jwt = f"{header}.{payload}.sig"
        decoded = auth.decode_jwt(dummy_jwt)
        self.assertEqual(decoded.get("id"), "1234567")
        self.assertEqual(decoded.get("domain"), "hirist.com")

    def test_build_cookie_header(self):
        header = auth.build_cookie_header("my_token", "sess123")
        self.assertIn("HIRIST_CK1=my_token", header)
        self.assertIn("hirist_seeker_enc=my_token", header)
        self.assertIn("PHPSESSID=sess123", header)

    def test_ttl_cache(self):
        from hirist_mcp.cache import TTLCache
        cache = TTLCache(default_ttl=10, max_size=5)
        cache.set("key1", "val1")
        self.assertEqual(cache.get("key1"), "val1")

        # Expiration test
        cache.set("short_key", "short_val", ttl=-1)
        self.assertIsNone(cache.get("short_key"))

        # Invalidation test
        cache.set("prefix_a", "val_a")
        cache.set("prefix_b", "val_b")
        cache.set("other", "val_other")
        cache.invalidate("prefix_")
        self.assertIsNone(cache.get("prefix_a"))
        self.assertIsNone(cache.get("prefix_b"))
        self.assertEqual(cache.get("other"), "val_other")

    def test_delete_profile_item_unsupported_type(self):
        from hirist_mcp import client, server
        st, res = client.delete_profile_item("unsupported_section", 12345)
        self.assertEqual(st, 400)
        self.assertIn("error", res)

        # server action requires item_id
        res_server = server.manage_profile(action="delete_item")
        self.assertEqual(res_server.get("status_code"), 400)
        self.assertIn("item_id is required", res_server.get("error", ""))


if __name__ == "__main__":
    unittest.main()
