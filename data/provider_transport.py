"""Bounded, header-authenticated GET transport; no secret-bearing URLs/logs."""
import time
from threading import Lock
from urllib.parse import urlsplit
import requests
import pandas as pd


def utc_now():return pd.Timestamp.now(tz='UTC')


class DataError(RuntimeError):pass


class RateLimiter:
    def __init__(self,seconds):self.seconds=seconds;self.last=None;self.lock=Lock()
    def wait(self):
        with self.lock:
            now=time.monotonic()
            if self.last is not None:
                delay=self.seconds-(now-self.last)
                if delay>0:time.sleep(delay)
            self.last=time.monotonic()


def get_json(url,headers,params,limiter,host):
    parsed=urlsplit(url)
    if (parsed.scheme,parsed.hostname,parsed.port,parsed.username,parsed.password) != ('https',host,None,None,None):
        raise DataError('Provider pagination host rejected')
    limiter.wait()
    try:
        response=requests.get(url,headers=headers,params=params,timeout=(5,20),allow_redirects=False)
        if response.status_code != 200:raise DataError('Market-data request rejected or rate limited')
        payload=response.json()
        if not isinstance(payload,dict):raise DataError('Invalid market-data response')
        return payload
    except DataError:raise
    except Exception:raise DataError('Market-data transport failed') from None
