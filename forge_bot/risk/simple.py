from __future__ import annotations


def can_trade(current_gross_exposure: float, new_notional: float, max_gross_exposure: float) -> tuple[bool, str]:
    if current_gross_exposure + new_notional > max_gross_exposure:
        return False, "gross_exposure_limit"
    return True, "ok"
