"""Deterministic offline evaluation. Fixed rules, no fitting or broker access."""
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
import importlib.metadata
import json
import math
from typing import Any
import pandas as pd
from core.backtest_engine import BacktestPolicy, simulate, nonoverlapping_windows
from data.bar_validation import validated_bars, bar_interval


VARIANTS = ('enhanced_technical', 'technical_no_volume', 'sma_only', 'always_long', 'cash')


def load_dataset(path, timeframe):
    """Never silently interpret a naive date as UTC or sort damaged input."""
    raw = Path(path).read_bytes()
    bars = pd.read_csv(path)
    bars.columns = bars.columns.str.lower()
    if bars.columns.has_duplicates or 'timestamp' not in bars:
        raise ValueError('Unique columns and timestamp required')
    timestamps = []
    for value in bars.pop('timestamp'):
        stamp = pd.Timestamp(value)
        if pd.isna(stamp) or stamp.tzinfo is None:
            raise ValueError('Every timestamp must contain an explicit timezone')
        timestamps.append(stamp.tz_convert('UTC'))
    bars.index = pd.DatetimeIndex(timestamps, name='timestamp')
    if not bars.index.is_monotonic_increasing:
        raise ValueError('Input timestamps must already be sorted')
    validated = validated_bars(bars, timeframe, require_fresh=False)
    if len(validated) != len(bars) or validated.empty:
        raise ValueError('Only completed historical bars accepted; no silent row removal')
    gaps = int((bars.index.to_series().diff().dropna() != bar_interval(timeframe)).sum())
    return validated, dict(sha256=sha256(raw).hexdigest(), rows=len(bars),
        start=bars.index[0].isoformat(), end=bars.index[-1].isoformat(),
        timeframe=timeframe, interval_discontinuities=gaps,
        warning='Discontinuities may be sessions or missing data; no calendar/coverage certification.')


def signals_for(bars, symbol, variant):
    if variant not in VARIANTS:
        raise ValueError('Unknown research variant')
    if variant == 'enhanced_technical':
        from scripts.backtesting.offline_backtest import research_signals
        return research_signals(bars, symbol)
    if variant == 'technical_no_volume':
        from core.enhanced_indicators import add_enhanced_indicators, generate_enhanced_signals
        return generate_enhanced_signals(add_enhanced_indicators(bars), require_volume=False)
    if variant == 'sma_only':
        fast = bars.close.rolling(10, min_periods=10).mean()
        slow = bars.close.rolling(30, min_periods=30).mean()
        return (fast > slow).astype(int)
    return pd.Series(int(variant == 'always_long'), index=bars.index)


def buy_hold(bars, policy):
    """Fully invested once at first test open, marked (not liquidated) at close."""
    policy.validate()
    fee, slip = policy.fee_bps/10000, policy.slippage_bps/10000
    price = float(bars.open.iloc[0])*(1+slip)
    qty = policy.initial_cash/(price*(1+fee))
    qty = float(math.floor(qty)) if policy.whole_shares else math.floor(qty*1e6)/1e6
    cash = policy.initial_cash-qty*price*(1+fee)
    equity = cash+qty*bars.close
    peaks = equity.cummax().clip(lower=policy.initial_cash)
    return dict(total_return=float(equity.iloc[-1]/policy.initial_cash-1),
        max_drawdown=float((equity/peaks-1).min()), final_equity=float(equity.iloc[-1]),
        open_quantity=qty, completed_trades=0,
        note='Full exposure, unlike risk-sized brackets; entry costs only, inventory marked not sold.')


def evaluate(bars, symbol, policy=BacktestPolicy(), warmup_bars=100, test_bars=100,
             *, calendar=None, timeframe=None):
    """Independent flat-start non-overlapping windows. No parameter selection.

    Not a continuous deployable portfolio: open lots are NOT carried between folds.
    Warmup has no fills; its final known signal may fill at first test open.
    """
    windows = list(nonoverlapping_windows(len(bars), warmup_bars, test_bars))
    if warmup_bars < 60 or not windows:
        raise ValueError('At least 60 warmup bars and one complete test window required')
    folds, artifacts = [], []
    for number, (warmup, test) in enumerate(windows):
        context = bars.iloc[warmup.start:test.stop]
        sample = bars.iloc[test]
        fold: dict[str, Any] = dict(fold=number, warmup_start=context.index[0].isoformat(),
            decision_time=bars.index[test.start-1].isoformat(),
            test_start=sample.index[0].isoformat(), test_end=sample.index[-1].isoformat(),
            test_rows=len(sample), variants={})
        for variant in VARIANTS:
            signals = signals_for(context, symbol, variant)
            curve, trades, metrics = simulate(sample, signals.loc[sample.index], policy,
                initial_signal=int(signals.iloc[warmup_bars-1]),
                calendar=calendar,timeframe=timeframe,
                initial_signal_time=bars.index[test.start-1])
            fold['variants'][variant] = metrics
            artifacts.append((number, variant, curve, trades))
        benchmark_sample = sample
        if calendar is not None:
            if timeframe is None:
                raise ValueError('Timeframe required for calendar-aware evaluation')
            from core.stock_sessions import session_windows
            endings,_ = session_windows(sample.index,calendar,timeframe)
            regular_positions = [i for i,value in enumerate(endings) if pd.notna(value)]
            if not regular_positions:
                raise ValueError('Test window has no regular-session bars')
            benchmark_sample=sample.iloc[regular_positions[0]:]
        fold['variants']['buy_hold'] = buy_hold(benchmark_sample, policy)
        folds.append(fold)
    return dict(protocol=('calendar-aware DAY independent-window evaluation v2'
                         if calendar is not None else 'fixed-rule independent-window evaluation v1'),
        policy=asdict(policy), warmup_bars=warmup_bars, test_bars=test_bars,
        evaluated_rows=len(windows)*test_bars,
        trailing_unevaluated_rows=len(bars)-windows[-1][1].stop,
        folds=folds, calendar_required=calendar is not None,
        excluded_overlays=['ML', 'regime', 'fundamentals', 'macro'],
        interpretation='No fitted models, tuning, statistical edge claim or compounded fold return. '
            'SMA-only is a rule-family ablation, not an isolated causal attribution. '
            'Always-long keeps bracket sizing; buy-hold uses full capital. '
            'Fold-start inventory resets omit carry risk; open lots are reported, not closed.'), artifacts


def save_report(output, report, artifacts, dataset, symbol):
    output = Path(output)
    # Refuse overwrite of a previous experiment or project directory.
    output.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[1]
    source = sha256()
    for directory in ('core', 'data', 'scripts/backtesting'):
        for path in sorted((root/directory).rglob('*.py')):
            source.update(str(path.relative_to(root)).encode())
            source.update(path.read_bytes())
    report['manifest'] = dict(dataset=dataset, symbol=symbol, source_sha256=source.hexdigest(),
        dependencies={name: importlib.metadata.version(name)
            for name in ('pandas', 'numpy', 'scikit-learn')},
        data_provenance='User-supplied CSV; vendor/adjustments/survivorship not independently verified.')
    (output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    for number, variant, curve, trades in artifacts:
        curve.to_csv(output/f'fold_{number}_{variant}_equity.csv')
        if trades.empty:
            trades = pd.DataFrame(columns=['entry_time','exit_time','qty','entry_price','exit_price','pnl','fees','reason'])
        trades.to_csv(output/f'fold_{number}_{variant}_trades.csv', index=False)
