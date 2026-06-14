"""Tests for api.py."""

import json
import sys
import socket
import urllib.error
import urllib.request
from io import BytesIO
from pathlib import Path
from unittest import TestCase, main as ut_main
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.api import DeepSeekClient, DeepSeekAPIError, BASE_URL


def _mock_response(status_code: int = 200, body: dict = None):
    """Build a mock that simulates urlopen returning a JSON response."""
    body_bytes = json.dumps(body or {}).encode("utf-8")

    def mock_urlopen(req, timeout=15):
        resp = MagicMock()
        resp.read.return_value = body_bytes
        resp.__enter__ = MagicMock(return_value=resp)
        resp.__exit__ = MagicMock(return_value=False)
        if status_code >= 400:
            error = urllib.error.HTTPError(
                url="http://fake",
                code=status_code,
                msg="Error",
                hdrs=None,
                fp=BytesIO(body_bytes),
            )
            raise error
        return resp

    return mock_urlopen


class TestDeepSeekClient(TestCase):

    def setUp(self):
        self.client = DeepSeekClient("sk-test-123")

    def test_init_with_empty_key_raises(self):
        with self.assertRaises(ValueError):
            DeepSeekClient("")
        with self.assertRaises(ValueError):
            DeepSeekClient(None)

    def test_headers_include_bearer_token(self):
        h = self.client._headers()
        self.assertEqual(h["Authorization"], "Bearer sk-test-123")
        self.assertEqual(h["Content-Type"], "application/json")

    def test_get_balance_parses_response(self):
        data = {
            "is_available": True,
            "balance_infos": [{
                "currency": "CNY",
                "total_balance": "100.50",
                "granted_balance": "10.00",
                "topped_up_balance": "90.50",
            }],
        }
        with patch("urllib.request.urlopen", _mock_response(200, data)):
            result = self.client.get_balance()
            self.assertTrue(result["is_available"])
            self.assertEqual(result["balance_infos"][0]["total_balance"], "100.50")

    def test_get_models_returns_list(self):
        data = {"data": [
            {"id": "deepseek-chat", "object": "model", "owned_by": "deepseek"},
        ]}
        with patch("urllib.request.urlopen", _mock_response(200, data)):
            models = self.client.get_models()
            self.assertEqual(len(models), 1)
            self.assertEqual(models[0]["id"], "deepseek-chat")

    def test_401_raises_unauthorized(self):
        def raise_401(req, timeout=15):
            raise urllib.error.HTTPError(
                url="http://fake", code=401, msg="Unauthorized",
                hdrs=None, fp=BytesIO(b'{"error":"unauthorized"}'),
            )
        with patch("urllib.request.urlopen", raise_401):
            with self.assertRaises(DeepSeekAPIError) as ctx:
                self.client.get_balance()
            self.assertIn("401", str(ctx.exception))

    def test_402_raises_insufficient_balance(self):
        def raise_402(req, timeout=15):
            raise urllib.error.HTTPError(
                url="http://fake", code=402, msg="Payment Required",
                hdrs=None, fp=BytesIO(b""),
            )
        with patch("urllib.request.urlopen", raise_402):
            with self.assertRaises(DeepSeekAPIError) as ctx:
                self.client.get_balance()
            self.assertIn("402", str(ctx.exception))

    def test_429_raises_rate_limit(self):
        def raise_429(req, timeout=15):
            raise urllib.error.HTTPError(
                url="http://fake", code=429, msg="Too Many Requests",
                hdrs=None, fp=BytesIO(b""),
            )
        with patch("urllib.request.urlopen", raise_429):
            with self.assertRaises(DeepSeekAPIError) as ctx:
                self.client.get_balance()
            self.assertIn("429", str(ctx.exception))

    def test_connection_timeout_raises(self):
        def raise_timeout(req, timeout=15):
            raise urllib.error.URLError(socket.timeout("timed out"))
        with patch("urllib.request.urlopen", raise_timeout):
            with self.assertRaises(DeepSeekAPIError) as ctx:
                self.client.get_balance()
            self.assertIn("timed out", str(ctx.exception))

    def test_connection_refused_raises(self):
        def raise_refused(req, timeout=15):
            raise urllib.error.URLError(ConnectionRefusedError("refused"))
        with patch("urllib.request.urlopen", raise_refused):
            with self.assertRaises(DeepSeekAPIError) as ctx:
                self.client.get_balance()
            self.assertIn("Connection failed", str(ctx.exception))


if __name__ == "__main__":
    ut_main()
