# data/live_data_fetch.py

import pandas as pd
from config import TIMEFRAME, LOOKBACK
from .hybrid_fetch import get_hybrid_data  # Real data fetching restored

# Rate limiting χειρίζεται από τα επιμέρους fetchers
# Mock data removed - using live data only

def get_live_data(
    symbol: str,
    timeframe: str = TIMEFRAME,
    lookback: int = LOOKBACK
) -> pd.DataFrame:
    # Using hybrid system: CryptoCompare for crypto, Polygon.io for stocks
    df = get_hybrid_data(symbol, timeframe, lookback)

    if df is None or df.empty:
        return pd.DataFrame()

    # Ensure we have the required columns
    required_columns = ['open', 'high', 'low', 'close', 'volume']
    if not all(col in df.columns for col in required_columns):
        print(f"⚠️ Missing required columns for {symbol}")
        return pd.DataFrame()

    # Normalize column names to lowercase
    df.columns = df.columns.str.lower()
    
    # Ensure datetime index
    if not isinstance(df.index, pd.DatetimeIndex):
        try:
            df.index = pd.to_datetime(df.index)
        except Exception as e:
            print(f"⚠️ Error converting index to datetime for {symbol}: {e}")
            return pd.DataFrame()

    return df
