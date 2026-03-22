from __future__ import annotations


def fair_probability_from_signal(signal: dict) -> tuple[float | None, str]:
    side = signal.get("side")
    conf = float(signal.get("confidence", 0.0) or 0.0)
    if side not in ("yes", "no"):
        return None, "no_side"

    # Confidence-linked fair probability independent of current market price.
    # This avoids circularly importing the market into the signal estimate.
    fair = min(0.90, max(0.52, 0.50 + 0.30 * conf))
    return fair, "ok"


def has_tradeable_edge(side: str, market_price: float, fair_prob: float, threshold: float) -> tuple[bool, float]:
    implied = market_price if side == "yes" else (1.0 - market_price)
    edge = fair_prob - implied
    return edge >= threshold, edge
