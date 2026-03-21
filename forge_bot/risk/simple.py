from __future__ import annotations


def can_trade(current_gross_exposure: float, new_notional: float, max_gross_exposure: float) -> tuple[bool, str]:
    if current_gross_exposure + new_notional > max_gross_exposure:
        return False, "gross_exposure_limit"
    return True, "ok"


def within_daily_drawdown(total_pnl: float, max_daily_drawdown_usd: float) -> tuple[bool, str]:
    if total_pnl <= -abs(max_daily_drawdown_usd):
        return False, "daily_drawdown_limit"
    return True, "ok"
