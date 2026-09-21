"""Explicit broker calendar coverage, never inferred from weekday clocks."""
from datetime import date
import json
import re
from pathlib import Path
import pandas as pd


def calendar_sessions(payload):
    if not isinstance(payload,dict) or payload.get('provider') != 'Alpaca paper calendar':
        raise ValueError('Explicit Alpaca paper calendar envelope required')
    first,last = date.fromisoformat(payload['requested_start']),date.fromisoformat(payload['requested_end'])
    if first > last: raise ValueError('Invalid calendar coverage')
    if not isinstance(payload.get('sessions'),list):
        raise ValueError('Calendar session list required')
    if (last-first).days >= 7 and not payload['sessions']:
        raise ValueError('Empty calendar across multiple weeks is not usable')
    sessions=[]
    previous=None
    for row in payload['sessions']:
        day = date.fromisoformat(row['date'])
        if not first <= day <= last or (previous is not None and day <= previous):
            raise ValueError('Calendar dates outside coverage, duplicated or unsorted')
        clocks=[row['open'],row['close']]
        if any(not isinstance(clock,str) or not re.fullmatch(r'\d{2}:\d{2}',clock) for clock in clocks):
            raise ValueError('Calendar must contain regular-session HH:MM clocks')
        opening,closing=[pd.Timestamp(f'{day.isoformat()} {clock}',tz='America/New_York').tz_convert('UTC') for clock in clocks]
        if opening >= closing: raise ValueError('Invalid session boundary')
        sessions.append((opening,closing))
        previous=day
    return dict(start=first,end=last,sessions=sessions)


def load_calendar(path):
    return calendar_sessions(json.loads(Path(path).read_text(encoding='utf-8-sig')))


def session_windows(index,calendar,timeframe):
    """Whole bars inside regular sessions; reject unsupported coarse candles."""
    from data.bar_validation import bar_interval
    duration=bar_interval(timeframe)
    if duration > pd.Timedelta(minutes=30):
        raise ValueError('Use at most 30-minute bars; coarse bars can straddle session boundaries')
    local=index.tz_convert('America/New_York')
    if any(not calendar['start'] <= day <= calendar['end'] for day in local.date):
        raise ValueError('Calendar coverage must contain the entire evaluated bar dataset')
    result=pd.Series(pd.NaT,index=index,dtype='datetime64[ns, UTC]')
    for opening,closing in calendar['sessions']:
        overlap=(index < closing)&(index+duration > opening)
        contained=(index >= opening)&(index+duration <= closing)
        if (overlap & ~contained).any():
            raise ValueError('Bar straddles session boundary; cannot invent regular-session OHLC')
        result.loc[contained]=closing
    return result,duration
