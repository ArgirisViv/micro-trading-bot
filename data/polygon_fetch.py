"""Polygon/Massive aggregate adapter; exact timeframe and bounded pagination."""
import os
import re
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode
import pandas as pd
from config import TIMEFRAME,LOOKBACK,POLYGON_API_KEY
from .bar_validation import bar_interval,validated_bars
from .provider_transport import DataError,RateLimiter,get_json,utc_now

_limiter=RateLimiter(12)


def get_polygon_data(symbol,timeframe=TIMEFRAME,lookback=LOOKBACK):
    if not POLYGON_API_KEY:raise DataError('Stock provider key is not configured')
    if not re.fullmatch(r'[A-Z][A-Z0-9.-]{0,15}',symbol):raise DataError('Invalid stock symbol')
    if not isinstance(lookback,int) or not 1<=lookback<=365:raise DataError('Invalid lookback days')
    seconds=int(bar_interval(timeframe).total_seconds())
    unit=86400 if seconds%86400==0 else 3600 if seconds%3600==0 else 60
    multiplier=seconds//unit;span={86400:'day',3600:'hour',60:'minute'}[unit]
    if unit==86400:raise DataError('Stock daily session-close policy not implemented; use intraday')
    host=os.getenv('STOCK_DATA_HOST','api.massive.com')
    if host not in {'api.massive.com','api.polygon.io'}:raise DataError('Unsupported stock data host')
    now=utc_now();start=now-pd.Timedelta(lookback, unit='D')
    url=f'https://{host}/v2/aggs/ticker/{symbol}/range/{multiplier}/{span}/{int(start.timestamp()*1000)}/{int(now.timestamp()*1000)}'
    headers={'Authorization':'Bearer '+POLYGON_API_KEY}
    params=dict(adjusted='true',sort='asc',limit=50000);seen=set();rows=[]
    for _ in range(20):
        if url in seen:raise DataError('Repeated stock pagination cursor')
        seen.add(url)
        payload=get_json(url,headers,params,_limiter,host)
        if payload.get('status') not in {'OK','DELAYED'}:raise DataError('Stock provider error')
        rows.extend(payload.get('results',[]))
        next_url=payload.get('next_url')
        if not next_url:break
        parsed=urlsplit(next_url)
        query=[(key,value) for key,value in parse_qsl(parsed.query) if key.lower() not in {'apikey','api_key'}]
        url=urlunsplit((parsed.scheme,parsed.netloc,parsed.path,urlencode(query),''));params=None
    else:raise DataError('Stock pagination budget exceeded')
    if not rows:return pd.DataFrame()
    frame=pd.DataFrame(rows).rename(columns=dict(o='open',h='high',l='low',c='close',v='volume'))
    frame.index=pd.to_datetime(frame.pop('t'),unit='ms',utc=True)
    frame=frame[['open','high','low','close','volume']]
    # Stock daily/multi-day bars follow ET calendar/session boundaries; fixed UTC
    # durations cannot prove their close. Do not pretend those live bars are safe.
    return validated_bars(frame,timeframe,now=now,require_fresh=False)
