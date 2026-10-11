import json
import numpy as np
import pandas as pd
import pytest
from core.backtest_engine import BacktestPolicy, simulate
from core.research_pipeline import load_dataset, evaluate, signals_for, save_report, buy_hold, VARIANTS


def bars(n=310):
    rng = np.random.default_rng(27)
    close = 100+np.cumsum(rng.normal(0,.4,n))
    return pd.DataFrame(dict(open=close, high=close+1, low=close-1, close=close,
        volume=rng.integers(1,1000,n)), index=pd.date_range('2025-01-01', periods=n, freq='5min', tz='UTC'))


@pytest.mark.parametrize('variant', VARIANTS)
def test_signals_prefix_invariant(variant):
    data = bars()
    pd.testing.assert_series_equal(signals_for(data.iloc[:210], 'AAPL', variant),
        signals_for(data, 'AAPL', variant).iloc[:210])


def test_future_changes_do_not_change_completed_folds():
    data = bars()
    first, _ = evaluate(data, 'AAPL', warmup_bars=100, test_bars=100)
    changed = data.copy()
    changed.iloc[200:, :4] *= 2
    second, _ = evaluate(changed, 'AAPL', warmup_bars=100, test_bars=100)
    assert first['folds'][0] == second['folds'][0]
    assert first['evaluated_rows'] == 200
    assert first['trailing_unevaluated_rows'] == 10
    assert str(first['folds'][0]['test_end']) < str(first['folds'][1]['test_start'])


def test_prior_warmup_signal_fills_first_test_open():
    data = bars(2)
    _, trades, metrics = simulate(data, pd.Series(0,index=data.index),
        BacktestPolicy(fee_bps=0,slippage_bps=0), initial_signal=1)
    assert metrics['open_quantity'] > 0
    assert trades.empty


def test_buy_hold_costs_cash_and_open_lot():
    data = bars(3)
    data.loc[:,['open','high','low','close']] = 100
    assert buy_hold(data, BacktestPolicy(fee_bps=0,slippage_bps=0))['total_return'] == 0
    result = buy_hold(data, BacktestPolicy())
    assert float(result['total_return']) < 0
    assert result['completed_trades'] == 0


@pytest.mark.parametrize('damage', ['naive','reverse','duplicate','future','ohlc'])
def test_csv_rejects_ambiguous_or_bad_data(tmp_path,damage):
    data = bars(3)
    if damage == 'naive': data.index = pd.DatetimeIndex(data.index).tz_localize(None)
    if damage == 'reverse': data = data.iloc[::-1]
    if damage == 'duplicate': data.index = pd.DatetimeIndex([data.index[0]]*3)
    if damage == 'future': data.index = pd.date_range('2099-01-01',periods=3,freq='5min',tz='UTC')
    if damage == 'ohlc': data['low'] = 500
    path = tmp_path/'bars.csv'
    data.to_csv(path,index_label='timestamp')
    with pytest.raises(ValueError): load_dataset(path,'5min')


def test_report_hash_and_no_overwrite(tmp_path):
    path = tmp_path/'bars.csv'
    bars(200).to_csv(path,index_label='timestamp')
    data, provenance = load_dataset(path,'5min')
    report, artifacts = evaluate(data,'AAPL')
    output = tmp_path/'experiment'
    save_report(output,report,artifacts,provenance,'AAPL')
    saved = json.loads((output/'report.json').read_text())
    assert len(saved['manifest']['dataset']['sha256']) == 64
    assert len(saved['manifest']['source_sha256']) == 64
    assert saved['folds'][0]['variants']['cash']['final_equity'] == 100000
    assert pd.read_csv(output/'fold_0_cash_trades.csv').empty
    with pytest.raises(FileExistsError): save_report(output,report,artifacts,provenance,'AAPL')


def test_volume_ablation_does_not_remove_other_rules():
    data = bars()
    full = signals_for(data,'AAPL','enhanced_technical')
    ablated = signals_for(data,'AAPL','technical_no_volume')
    assert (ablated[full != 0] == full[full != 0]).all()


@pytest.mark.parametrize('warmup,test', [(59,100),(100,0),(100,1000)])
def test_invalid_windows_rejected(warmup,test):
    with pytest.raises(ValueError): evaluate(bars(),'AAPL',warmup_bars=warmup,test_bars=test)


@pytest.mark.parametrize('module', ['offline_backtest','backtest','backtest_walkforward','advanced_backtest'])
def test_all_cli_entrypoints_write_same_offline_protocol(tmp_path,monkeypatch,module):
    import importlib
    path = tmp_path/'input.csv'
    bars(200).to_csv(path,index_label='timestamp')
    output = tmp_path/'output'
    monkeypatch.setattr('sys.argv',[module,str(path),'--timeframe','5min','--legacy-all-sessions','--output',str(output)])
    importlib.import_module('scripts.backtesting.'+module).main()
    report = json.loads((output/'report.json').read_text())
    assert report['protocol'] == 'fixed-rule independent-window evaluation v1'
    assert set(report['folds'][0]['variants']) == set(VARIANTS)|{'buy_hold'}
