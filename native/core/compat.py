from __future__ import annotations

from native.core.polymarket_adapter import fetch_active_markets, get_context, get_native_snapshot


def get_snapshot(_key=None):
    return get_native_snapshot()


def fetch_markets():
    return fetch_active_markets()


def fetch_context(market_id: str):
    return get_context(market_id)
