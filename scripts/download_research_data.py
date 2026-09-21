"""Read-only Massive/Polygon export. No config, broker SDK, or trading imports."""
import argparse
from datetime import date, timedelta
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import time
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import pandas as pd
import requests
from dotenv import dotenv_values

INTERVALS = {'1min':(1,'minute'), '5min':(5,'minute'), '15min':(15,'minute'),
             '30min':(30,'minute'), '1h':(1,'hour')}
HOSTS = {'api.massive.com', 'api.polygon.io'}


class DownloadError(RuntimeError):
    """Only controlled, non-provider error messages may reach the terminal."""


def load_key(env_path):
    path = Path(env_path)
    if not path.is_file():
        raise DownloadError('ENV_MISSING: .env.local must be a file in the project folder.')
    with path.open('rb') as stream:
        signature = stream.read(4)
    encoding = 'utf-16' if signature.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig'
    values = dotenv_values(path, encoding=encoding, interpolate=False)
    key = (values.get('POLYGON_API_KEY') or '').strip()
    host = values.get('STOCK_DATA_HOST') or 'api.massive.com'
    if not key or any(char.isspace() for char in key):
        raise DownloadError('KEY_MISSING: configure POLYGON_API_KEY locally; never share it.')
    if host not in HOSTS:
        raise DownloadError('HOST_INVALID: only official Massive/Polygon hosts are allowed.')
    return key, host


def date_range(start, end, now):
    try:
        first, last = date.fromisoformat(start), date.fromisoformat(end)
    except (TypeError, ValueError):
        raise DownloadError('DATES_INVALID: use YYYY-MM-DD.') from None
    if last < first or (last-first).days >= 365:
        raise DownloadError('DATES_INVALID: request 1 to 365 calendar days.')
    lower = pd.Timestamp(first, tz='America/New_York').tz_convert('UTC')
    upper = pd.Timestamp(last+timedelta(days=1), tz='America/New_York').tz_convert('UTC')
    if upper > now:
        raise DownloadError('DATES_UNFINISHED: end date must be a completed Eastern-Time day.')
    return lower, upper


def safe_url(url, host):
    try:
        parsed = urlsplit(url)
        valid = (parsed.scheme,parsed.hostname,parsed.port,parsed.username,parsed.password) == ('https',host,None,None,None)
    except (TypeError,ValueError):
        valid = False
    if not valid:
        raise DownloadError('PAGINATION_INVALID: official same-host HTTPS required.')
    query = [(key,value) for key,value in parse_qsl(parsed.query)
             if key.lower() not in {'apikey','api_key'}]
    return urlunsplit((parsed.scheme,parsed.netloc,parsed.path,urlencode(query),''))


