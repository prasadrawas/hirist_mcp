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
from hirist_mcp import client, auth


class TestHiristMCP(unittest.TestCase):
    def test_mcp_initialization(self):
        self.assertEqual(mcp.name, "hirist-mcp")
        self.assertGreaterEqual(len(mcp._tool_manager._tools), 20)

    def test_tool_names(self):
        tools = mcp._tool_manager._tools
        expected_tools = [
            "validate_session",
            "get_profile",
            "get_full_profile_v2",
            "update_personal_details",
            "update_work_experience",
            "update_education",
            "update_additional_info",
            "get_key_skills",
            "update_key_skills",
            "get_cover_letter",
            "update_cover_letter",
            "touch_profile_pulse",
            "get_job_feed",
            "search_jobs",
            "get_job_details",
            "apply_to_job",
            "save_job",
            "unsave_job",
            "do_follow_up",
            "get_applied_job_count",
            "get_pending_jobs_count",
            "get_user_settings",
            "update_user_settings",
            "get_blocked_companies",
            "block_or_unblock_company",
            "suggest_companies",
            "suggest_institutes",
            "download_resume",
        ]
        for tool_name in expected_tools:
            self.assertIn(tool_name, tools, f"Missing tool: {tool_name}")

    def test_decode_jwt(self):
        header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip("=")
        payload = base64.urlsafe_b64encode(b'{"id":"5552070","domain":"hirist.com","status":1}').decode().rstrip("=")
        dummy_jwt = f"{header}.{payload}.sig"
        decoded = auth.decode_jwt(dummy_jwt)
        self.assertEqual(decoded.get("id"), "5552070")
        self.assertEqual(decoded.get("domain"), "hirist.com")

    def test_build_cookie_header(self):
        header = auth.build_cookie_header("my_token", "sess123")
        self.assertIn("HIRIST_CK1=my_token", header)
        self.assertIn("hirist_seeker_enc=my_token", header)
        self.assertIn("PHPSESSID=sess123", header)


if __name__ == "__main__":
    unittest.main()
