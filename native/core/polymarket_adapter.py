from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

import requests


GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE = "https://clob.polymarket.com"

ASSET_SYMBOLS = {
    "BTC": ["btc"],
    "ETH": ["eth"],
    "SOL": ["sol"],
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _get_json(url: str, params: dict[str, Any] | None = None, timeout: int = 10):
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _parse_clob_token_ids(raw):
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return []
    return raw if isinstance(raw, list) else []


def _midpoint(token_id: str) -> float | None:
    try:
        data = _get_json(f"{CLOB_BASE}/midpoint", params={"token_id": token_id}, timeout=8)
        mid = data.get("mid")
        return float(mid) if mid is not None else None
    except Exception:
        return None


def _infer_current_probability(market: dict) -> float | None:
    token_ids = _parse_clob_token_ids(market.get("clobTokenIds"))
    if token_ids:
        mid = _midpoint(token_ids[0])
        if mid is not None and 0.0 <= mid <= 1.0:
            return mid

    for key in ("probability", "currentProbability", "lastTradePrice", "price"):
        try:
            val = market.get(key)
            if val is not None:
                f = float(val)
                if 0.0 <= f <= 1.0:
                    return f
        except Exception:
            pass
    return None


def _normalize_market(row: dict) -> dict | None:
    if not row.get("active", True):
        return None
    if row.get("closed"):
        return None

    question = row.get("question") or row.get("title") or ""
    slug = row.get("slug") or ""
    cond_id = row.get("conditionId") or slug or row.get("id")
    resolves_at = row.get("endDate") or row.get("end_date_iso") or row.get("resolveDate") or row.get("resolvesAt")
    current_probability = _infer_current_probability(row)

    if not cond_id or not question or resolves_at is None or current_probability is None:
        return None

    return {
        "id": cond_id,
        "slug": slug,
        "question": question,
        "current_probability": current_probability,
        "resolves_at": resolves_at,
        "raw": row,
    }


def _market_by_slug(slug: str):
    for url, params in [
        (f"{GAMMA_BASE}/markets/slug/{slug}", None),
        (f"{GAMMA_BASE}/markets", {"slug": slug, "limit": 5}),
    ]:
        try:
            data = _get_json(url, params=params, timeout=10)
        except Exception:
            continue
        if isinstance(data, dict) and data.get("slug"):
            return data
        if isinstance(data, list) and data:
            return data[0]
        if isinstance(data, dict) and isinstance(data.get("data"), list) and data["data"]:
            return data["data"][0]
    return None


def _window_ts(step_sec: int, offset_steps: int = 0) -> int:
    now_ts = int(time.time())
    base = (now_ts // step_sec) * step_sec
    return base - (offset_steps * step_sec)


def _candidate_slugs() -> list[str]:
    slugs = []
    for asset, symbols in ASSET_SYMBOLS.items():
        _ = asset
        for sym in symbols:
            for tf_label, step_sec in (("5m", 300), ("15m", 900)):
                for offset in (0, 1):
                    slugs.append(f"{sym}-updown-{tf_label}-{_window_ts(step_sec, offset)}")
    return slugs


def fetch_active_markets(limit_per_query: int = 100) -> list[dict]:
    _ = limit_per_query
    out = []
    seen = set()
    for slug in _candidate_slugs():
        row = _market_by_slug(slug)
        if not row:
            continue
        norm = _normalize_market(row)
        if not norm:
            continue
        key = norm["id"]
        if key in seen:
            continue
        seen.add(key)
        out.append(norm)
    return out


def get_context(market_id: str) -> dict:
    # Minimal compatibility shim. Native Polymarket doesn't expose a Simmer-like context endpoint.
    return {"warnings": [], "market_id": market_id, "ts": int(time.time())}


def get_native_snapshot() -> dict:
    # Paper-mode compatibility shape mirroring the legacy Simmer snapshot contract.
    balance = 10000.0
    positions = []
    positions_value = 0.0
    me = {"balance": balance}
    pos = {"positions": positions, "total_value": positions_value}
    return {
        "headers": {},
        "me": me,
        "pos": pos,
        "balance": balance,
        "positions": positions,
        "positions_value": positions_value,
        "equity": balance + positions_value,
        "t_me_ms": 0,
        "t_pos_ms": 0,
        "ts": int(time.time()),
    }
