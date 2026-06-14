"""
DeepSeek API client - handles all communication with the DeepSeek API.
Uses urllib only (no requests dependency).
"""

import json
import socket
import urllib.request
import urllib.error
from typing import Optional, List, Dict, Any


BASE_URL = "https://api.deepseek.com"


class DeepSeekAPIError(Exception):
    """API request failed."""
    pass


class DeepSeekClient:
    """Lightweight DeepSeek API client using urllib."""

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("API key cannot be empty")
        self.api_key = api_key

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _request(self, method: str, path: str, payload: Optional[Dict] = None,
                 timeout: int = 15) -> Dict[str, Any]:
        """Execute an HTTP request and return parsed JSON.

        Centralises error handling for all API calls.
        """
        url = f"{BASE_URL}{path}"
        data = json.dumps(payload).encode("utf-8") if payload else None
        req = urllib.request.Request(url, data=data, headers=self._headers(), method=method)

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            if e.code == 401:
                raise DeepSeekAPIError("Invalid API Key (401 Unauthorized)")
            elif e.code == 402:
                raise DeepSeekAPIError("Insufficient balance (402)")
            elif e.code == 429:
                raise DeepSeekAPIError("Rate limit exceeded (429)")
            else:
                raise DeepSeekAPIError(f"HTTP {e.code}: {body[:200]}")
        except urllib.error.URLError as e:
            reason = e.reason
            if isinstance(reason, (socket.timeout, TimeoutError)):
                raise DeepSeekAPIError("Request timed out")
            raise DeepSeekAPIError(f"Connection failed: {reason}")

    def get_balance(self) -> Dict[str, Any]:
        """
        GET /user/balance
        Returns: { is_available, balance_infos: [{ currency, total_balance, granted_balance, topped_up_balance }] }
        """
        return self._request("GET", "/user/balance")

    def get_models(self) -> List[Dict[str, str]]:
        """
        GET /models
        Returns list of { id, object, owned_by } dicts.
        """
        data = self._request("GET", "/models")
        return data.get("data", [])
