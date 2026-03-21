from __future__ import annotations

import time
import requests


def floor_window(ts: int, seconds: int) -> int:
    return (ts // seconds) * seconds


class PolymarketData:
    def __init__(self, gamma_base: str = "https://gamma-api.polymarket.com", clob_base: str = "https://clob.polymarket.com"):
        self.gamma_base = gamma_base.rstrip("/")
        self.clob_base = clob_base.rstrip("/")

    def current_btc_5m_slug(self) -> str:
        return f"btc-updown-5m-{floor_window(int(time.time()), 300)}"

    def market_by_slug(self, slug: str):
        for url, params in [
            (f"{self.gamma_base}/markets/slug/{slug}", None),
            (f"{self.gamma_base}/markets", {"slug": slug, "limit": 5}),
        ]:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code != 200:
                continue
            data = r.json()
            if isinstance(data, dict) and data.get("slug"):
                return data
            if isinstance(data, list) and data:
                return data[0]
            if isinstance(data, dict) and isinstance(data.get("data"), list) and data["data"]:
                return data["data"][0]
        return None

    def extract_token_ids(self, market: dict):
        ids = market.get("clobTokenIds")
        if isinstance(ids, str):
            import json
            ids = json.loads(ids)
        if ids and len(ids) >= 2:
            return ids[0], ids[1]
        return None, None

    def midpoint(self, token_id: str):
        r = requests.get(f"{self.clob_base}/midpoint", params={"token_id": token_id}, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        mid = data.get("mid")
        return float(mid) if mid is not None else None
