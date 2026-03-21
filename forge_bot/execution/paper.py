from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class PaperOrder:
    side: str
    price: float
    notional_usd: float
    shares: float
    status: str
    slug: Optional[str] = None


class PaperExecutor:
    def place(self, side: str, price: float, notional_usd: float, slug: str | None = None) -> PaperOrder:
        shares = notional_usd / max(price, 0.01)
        return PaperOrder(side=side, price=price, notional_usd=notional_usd, shares=shares, status="filled", slug=slug)
