"""Long-only, next-bar execution, fixed brackets, explicit simulated costs.

This is a bar simulation, not an Alpaca execution emulator. No broker calls.
"""
from dataclasses import dataclass, asdict
import math
import pandas as pd
from core.execution_safety import risk_quantity


@dataclass(frozen=True)
class BacktestPolicy:
    initial_cash: float = 100000
    risk_pct: float = .01
    stop_pct: float = .02
    take_pct: float = .04
    fee_bps: float = 1
    slippage_bps: float = 5
    whole_shares: bool = True

    def validate(self):
        if not all(math.isfinite(float(v)) for v in asdict(self).values()):
            raise ValueError('Non-finite backtest policy')
        if self.initial_cash <= 0 or not 0 < self.risk_pct < 1:
            raise ValueError('Invalid capital/risk')
        if not 0 < self.stop_pct < 1 or not 0 < self.take_pct < 1:
            raise ValueError('Invalid bracket')
        if not 0 <= self.fee_bps < 1000 or not 0 <= self.slippage_bps < 1000:
            raise ValueError('Invalid simulated costs')


def simulate(bars, signals, policy=BacktestPolicy(), *, initial_signal=0,
             calendar=None, timeframe=None, initial_signal_time=None):
    policy.validate()
    if bars.empty or not isinstance(bars.index, pd.DatetimeIndex):
        raise ValueError('Nonempty datetime-indexed bars required')
    if bars.index.tz is None or bars.index.hasnans or bars.index.has_duplicates or not bars.index.is_monotonic_increasing:
        raise ValueError('Sorted, unique, timezone-aware bars required')
    data = bars[['open','high','low','close','volume']].apply(pd.to_numeric)
    if not data.map(math.isfinite).all().all() or (data[['open','high','low','close']] <= 0).any().any():
        raise ValueError('Invalid bars')
    if ((data.high < data[['open','low','close']].max(axis=1)) |
        (data.low > data[['open','high','close']].min(axis=1)) | (data.volume < 0)).any():
        raise ValueError('Invalid candle range/volume')
    signal = pd.Series(signals).reindex(bars.index)
    if signal.isna().any() or not signal.isin([-1,0,1]).all():
        raise ValueError('Signals must align exactly with bars and be -1/0/1')
    if initial_signal not in (-1, 0, 1):
        raise ValueError('Invalid pre-window signal')
    cash, qty, entry, entry_fee, stop, take = policy.initial_cash, 0., 0., 0., 0., 0.
    entered_at = None
    fee = policy.fee_bps / 10000
    slip = policy.slippage_bps / 10000
    history, trades = [], []
    previous_equity = cash
    session_ends, duration = None, None
    if calendar is not None:
        from core.stock_sessions import session_windows
        session_ends,duration = session_windows(data.index,calendar,timeframe)
    elif timeframe is not None:
        raise ValueError('Explicit calendar required for session-aware simulation')
    protection_expires = None
    protection_active = True
    expirations, unprotected_bars = 0, 0
    for i, (timestamp, bar) in enumerate(data.iterrows()):
        regular = session_ends is None or pd.notna(session_ends.iloc[i])
        if qty > 0 and protection_expires is not None and timestamp >= protection_expires:
            protection_active = False
            protection_expires = None
            expirations += 1
        # The signal at t is only executable at t+1; the last signal has no fill.
        prior_signal = initial_signal if i == 0 else signal.iloc[i-1]
        decision_time = data.index[i-1] if i > 0 else initial_signal_time
        fresh_decision = session_ends is None or (decision_time is not None
            and pd.Timestamp(decision_time).tzinfo is not None
            and pd.Timestamp(decision_time)+duration == timestamp)
        # No stale signal carry across an overnight/missing-bar gap.
        if qty == 0 and regular and fresh_decision and prior_signal == 1:
            entry = bar.open * (1 + slip)
            qty = risk_quantity(cash, cash/(1+fee), entry, policy.stop_pct, policy.risk_pct)
            if policy.whole_shares: qty = float(int(qty))
            entry_fee = qty * entry * fee
            cash -= qty * entry + entry_fee
            stop, take = entry*(1-policy.stop_pct), entry*(1+policy.take_pct)
            entered_at = timestamp
            protection_active = True
            protection_expires = None if session_ends is None else session_ends.iloc[i]
        if qty > 0 and regular and protection_active:
            exit_price, reason = None, None
            if bar.open <= stop:
                exit_price, reason = bar.open, 'gap_stop'
            elif bar.open >= take:
                # Do not credit favorable gap improvement on the limit take.
                exit_price, reason = take, 'take_profit'
            elif bar.low <= stop:
                # Both levels touched: conservative stop-first, no invented path.
                exit_price, reason = stop, 'stop_loss'
            elif bar.high >= take:
                exit_price, reason = take, 'take_profit'
            if exit_price is not None:
                exit_price *= 1-slip
                exit_fee = qty * exit_price * fee
                pnl = qty*(exit_price-entry)-entry_fee-exit_fee
                cash += qty*exit_price-exit_fee
                trades.append(dict(entry_time=entered_at, exit_time=timestamp, qty=qty,
                    entry_price=entry, exit_price=exit_price, pnl=pnl,
                    fees=entry_fee+exit_fee, reason=reason))
                qty = 0.
                protection_expires = None
        if (qty > 0 and session_ends is not None and protection_expires is not None
                and timestamp+duration >= protection_expires):
            protection_active = False
            protection_expires = None
            expirations += 1
        if qty > 0 and not protection_active:
            unprotected_bars += 1
        equity = cash + qty * bar.close
        history.append(dict(timestamp=timestamp, close=bar.close, Position=qty,
            Equity=equity, StratReturn=equity/previous_equity-1,
            signal=int(signal.iloc[i]), regular_session=regular,
            protection_active=bool(qty > 0 and protection_active)))
        previous_equity = equity
    curve = pd.DataFrame(history).set_index('timestamp')
    closed = pd.DataFrame(trades)
    pnl_values = closed.pnl if not closed.empty else pd.Series(dtype=float)
    gains, losses = pnl_values[pnl_values > 0].sum(), -pnl_values[pnl_values < 0].sum()
    peaks = curve.Equity.cummax().clip(lower=policy.initial_cash)
    metrics = dict(total_return=curve.Equity.iloc[-1]/policy.initial_cash-1,
        max_drawdown=float((curve.Equity/peaks-1).min()), completed_trades=len(closed),
        win_rate=float((pnl_values > 0).mean()) if len(closed) else None,
        profit_factor=float(gains/losses) if losses > 0 else None,
        final_equity=float(curve.Equity.iloc[-1]),
        realized_pnl=float(pnl_values.sum()), open_quantity=qty,
        note='Open inventory marked to last close; not forced closed. Costs are assumptions.')
    if calendar is not None:
        metrics.update(session_policy='explicit broker calendar, regular-session fills only',
            bracket_tif='day',expired_protection_events=expirations,
            unprotected_inventory_bars=unprotected_bars,
            open_inventory_protected=bool(qty > 0 and protection_active),
            note='DAY exits expire at session close; inventory is NOT sold or re-protected. '
                 'Indicators retain all input sessions. Brackets use simulated fill, not actual broker quote.')
    # Short samples do not justify annualized Sharpe/CAGR claims.
    return curve, closed, metrics


def nonoverlapping_windows(length, warmup_bars, test_bars, step_bars=None):
    step_bars = test_bars if step_bars is None else step_bars
    if any(isinstance(value, bool) or not isinstance(value, int)
           for value in (length, warmup_bars, test_bars, step_bars)) or length < 0:
        raise ValueError('Window sizes must be integer bar counts')
    if min(warmup_bars, test_bars, step_bars) <= 0 or step_bars < test_bars:
        raise ValueError('Positive bar counts and nonoverlapping test windows required')
    end = warmup_bars
    while end + test_bars <= length:
        yield slice(end-warmup_bars, end), slice(end, end+test_bars)
        end += step_bars
