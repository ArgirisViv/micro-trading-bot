import pandas as pd
import pytest
from core.backtest_engine import simulate,BacktestPolicy
from core.stock_sessions import calendar_sessions,session_windows
from scripts.download_market_calendar import fetch_calendar


def calendar(rows=None,start='2026-01-02',end='2026-01-05'):
    rows = [{'date':'2026-01-02','open':'09:30','close':'16:00'},
        {'date':'2026-01-05','open':'09:30','close':'16:00'}] if rows is None else rows
    return calendar_sessions(dict(provider='Alpaca paper calendar',requested_start=start,
        requested_end=end,sessions=rows))


def bars(stamps,prices=None):
    prices=[100]*len(stamps) if prices is None else prices
    return pd.DataFrame(dict(open=prices,high=prices,low=prices,close=prices,volume=10),
        index=pd.DatetimeIndex(stamps).tz_localize('America/New_York').tz_convert('UTC'))


POLICY=BacktestPolicy(fee_bps=0,slippage_bps=0)


def run(data,signals,cal=None,**kwargs):
    return simulate(data,pd.Series(signals,index=data.index),POLICY,
        calendar=calendar() if cal is None else cal,timeframe='5min',**kwargs)


def test_no_premarket_fill_or_exit_after_close():
    data=bars(['2026-01-02 09:20','2026-01-02 09:25','2026-01-02 09:30','2026-01-02 16:00'],[100,100,100,110])
    curve,trades,m=run(data,[1,1,0,0])
    assert curve.Position.iloc[1]==0
    assert curve.Position.iloc[2]>0
    assert trades.empty
    assert m['expired_protection_events']==1
    assert not m['open_inventory_protected']


def test_day_expiry_never_sells_or_rearms_inventory_next_day():
    data=bars(['2026-01-02 15:45','2026-01-02 15:50','2026-01-02 15:55','2026-01-05 09:30'],[100,100,100,90])
    curve,trades,m=run(data,[1,0,0,1])
    assert trades.empty
    assert m['open_quantity']==500
    assert m['total_return']==pytest.approx(-.05)
    assert m['expired_protection_events']==1
    assert m['unprotected_inventory_bars']==2
    assert not curve.protection_active.iloc[-1]


def test_last_regular_bar_exit_is_allowed_before_expiry():
    data=bars(['2026-01-02 15:45','2026-01-02 15:50','2026-01-02 15:55'],[100,100,105])
    _,trades,m=run(data,[1,0,0])
    assert len(trades)==1
    assert m['expired_protection_events']==0


def test_early_close_and_holiday_have_no_regular_fills():
    cal=calendar([{'date':'2026-01-02','open':'09:30','close':'13:00'}])
    data=bars(['2026-01-02 12:50','2026-01-02 12:55','2026-01-02 13:00','2026-01-05 09:30'],[100,100,105,110])
    curve,trades,m=run(data,[1,0,0,0],cal)
    assert trades.empty
    assert curve.regular_session.tolist()==[True,True,False,False]
    assert m['expired_protection_events']==1


def test_missing_previous_bar_signal_never_fills():
    data=bars(['2026-01-02 09:30','2026-01-02 10:00'])
    _,_,m=run(data,[1,0])
    assert m['open_quantity']==0


def test_initial_warmup_signal_requires_timestamp_provenance():
    data=bars(['2026-01-02 09:30'])
    _,_,m=run(data,[0],initial_signal=1)
    assert m['open_quantity']==0
    _,_,m=run(data,[0],initial_signal=1,initial_signal_time=data.index[0]-pd.Timedelta(minutes=5))
    assert m['open_quantity']>0


def test_dst_calendar_uses_real_et_offsets():
    cal=calendar([{'date':'2026-03-06','open':'09:30','close':'16:00'},
        {'date':'2026-03-09','open':'09:30','close':'16:00'}],start='2026-03-06',end='2026-03-09')
    assert cal['sessions'][0][0].hour==14
    assert cal['sessions'][1][0].hour==13


@pytest.mark.parametrize('damage',['coverage','duplicate','reverse','clock'])
def test_calendar_rejects_bad_structure(damage):
    rows=[{'date':'2026-01-02','open':'09:30','close':'16:00'}]
    if damage=='coverage': rows[0]['date']='2026-01-06'
    if damage=='duplicate': rows *=2
    if damage=='reverse': rows[0]['close']='09:00'
    if damage=='clock': rows[0]['open']='SECRET'
    with pytest.raises(ValueError): calendar(rows)


def test_coarse_or_straddling_bars_are_rejected():
    data=bars(['2026-01-02 09:25'])
    with pytest.raises(ValueError): session_windows(data.index,calendar(),'1h')
    with pytest.raises(ValueError): session_windows(data.index,calendar(),'15min')
    outside=bars(['2026-01-06 09:30'])
    with pytest.raises(ValueError): session_windows(outside.index,calendar(),'5min')


