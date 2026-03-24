from __future__ import annotations

import json
from pprint import pprint

from core.polymarket_adapter import fetch_active_markets, get_context, get_native_snapshot


def main():
    snap = get_native_snapshot()
    markets = fetch_active_markets()
    print("NATIVE SNAPSHOT")
    pprint(snap)
    print(f"\nMARKETS FOUND: {len(markets)}")
    for m in markets:
        print(json.dumps({
            "id": m["id"],
            "slug": m["slug"],
            "current_probability": m["current_probability"],
            "question": m["question"],
            "resolves_at": m["resolves_at"],
            "context": get_context(m["id"]),
        }, default=str))


if __name__ == "__main__":
    main()