def fetch(symbol, start, end, timeframe, key, host='api.massive.com', now=None,
          get=requests.get, wait=time.sleep):
    now = pd.Timestamp.now(tz='UTC') if now is None else pd.Timestamp(now)
    if not re.fullmatch(r'[A-Z][A-Z0-9.-]{0,15}',symbol) or timeframe not in INTERVALS or host not in HOSTS:
        raise DownloadError('REQUEST_INVALID: supported stock symbol, intraday timeframe and host required.')
    lower, upper = date_range(start,end,now)
    multiplier, span = INTERVALS[timeframe]
    url = f'https://{host}/v2/aggs/ticker/{symbol}/range/{multiplier}/{span}/{int(lower.timestamp()*1000)}/{int(upper.timestamp()*1000)-1}'
    params = dict(adjusted='true',sort='asc',limit=50000)
    rows, seen, statuses = [], set(), set()
    pages = 0
    for page in range(20):
        url = safe_url(url,host)
        if url in seen:
            raise DownloadError('PAGINATION_REPEATED: incomplete download rejected.')
        seen.add(url)
        if page:
            wait(12)
        try:
            response = get(url,headers={'Authorization':'Bearer '+key},params=params,
                           timeout=(5,20),allow_redirects=False)
        except Exception:
            raise DownloadError('NETWORK_FAILED: download stopped; no dataset saved.') from None
        code = response.status_code
        if code in (401,403):
            raise DownloadError('ACCESS_DENIED: check key and historical-data plan access; do not buy an upgrade yet.')
        if code == 429:
            raise DownloadError('RATE_LIMITED: no retry; wait before starting a new run.')
        if code != 200:
            raise DownloadError('HTTP_FAILED: provider rejected request; no dataset saved.')
        try:
            payload = response.json()
            if not isinstance(payload,dict) or payload.get('status') not in {'OK','DELAYED'}:
                raise ValueError()
            if payload.get('ticker',symbol) != symbol or payload.get('adjusted',True) is not True:
                raise ValueError()
            result = payload.get('results',[])
            if not isinstance(result,list) or any(not isinstance(row,dict) for row in result):
                raise ValueError()
            rows.extend(result)
            statuses.add(payload['status'])
            pages += 1
            next_url = payload.get('next_url')
        except Exception:
            raise DownloadError('PAYLOAD_INVALID: unusable provider response.') from None
        if not next_url:
            break
        url, params = next_url, None
    else:
        raise DownloadError('PAGE_BUDGET: incomplete download rejected.')
    if not rows:
        raise DownloadError('NO_DATA: no bars returned; check dates and access.')
    try:
        frame = pd.DataFrame(rows)[['t','o','h','l','c','v']]
        frame.index = pd.to_datetime(frame.pop('t'),unit='ms',utc=True)
        frame.columns = ['open','high','low','close','volume']
        frame = frame.apply(pd.to_numeric,errors='raise')
        if frame.index.hasnans or frame.index.has_duplicates:
            raise ValueError()
        if not frame.map(math.isfinite).all().all() or (frame.iloc[:,:4] <= 0).any().any() or (frame.volume < 0).any():
            raise ValueError()
        if ((frame.high < frame[['open','low','close']].max(axis=1)) |
            (frame.low > frame[['open','high','close']].min(axis=1))).any():
            raise ValueError()
        frame = frame.sort_index()
        if ((frame.index < lower) | (frame.index >= upper)).any():
            raise ValueError()
        interval = pd.Timedelta(minutes=multiplier) if span == 'minute' else pd.Timedelta(hours=multiplier)
        if (frame.index+interval > now).any():
            raise ValueError()
    except Exception:
        raise DownloadError('BARS_INVALID: malformed, duplicated or out-of-range candles.') from None
    # Deliberately retain pre/post-market bars. Do not pretend a clock filter is
    # an exchange calendar or silently change the traded session policy.
    return frame, dict(provider='Massive/Polygon', symbol=symbol, timeframe=timeframe,
        requested_start=start, requested_end=end, request_timezone='America/New_York',
        adjusted_for_splits=True, session_policy='all qualifying provider sessions',
        fetched_at=now.isoformat(), pages=pages, provider_statuses=sorted(statuses),
        rows=len(frame), actual_start=frame.index[0].isoformat(),actual_end=frame.index[-1].isoformat(),
        warning='No calendar completeness, dividends or survivorship certification; no synthetic gap fill.')


def save_dataset(output, frame, metadata):
    output = Path(output)
    output.mkdir(parents=True,exist_ok=False)
    path = output/'bars.csv'
    frame.to_csv(path,index_label='timestamp')
    metadata = dict(metadata,sha256=sha256(path.read_bytes()).hexdigest())
    (output/'dataset.json').write_text(json.dumps(metadata,indent=2,allow_nan=False),encoding='utf-8')
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--symbol',default='AAPL')
    parser.add_argument('--start',required=True)
    parser.add_argument('--end',required=True,help='Inclusive ET date; completed days only')
    parser.add_argument('--timeframe',choices=INTERVALS,default='5min')
    parser.add_argument('--env-file',default='.env.local')
    parser.add_argument('--output',default='research_data_AAPL_001')
    args = parser.parse_args()
    try:
        if Path(args.output).exists():
            raise DownloadError('OUTPUT_EXISTS: choose a new output folder; no overwrite.')
        # Validate dates before reading credentials or performing a request.
        date_range(args.start,args.end,pd.Timestamp.now(tz='UTC'))
        key,host = load_key(args.env_file)
        frame,metadata = fetch(args.symbol,args.start,args.end,args.timeframe,key,host)
        save_dataset(args.output,frame,metadata)
    except DownloadError as error:
        print(str(error))
        return 1
    except Exception:
        print('EXPORT_FAILED: check local file permissions and dependencies. No secrets displayed.')
        return 1
    print(f'Download complete: {len(frame)} bars. Saved bars.csv and dataset.json in the output folder.')
    print('Read-only market data export. No broker orders submitted. Coverage is not certified.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
