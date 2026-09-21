from datetime import datetime, timezone
import math
import pandas as pd
import pytest
from core.execution_safety import risk_quantity, reset_daily_state, exclusive_runtime
from data.bar_validation import validated_bars, bar_interval
from core.enhanced_strategy import EnhancedStrategy
from data import hybrid_fetch
from scripts.paper_trading import multi_asset_loop as loop


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), -1, 0])
@pytest.mark.parametrize('field', range(5))
def test_sizing_rejects_nonfinite_or_nonpositive(bad, field):
    inputs = [100000, 10000, 100, .02, .01]
    inputs[field] = bad
    assert risk_quantity(*inputs) == 0


def test_sizing_uses_actual_stop_not_atr(monkeypatch):
    monkeypatch.setattr(loop, 'RISK_PER_TRADE', .01)
    monkeypatch.setattr(loop, 'STOP_LOSS_PCT', .02)
    quantity = loop._position_size_from_atr(100000, 100000, 100, .01)
    assert quantity == 500
    assert quantity * 100 * .02 <= 100000 * .01


def test_quantity_rounds_down_not_up():
    quantity = risk_quantity(100000, 1, 3, .02, .01)
    assert quantity * 3 <= 1


def test_reset_works_without_process_restart():
    state = dict(last_reset_date='2026-09-15', daily_order_count=100,
                 daily_start_equity=10000, trading_halted_today=True)
    assert reset_daily_state(state, datetime(2026,9,16,tzinfo=timezone.utc))
    assert state['daily_order_count'] == 0
    assert state['daily_start_equity'] is None
    assert not state['trading_halted_today']
    state['daily_order_count'] = 3
    assert not reset_daily_state(state, datetime(2026,9,16,12,tzinfo=timezone.utc))
    assert state['daily_order_count'] == 3


def test_reset_rejects_naive_time():
    with pytest.raises(ValueError):
        reset_daily_state({}, datetime(2026,9,16))


def bars():
    return pd.DataFrame(dict(Open=[100,101,102], High=[102,103,104],
        Low=[99,100,101], Close=[101,102,103], Volume=[10,20,30]),
        index=pd.date_range('2026-09-16T10:00Z', periods=3, freq='5min'))


def test_completed_candles_only_and_normalized_columns():
    result = validated_bars(bars(), '5min', now='2026-09-16T10:12Z')
    assert len(result) == 2
    assert 'close' in result


@pytest.mark.parametrize('problem', ['naive','duplicate','nan','negative','range','future','stale'])
def test_bad_bars_fail_closed(problem):
    frame = bars()
    now = '2026-09-16T10:16Z'
    if problem == 'naive': frame.index = frame.index.tz_localize(None)
    elif problem == 'duplicate': frame.index = [frame.index[0]] * 3
    elif problem == 'nan': frame.iloc[0,0] = math.nan
    elif problem == 'negative': frame.iloc[0,4] = -1
    elif problem == 'range': frame.iloc[0,1] = 50
    elif problem == 'future': now = '2026-09-16T10:01Z'
    elif problem == 'stale': now = '2026-09-16T11:00Z'
    with pytest.raises(ValueError):
        validated_bars(frame, '5min', now=now)


def test_unsupported_timeframe_rejected():
    with pytest.raises(ValueError): bar_interval('1week')


def test_low_pe_improves_not_degrades_score():
    strategy = EnhancedStrategy()
    assert strategy._calculate_fundamental_score({'pe':10}) > strategy._calculate_fundamental_score({'pe':90})
    assert strategy._calculate_fundamental_score({'pe':None}) == .5


def test_regime_adaptation_disabled_until_causal_implementation():
    assert not EnhancedStrategy().enable_regime_adaptation


def test_routing_never_uses_crypto_substring(monkeypatch):
    monkeypatch.setattr(hybrid_fetch, 'STOCK_WATCHLIST', ['SOLVENT'])
    monkeypatch.setattr(hybrid_fetch, 'CRYPTO_WATCHLIST', ['SOLUSD'])
    assert not hybrid_fetch.is_crypto_symbol('SOLVENT')
    assert hybrid_fetch.is_crypto_symbol('SOLUSD')
    with pytest.raises(ValueError): hybrid_fetch.is_crypto_symbol('UNKNOWN')


def test_second_trader_rejected(tmp_path):
    pytest.importorskip('fcntl')
    with exclusive_runtime(str(tmp_path / 'trader.lock')):
        with pytest.raises(RuntimeError):
            with exclusive_runtime(str(tmp_path / 'trader.lock')): pass
