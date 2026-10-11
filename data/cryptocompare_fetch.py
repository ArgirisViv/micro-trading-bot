"""CryptoCompare legacy REST, UTC base bars, local exact-timeframe aggregation."""
import math
import re
import pandas as pd
from config import TIMEFRAME,LOOKBACK,CRYPTOCOMPARE_API_KEY
from .bar_validation import bar_interval,validated_bars
from .provider_transport import DataError,RateLimiter,get_json,utc_now

_limiter=RateLimiter(1)


def get_cryptocompare_data(symbol,timeframe=TIMEFRAME,lookback=LOOKBACK):
    if not CRYPTOCOMPARE_API_KEY:raise DataError('CryptoCompare key is not configured')
    pair=re.fullmatch(r'([A-Z0-9]+?)/?(USDT|USDC|USD|BTC|EUR)',symbol)
    if not pair:raise DataError('Unsupported crypto pair')
    base,quote=pair.groups()  # Never silently convert USDT/USDC into USD.
    if not isinstance(lookback,int) or not 1<=lookback<=365:raise DataError('Invalid lookback days')
    interval=bar_interval(timeframe)
    seconds=int(interval.total_seconds())
    unit=86400 if seconds%86400==0 else 3600 if seconds%3600==0 else 60
    factor=seconds//unit
    if unit==60 and lookback>7:raise DataError('Minute-history retention exceeded; choose another dataset')
    endpoint={60:'histominute',3600:'histohour',86400:'histoday'}[unit]
    now=utc_now();start=now-pd.Timedelta(lookback, unit='D')
    cursor=int(now.timestamp());rows=[]
    headers={'authorization':'Apikey '+CRYPTOCOMPARE_API_KEY}
    for _ in range(20):
        needed=math.ceil((cursor-start.timestamp())/unit)+factor
        payload=get_json('https://min-api.cryptocompare.com/data/v2/'+endpoint,headers,
            dict(fsym=base,tsym=quote,limit=min(2000,max(1,needed)),aggregate=1,toTs=cursor),
            _limiter,'min-api.cryptocompare.com')
        if payload.get('Response')!='Success':raise DataError('CryptoCompare provider error')
        page=payload.get('Data',{}).get('Data',[])
        if not page:raise DataError('Insufficient crypto history')
        oldest=min(int(row['time']) for row in page)
        if oldest>cursor:raise DataError('Non-progressing crypto pagination')
        rows.extend(page)
        if oldest<=start.timestamp()-seconds:break
        cursor=oldest-1
    else:raise DataError('Crypto pagination budget exceeded')
    frame=pd.DataFrame(rows)
    frame.index=pd.to_datetime(frame.pop('time'),unit='s',utc=True)
    frame=frame.rename(columns={'volumefrom':'volume'})[['open','high','low','close','volume']].sort_index()
    if frame.index.has_duplicates:
        # Overlap must agree exactly; inconsistent duplicate data is rejected.
        for _,group in frame.groupby(level=0):
            if len(group.drop_duplicates())!=1:raise DataError('Conflicting crypto page overlap')
        frame=frame[~frame.index.duplicated()]
    frame=validated_bars(frame,f'{unit//60}min',now=now,require_fresh=False)
    aggregates=frame.resample(interval,origin='epoch').agg(
        dict(open='first',high='max',low='min',close='last',volume='sum'))
    counts=frame.close.resample(interval,origin='epoch').count()
    aggregates=aggregates[counts==factor]
    aggregates=aggregates[aggregates.index>=start.floor(interval)]
    result=validated_bars(aggregates,timeframe,now=now,require_fresh=False)
    if len(result)>1 and (result.index.to_series().diff().dropna()!=interval).any():
        raise DataError('Crypto candle gap detected')
    return result
