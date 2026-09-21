"""Fail closed on malformed or incomplete provider candles; UTC bar START index."""
import re
import numpy as np
import pandas as pd


def bar_interval(timeframe):
    match = re.fullmatch(r'([1-9][0-9]*)(min|m|h|hour|day|Day|d)', timeframe)
    if not match:
        raise ValueError('Unsupported timeframe')
    number, unit = match.groups()
    return pd.Timedelta(int(number), unit={'min':'min', 'm':'min', 'h':'h',
        'hour':'h', 'day':'D', 'Day':'D', 'd':'D'}[unit])


def validated_bars(frame, timeframe, now=None, require_fresh=True):
    if frame is None or frame.empty:
        raise ValueError('No market bars')
    result = frame.copy()
    result.columns = result.columns.str.lower()
    columns = ['open', 'high', 'low', 'close', 'volume']
    if not all(column in result for column in columns):
        raise ValueError('Missing OHLCV columns')
    if not isinstance(result.index, pd.DatetimeIndex):
        raise ValueError('Provider must supply a datetime index')
    # Naive timestamps have unknown provenance: providers must explicitly use UTC.
    if result.index.tz is None or result.index.hasnans or result.index.has_duplicates:
        raise ValueError('Ambiguous or duplicate bar timestamps')
    result.index = result.index.tz_convert('UTC')
    result = result.sort_index()
    values = result[columns].apply(pd.to_numeric, errors='coerce')
    if not np.isfinite(values.to_numpy()).all():
        raise ValueError('Non-finite OHLCV')
    if (values[['open','high','low','close']] <= 0).any().any() or (values.volume < 0).any():
        raise ValueError('Invalid prices or volume')
    if ((values.high < values[['open','close','low']].max(axis=1)) |
        (values.low > values[['open','close','high']].min(axis=1))).any():
        raise ValueError('Inconsistent candle range')
    result[columns] = values
    interval = bar_interval(timeframe)
    current = pd.Timestamp.now(tz='UTC') if now is None else pd.Timestamp(now)
    if current.tzinfo is None:
        raise ValueError('Current time must be timezone-aware')
    current = current.tz_convert('UTC')
    if (result.index > current).any():
        raise ValueError('Future bar')
    result = result[result.index + interval <= current]
    if result.empty:
        raise ValueError('No completed bars')
    if require_fresh and current - (result.index[-1] + interval) > interval * 2:
        raise ValueError('Market bars are stale')
    return result
