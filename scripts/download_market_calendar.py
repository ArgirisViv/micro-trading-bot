"""One read-only GET to Alpaca PAPER calendar. No order or account writes."""
import argparse
from datetime import date, datetime, timezone
import json
from pathlib import Path
import requests
from dotenv import dotenv_values
from core.stock_sessions import calendar_sessions

URL='https://paper-api.alpaca.markets/v2/calendar'


def fetch_calendar(start,end,key,secret,get=requests.get):
    first,last=date.fromisoformat(start),date.fromisoformat(end)
    if first>last or (last-first).days>=366:
        raise ValueError('CALENDAR_DATES: request at most 366 calendar days')
    if not key or not secret:
        raise ValueError('CALENDAR_KEYS: configure the existing Alpaca paper key and secret locally')
    try:
        response=get(URL,params={'start':start,'end':end},
            headers={'APCA-API-KEY-ID':key,'APCA-API-SECRET-KEY':secret},
            timeout=(5,20),allow_redirects=False)
        if response.status_code!=200:
            raise ValueError('CALENDAR_HTTP: access denied, rate limited or provider unavailable; no retry')
        rows=response.json()
        if not isinstance(rows,list):
            raise ValueError('CALENDAR_PAYLOAD: expected session list')
        sessions=[{name:row[name] for name in ('date','open','close')} for row in rows]
        payload=dict(provider='Alpaca paper calendar',requested_start=start,requested_end=end,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            sessions=sessions)
        calendar_sessions(payload)
        return payload
    except Exception:
        # Do not relay response bodies, exception strings or credential headers.
        raise ValueError('CALENDAR_FAILED: check dates, paper credentials and network; no secrets displayed') from None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start',required=True)
    parser.add_argument('--end',required=True)
    parser.add_argument('--env-file',default='.env.local')
    parser.add_argument('--output',default='market_calendar_001.json')
    args=parser.parse_args()
    try:
        path=Path(args.output)
        if path.exists(): raise ValueError('CALENDAR_OUTPUT_EXISTS: choose a new output filename')
        env=Path(args.env_file)
        with env.open('rb') as stream: signature=stream.read(4)
        encoding='utf-16' if signature.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig'
        values=dotenv_values(env,encoding=encoding,interpolate=False)
        payload=fetch_calendar(args.start,args.end,values.get('APCA_API_KEY_ID'),values.get('APCA_API_SECRET_KEY'))
        # Exclusive create: a concurrent run cannot overwrite an existing export.
        with path.open('x',encoding='utf-8') as stream:
            json.dump(payload,stream,indent=2,allow_nan=False)
    except Exception:
        print('CALENDAR_EXPORT_FAILED: check dates, .env.local, network and a NEW output filename. No secrets displayed.')
        return 1
    print(f'Calendar saved: {len(payload["sessions"])} sessions. Read-only PAPER request; no orders submitted.')
    return 0


if __name__=='__main__': raise SystemExit(main())
