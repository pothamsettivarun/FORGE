from __future__ import annotations

import requests


class BinanceFeed:
    def __init__(self, symbol: str = "BTCUSDT"):
        self.symbol = symbol

    def klines(self, interval: str = "1m", limit: int = 30) -> list[dict]:
        r = requests.get(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": self.symbol, "interval": interval, "limit": limit},
            timeout=10,
        )
        r.raise_for_status()
        rows = r.json()
        out = []
        for row in rows:
            out.append({
                "open_time": row[0],
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            })
        return out
