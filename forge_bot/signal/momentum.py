from __future__ import annotations


def build_momentum_signal(closes: list[float]) -> dict:
    if len(closes) < 6:
        return {"side": None, "confidence": 0.0, "reason": "insufficient_data"}

    r1 = (closes[-1] / closes[-2] - 1) * 100
    r3 = (closes[-1] / closes[-4] - 1) * 100
    r5 = (closes[-1] / closes[-6] - 1) * 100
    rets = [(closes[i] / closes[i - 1] - 1) * 100 for i in range(1, len(closes))]
    mean15 = sum(rets[-15:]) / min(15, len(rets))
    vol = (sum((x - mean15) ** 2 for x in rets[-15:]) / min(15, len(rets))) ** 0.5

    score = 0
    score += 1 if r1 > 0 else -1 if r1 < 0 else 0
    score += 2 if r3 > 0 else -2 if r3 < 0 else 0
    score += 2 if r5 > 0 else -2 if r5 < 0 else 0

    strength = abs(r3) + abs(r5)
    if vol > 0.18 or strength < 0.11:
        return {"side": None, "confidence": 0.0, "r1": r1, "r3": r3, "r5": r5, "vol": vol, "score": score, "reason": "weak_or_choppy"}

    side = "yes" if score >= 3 else "no" if score <= -3 else None
    conf = min(1.0, max(0.0, (strength / 0.30) * (1.0 - min(vol, 0.20) / 0.20)))
    return {"side": side, "confidence": conf if side else 0.0, "r1": r1, "r3": r3, "r5": r5, "vol": vol, "score": score, "reason": "ok" if side else "no_clear_edge"}
