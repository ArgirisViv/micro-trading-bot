"""Offline-testable guards. These are not guarantees against gaps or slippage."""
from __future__ import annotations

import math
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, ROUND_DOWN


def risk_quantity(equity, cash, price, stop_pct, risk_pct):
    values = tuple(float(v) for v in (equity, cash, price, stop_pct, risk_pct))
    if not all(math.isfinite(v) and v > 0 for v in values):
        return 0.0
    equity, cash, price, stop_pct, risk_pct = values
    if stop_pct >= 1 or risk_pct >= 1:
        return 0.0
    # Use the FIXED stop actually used by the runtime, not an unrelated ATR.
    quantity = min(equity * risk_pct / (price * stop_pct), cash / price)
    return float(Decimal(str(quantity)).quantize(Decimal('0.000001'), rounding=ROUND_DOWN))


def reset_daily_state(state: dict, now: datetime) -> bool:
    if now.tzinfo is None:
        raise ValueError('Daily reset requires an aware timestamp')
    date = now.astimezone(timezone.utc).date().isoformat()
    if state.get('last_reset_date') == date:
        return False
    state.update(last_reset_date=date, daily_order_count=0,
                 daily_start_equity=None, trading_halted_today=False)
    return True


@contextmanager
def exclusive_runtime(path: str):
    """Linux/Docker: one trader per runtime volume, including scaled services."""
    import fcntl
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'a', encoding='utf-8') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('Another trader owns this runtime volume') from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
