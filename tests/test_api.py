import os
import secrets
import time
import unittest
from datetime import timezone
from unittest.mock import patch

from fastapi import Response

from api import index


class CloudApiContractTests(unittest.TestCase):
    def test_vercel_routes_include_api_prefix(self):
        paths = {route.path for route in index.app.routes}
        self.assertIn("/api/v1/health", paths)
        self.assertIn("/api/v1/auth/login", paths)
        self.assertIn("/api/v1/devices/pair", paths)
        self.assertIn("/api/v1/telemetry/snapshot", paths)
        self.assertIn("/api/v1/agent/jobs/claim", paths)
        self.assertIn("/api/v1/dashboard/devices/{device_id}/revoke", paths)

    def test_health_is_read_only(self):
        result = index.health()
        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["execution_enabled"])

    def test_login_issues_valid_signed_session_cookie(self):
        with patch.dict(os.environ, {
            "GHOST_DASHBOARD_PASSWORD": "test-dashboard-password",
            "GHOST_SESSION_SECRET": "test-session-secret-long-enough-for-unit-test",
        }):
            response = Response()
            result = index.login(index.LoginRequest(password="test-dashboard-password"), response)
            self.assertTrue(result["authenticated"])
            cookie = response.headers["set-cookie"]
            token = cookie.split("ghost_session=", 1)[1].split(";", 1)[0]
            self.assertTrue(index.valid_session(token))
            self.assertTrue(response.headers["set-cookie"].lower().find("httponly") >= 0)

    def test_expired_session_is_rejected(self):
        with patch.dict(os.environ, {"GHOST_SESSION_SECRET": "test-session-secret-long-enough-for-unit-test"}):
            expiry = str(int(time.time()) - 5)
            payload = expiry + "." + secrets.token_urlsafe(18)
            token = payload + "." + index.session_signature(payload)
            self.assertFalse(index.valid_session(token))


    def test_session_tokens_are_unique_even_within_the_same_second(self):
        with patch.dict(os.environ, {"GHOST_SESSION_SECRET": "test-session-secret-long-enough-for-unit-test"}):
            first = index.make_session()
            second = index.make_session()
            self.assertNotEqual(first, second)
            self.assertTrue(index.valid_session(first))
            self.assertTrue(index.valid_session(second))

    def test_mt5_export_timestamp_parses_as_utc(self):
        result = index.parse_export_time("2026.11.15 10:30:00")
        self.assertEqual(result.tzinfo, timezone.utc)
        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 11)
        self.assertEqual(result.day, 15)

    def test_job_types_are_allowlisted(self):
        job = index.JobCreateRequest(job_type="PING", params={})
        self.assertEqual(job.job_type, "PING")
        with self.assertRaises(Exception):
            index.JobCreateRequest(job_type="SHELL", params={"command": "whoami"})


if __name__ == "__main__":
    unittest.main()
