from __future__ import annotations


def fair_probability_from_signal(signal: dict, market_price: float) -> tuple[float | None, str]:
    side = signal.get("side")
    conf = float(signal.get("confidence", 0.0) or 0.0)
    if side not in ("yes", "no"):
        return None, "no_side"

    edge = min(0.20, 0.02 + 0.25 * conf)
    if side == "yes":
        fair = min(0.99, float(market_price) + edge)
    else:
        fair = min(0.99, (1.0 - float(market_price)) + edge)
    return fair, "ok"


def has_tradeable_edge(side: str, market_price: float, fair_prob: float, threshold: float) -> tuple[bool, float]:
    if side == "yes":
        edge = fair_prob - market_price
    else:
        edge = fair_prob - (1.0 - market_price)
    return edge >= threshold, edge
