# hybrid_fetch.py
import pandas as pd
from .polygon_fetch import get_polygon_data
from .cryptocompare_fetch import get_cryptocompare_data
from config import STOCK_WATCHLIST, CRYPTO_WATCHLIST

def is_crypto_symbol(symbol: str) -> bool:
    """
    Ελέγχει αν το symbol είναι crypto ή stock.
    """
    if symbol in CRYPTO_WATCHLIST and symbol in STOCK_WATCHLIST:
        raise ValueError('Symbol appears in both watchlists')
    if symbol in CRYPTO_WATCHLIST:
        return True
    if symbol in STOCK_WATCHLIST:
        return False
    raise ValueError('Symbol is not in a configured watchlist')

def get_hybrid_data(
    symbol: str,
    timeframe: str = "5min",
    lookback: int = 3
) -> pd.DataFrame:
    """
    Επιλέγει αυτόματα το κατάλληλο data provider:
    - CryptoCompare για crypto symbols
    - Polygon.io για stock symbols
    """
    try:
        if is_crypto_symbol(symbol):
            print(f"Using CryptoCompare for {symbol}")
            return get_cryptocompare_data(symbol, timeframe, lookback)
        else:
            print(f"Using Polygon.io for {symbol}")
            return get_polygon_data(symbol, timeframe, lookback)
            
    except Exception:
        # Provider exception strings may contain URLs carrying credentials.
        print('Market data unavailable; provider request failed')
        return pd.DataFrame()
