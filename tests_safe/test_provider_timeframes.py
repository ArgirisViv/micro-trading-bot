import pandas as pd
import pytest
from data import cryptocompare_fetch as cc,polygon_fetch as stock,provider_transport as transport
from data.provider_transport import DataError

NOW=pd.Timestamp('2026-09-16T15:00Z')


def cc_rows(start,periods,freq='min'):
    return [dict(time=int(ts.timestamp()),open=100,high=102,low=99,close=101,
        volumefrom=1) for ts in pd.date_range(start,periods=periods,freq=freq)]


def setup_cc(monkeypatch,rows):
    monkeypatch.setattr(cc,'CRYPTOCOMPARE_API_KEY','offline-placeholder')
    monkeypatch.setattr(cc,'utc_now',lambda:NOW)
    calls=[]
    def request(url,headers,params,limiter,host):
        calls.append((url,headers,params))
        eligible=[row for row in rows if row['time']<=params['toTs']]
        return dict(Response='Success',Data=dict(Data=eligible[-(params['limit']+1):]))
    monkeypatch.setattr(cc,'get_json',request)
    return calls


def test_five_minute_crypto_bars_are_not_hourly(monkeypatch):
    calls=setup_cc(monkeypatch,cc_rows(
        NOW-pd.Timedelta(1, unit='D')-pd.Timedelta(10, unit='min'),1451))
    bars=cc.get_cryptocompare_data('BTCUSD','5min',1)
    assert bars.index.tz is not None
    assert (bars.index.to_series().diff().dropna()==pd.Timedelta(5, unit='min')).all()
    assert bars.volume.iloc[-1]==5
    assert bars.index[-1]==NOW-pd.Timedelta(5, unit='min')
    assert 'histominute' in calls[0][0]
    assert 'offline-placeholder' not in calls[0][0]
    assert 'apiKey' not in calls[0][2]


def test_exact_quote_currency_not_silently_converted(monkeypatch):
    calls=setup_cc(monkeypatch,cc_rows(
        NOW-pd.Timedelta(1, unit='D')-pd.Timedelta(2, unit='h'),27,'h'))
    cc.get_cryptocompare_data('BTCUSDT','1h',1)
    assert calls[0][2]['tsym']=='USDT'
    assert calls[0][2]['fsym']=='BTC'
    assert 'histohour' in calls[0][0]


def test_crypto_history_paginates_until_requested_range(monkeypatch):
    calls=setup_cc(monkeypatch,cc_rows(
        NOW-pd.Timedelta(3, unit='D')-pd.Timedelta(10, unit='min'),4331))
    bars=cc.get_cryptocompare_data('BTCUSD','5min',3)
    assert len(calls)>=3
    assert calls[1][2]['toTs']<calls[0][2]['toTs']
    assert len(bars)==864


def test_crypto_missing_base_bar_does_not_fabricate_complete_candle(monkeypatch):
    rows=cc_rows(NOW-pd.Timedelta(1, unit='D')-pd.Timedelta(10, unit='min'),1451)
    del rows[-100]
    setup_cc(monkeypatch,rows)
    with pytest.raises(DataError,match='gap'):cc.get_cryptocompare_data('BTCUSD','5min',1)


def test_crypto_retention_rejected_before_request(monkeypatch):
    monkeypatch.setattr(cc,'CRYPTOCOMPARE_API_KEY','offline-placeholder')
    monkeypatch.setattr(cc,'get_json',lambda *args:pytest.fail('must reject before HTTP'))
    with pytest.raises(DataError):cc.get_cryptocompare_data('BTCUSD','5min',8)


def stock_row(ts):return dict(t=int(ts.timestamp()*1000),o=100,h=102,l=99,c=101,v=10)


def test_stock_exact_timeframe_and_pagination(monkeypatch):
    monkeypatch.setattr(stock,'POLYGON_API_KEY','offline-placeholder')
    monkeypatch.setattr(stock,'utc_now',lambda:NOW)
    monkeypatch.delenv('STOCK_DATA_HOST',raising=False)
    calls=[]
    def request(url,headers,params,limiter,host):
        calls.append((url,headers,params))
        if len(calls)==1:return dict(status='OK',results=[stock_row(NOW-pd.Timedelta(10, unit='min'))],
            next_url='https://api.massive.com/v2/aggs?cursor=next&apiKey=discard-this')
        return dict(status='OK',results=[stock_row(NOW-pd.Timedelta(5, unit='min'))])
    monkeypatch.setattr(stock,'get_json',request)
    result=stock.get_polygon_data('AAPL','5min',1)
    assert '/range/5/minute/' in calls[0][0]
    assert len(result)==2
    assert 'apiKey' not in calls[1][0]
    assert calls[0][1]['Authorization']=='Bearer offline-placeholder'


def test_stock_daily_not_silently_fallback_to_five_minutes(monkeypatch):
    monkeypatch.setattr(stock,'POLYGON_API_KEY','offline-placeholder')
    monkeypatch.setattr(stock,'get_json',lambda *args:pytest.fail('daily policy unsupported'))
    with pytest.raises(DataError):stock.get_polygon_data('AAPL','1Day',1)


@pytest.mark.parametrize('url',['http://api.massive.com/a','https://evil.example/a',
    'https://api.massive.com.evil.example/a','https://user@api.massive.com/a'])
def test_pagination_never_forwards_headers_to_untrusted_host(monkeypatch,url):
    monkeypatch.setattr(transport.requests,'get',lambda *args,**kwargs:pytest.fail('untrusted HTTP attempted'))
    with pytest.raises(DataError):transport.get_json(url,{'Authorization':'dummy'},None,
        transport.RateLimiter(0),'api.massive.com')


def test_transport_timeout_no_redirect_and_sanitized_errors(monkeypatch):
    calls=[]
    def get(url,**kwargs):
        calls.append(kwargs);raise RuntimeError('URL-with-secret')
    monkeypatch.setattr(transport.requests,'get',get)
    with pytest.raises(DataError) as exc:
        transport.get_json('https://api.massive.com/a',{},None,transport.RateLimiter(0),'api.massive.com')
    assert 'secret' not in str(exc.value)
    assert calls[0]['allow_redirects'] is False
    assert calls[0]['timeout']==(5,20)
