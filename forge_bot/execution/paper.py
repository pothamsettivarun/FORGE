from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PaperOrder:
    side: str
    price: float
    notional_usd: float
    status: str


class PaperExecutor:
    def place(self, side: str, price: float, notional_usd: float) -> PaperOrder:
        return PaperOrder(side=side, price=price, notional_usd=notional_usd, status="filled")