def test_calendar_get_is_paper_only_readonly_and_redacted():
    calls=[]
    class Response:
        status_code=200
        def json(self): return [{'date':'2026-01-02','open':'09:30','close':'16:00','unused':'SECRET'}]
    def get(url,**kwargs): calls.append((url,kwargs));return Response()
    result=fetch_calendar('2026-01-02','2026-01-05','FAKEKEY','FAKESECRET',get=get)
    assert calls[0][0]=='https://paper-api.alpaca.markets/v2/calendar'
    assert calls[0][1]['allow_redirects'] is False
    assert calls[0][1]['timeout']==(5,20)
    assert 'unused' not in result['sessions'][0]
    assert 'FAKEKEY' not in str(result)


def test_calendar_network_failure_does_not_print_secret():
    def fail(*a,**k): raise RuntimeError('SECRET')
    with pytest.raises(ValueError) as exc:
        fetch_calendar('2026-01-02','2026-01-05','FAKE','SECRET',get=fail)
    assert 'SECRET' not in str(exc.value)


def test_session_simulation_prefix_invariance():
    data=bars(['2026-01-02 15:45','2026-01-02 15:50','2026-01-02 15:55','2026-01-05 09:30'],[100,100,100,90])
    prefix,_,_=run(data.iloc[:3],[1,0,0])
    full,_,_=run(data,[1,0,0,0])
    pd.testing.assert_frame_equal(prefix,full.iloc[:3])


def test_direct_technical_branch_matches_original_neutral_strategy(monkeypatch):
    from core.enhanced_strategy import EnhancedStrategy
    from scripts.backtesting.offline_backtest import research_signals
    data=bars(pd.date_range('2026-01-02 09:00',periods=100,freq='5min').astype(str))
    data.close=100+pd.Series(range(100),index=data.index).map(lambda x: (x%15)/10)
    data.high=data[['open','close']].max(axis=1)+1
    data.low=data[['open','close']].min(axis=1)-1
    strategy=EnhancedStrategy(enable_regime_adaptation=False,enable_macro_adaptation=False)
    strategy._add_ml_predictions=lambda frame:frame.assign(ml_prediction=0,ml_confidence=0.,ml_available=False)
    strategy._add_fundamental_analysis=lambda frame,symbol:frame.assign(fundamental_score=.5,fundamental_adjustment=1.)
    pd.testing.assert_series_equal(research_signals(data,'AAPL'),strategy.apply_strategy(data,'AAPL').signal)


def test_continuous_audit_cli_reserves_later_data(tmp_path,monkeypatch):
    import json
    from scripts.backtesting import session_audit
    data=bars(pd.date_range('2026-01-02 07:00',periods=105,freq='5min').astype(str))
    later=bars(['2026-07-01 09:30'],[1000])
    data=pd.concat([data,later])
    csv=tmp_path/'bars.csv';data.to_csv(csv,index_label='timestamp')
    path=tmp_path/'calendar.json'
    path.write_text(json.dumps(dict(provider='Alpaca paper calendar',requested_start='2026-01-02',
        requested_end='2026-01-02',sessions=[{'date':'2026-01-02','open':'09:30','close':'16:00'}])))
    output=tmp_path/'out'
    monkeypatch.setattr('sys.argv',['audit',str(csv),'--calendar',str(path),'--development-end','2026-06-30','--output',str(output)])
    session_audit.main()
    report=json.loads((output/'report.json').read_text())
    assert report['reserved_later_rows']==1
    assert report['later_performance_evaluated'] is False
    assert report['evaluated_rows']==5


def test_calendar_aware_walkforward_requires_regular_sample():
    from core.research_pipeline import evaluate
    data=bars(pd.date_range('2026-01-02 07:00',periods=105,freq='5min').astype(str))
    report,_=evaluate(data,'AAPL',warmup_bars=100,test_bars=5,calendar=calendar(),timeframe='5min')
    assert report['calendar_required'] is True
    assert 'DAY' in report['protocol']
    assert report['folds'][0]['variants']['enhanced_technical']['bracket_tif']=='day'


def test_calendar_export_cli_uses_mock_get_and_never_overwrites(tmp_path,monkeypatch,capsys):
    from scripts import download_market_calendar as script
    env=tmp_path/'test.env';env.write_text('APCA_API_KEY_ID=FAKE\nAPCA_API_SECRET_KEY=FAKESECRET\n')
    output=tmp_path/'calendar.json'
    monkeypatch.setattr('sys.argv',['calendar','--start','2026-01-02','--end','2026-01-02','--env-file',str(env),'--output',str(output)])
    monkeypatch.setattr(script,'fetch_calendar',lambda *a:dict(provider='Alpaca paper calendar',requested_start='2026-01-02',requested_end='2026-01-02',sessions=[]))
    assert script.main()==0
    assert script.main()==1
    assert 'FAKESECRET' not in capsys.readouterr().out
