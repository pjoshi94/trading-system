import base64
import json
import re
import time

import requests

from config import settings


_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

_BASE_HEADERS = {
    "User-Agent": _BROWSER_UA,
    "Accept": "application/json",
    "Origin": "https://moneyflows.com",
    "Referer": "https://moneyflows.com/",
}


class MoneyFlowsClient:

    def __init__(self):
        self._token: str | None = None

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def _is_token_valid(self) -> bool:
        if not self._token:
            return False
        try:
            payload_b64 = self._token.split(".")[1]
            # JWT base64url may lack padding
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            payload = json.loads(base64.b64decode(payload_b64))
            exp = payload.get("exp", 0)
            # Re-auth if expired or within 5 minutes of expiry
            return time.time() < (exp - 300)
        except Exception:
            return False

    def _authenticate(self):
        url = f"{settings.MONEYFLOWS_BASE_URL}{settings.MONEYFLOWS_AUTH_ENDPOINT}"
        resp = requests.post(
            url,
            json={
                "email": settings.MONEYFLOWS_EMAIL,
                "password": settings.MONEYFLOWS_PASSWORD,
            },
            headers=_BASE_HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        self._token = resp.json()["data"]["jwt"]

    def _headers(self) -> dict:
        if not self._is_token_valid():
            self._authenticate()
        return {**_BASE_HEADERS, "Authorization": f"Bearer {self._token}"}

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def _get(self, endpoint: str) -> list:
        url = f"{settings.MONEYFLOWS_BASE_URL}{endpoint}"
        resp = requests.get(url, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_latest_outlier50(self) -> dict:
        return self._get(settings.MONEYFLOWS_OUTLIER50_ENDPOINT)[0]

    def get_outlier50_by_page(self, page: int) -> dict | None:
        endpoint = f"/wp-json/wp/v2/outlier-50/?per_page=1&page={page}"
        try:
            results = self._get(endpoint)
            return results[0] if results else None
        except Exception:
            return None

    def get_latest_weekly_flows(self) -> dict:
        return self._get(settings.MONEYFLOWS_WEEKLY_ENDPOINT)[0]

    # ------------------------------------------------------------------
    # PDF URL extraction
    # ------------------------------------------------------------------

    @staticmethod
    def extract_pdf_url(post: dict) -> str | None:
        """Pull the PDF download href from a post's content.rendered field."""
        content = post.get("content", {}).get("rendered", "")
        match = re.search(r'href=["\']([^"\']+\.pdf[^"\']*)["\']', content)
        return match.group(1) if match else None
