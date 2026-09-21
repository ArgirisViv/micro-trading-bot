import json
import numpy as np
import pandas as pd
import pytest
from core.ml_model import create_features, train_and_save, load_model
from core.backtest_engine import simulate, BacktestPolicy, nonoverlapping_windows
from webapp.server import _backtest_trade_returns


def frame(prices):
    return pd.DataFrame(dict(open=prices, close=prices, high=prices, low=prices,
        volume=[10]*len(prices)), index=pd.date_range('2026-01-01', periods=len(prices),
        freq='5min', tz='UTC'))


def test_unknown_final_label_not_fabricated_and_latest_inference_present():
    bars = frame(list(range(100,180)))
    X,y = create_features(bars)
    assert X.index[-1] == bars.index[-1]
    assert pd.isna(y.iloc[-1])
    assert X.index[0] == bars.index[29]


def test_features_do_not_change_when_future_data_appended():
    bars = frame(list(range(100,180)))
    prefix,_ = create_features(bars.iloc[:60])
    complete,_ = create_features(bars)
    pd.testing.assert_frame_equal(prefix,complete.loc[prefix.index])


def test_training_purges_boundary_and_publishes_holdout_metadata(tmp_path):
    rng = np.random.default_rng(4)
    bars = frame((100+np.cumsum(rng.normal(0,.2,250))).tolist())
    path = str(tmp_path / 'own_model.joblib')
    train_and_save(bars,path)
    metadata = json.loads((tmp_path / 'own_model.joblib.json').read_text())
    assert metadata['purged_rows'] == 1
    assert metadata['training_end'] < metadata['holdout_start']
    assert load_model(path).orbit_schema == ['return','sma_fast','sma_slow','rsi']


def test_insufficient_training_does_not_save_dummy(tmp_path):
    with pytest.raises(ValueError): train_and_save(frame([100]*40),str(tmp_path/'model'))
    assert not (tmp_path/'model').exists()


def test_last_bar_signal_is_not_executed():
    bars = frame([100,100])
    _,trades,metrics = simulate(bars,pd.Series([0,1],index=bars.index))
    assert trades.empty
    assert metrics['open_quantity'] == 0


def test_signal_fills_next_open_not_previous_close():
    bars = frame([100,110,110])
    curve,trades,metrics = simulate(bars,pd.Series([1,0,0],index=bars.index),
        BacktestPolicy(fee_bps=0,slippage_bps=0))
    assert curve.Position.iloc[0] == 0
    assert curve.Position.iloc[1] > 0
    assert trades.empty
    assert metrics['completed_trades'] == 0
    assert metrics['total_return'] == 0


def test_both_levels_touched_stop_first():
    bars = frame([100,100])
    bars.iloc[1,bars.columns.get_loc('low')] = 95
    bars.iloc[1,bars.columns.get_loc('high')] = 110
    _,trades,metrics = simulate(bars,pd.Series([1,0],index=bars.index),
        BacktestPolicy(fee_bps=0,slippage_bps=0))
    assert trades.reason.iloc[0] == 'stop_loss'
    assert trades.pnl.iloc[0] == -1000
    assert metrics['win_rate'] == 0


def test_gap_stop_cannot_fill_at_favorable_stop_price():
    bars = frame([100,100,90])
    _,trades,_ = simulate(bars,pd.Series([1,0,0],index=bars.index),
        BacktestPolicy(fee_bps=0,slippage_bps=0))
    assert trades.exit_price.iloc[0] == 90
    assert trades.reason.iloc[0] == 'gap_stop'


def test_costs_reduce_equity_and_cash_never_overspent():
    bars = frame([100,100,105])
    _,trades,metrics = simulate(bars,pd.Series([1,0,0],index=bars.index))
    assert trades.fees.iloc[0] > 0
    assert metrics['final_equity'] == pytest.approx(100000+metrics['realized_pnl'])


def test_walkforward_refuses_overlap_and_labels_bar_counts():
    with pytest.raises(ValueError): list(nonoverlapping_windows(200,50,63,21))
    windows=list(nonoverlapping_windows(200,50,50))
    assert [window[1].start for window in windows] == [50,100,150]


def test_dashboard_does_not_close_terminal_open_trade():
    bars = pd.DataFrame({'position':[0,1,1],'strat_return':[0,.01,.02]})
    assert _backtest_trade_returns(bars) == []
