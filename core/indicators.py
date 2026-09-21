# indicators.py

import pandas as pd
from config import SMA_FAST, SMA_SLOW, RSI_PERIOD, ATR_PERIOD

def compute_rsi(series: pd.Series, length: int = RSI_PERIOD) -> pd.Series:
    delta = series.diff()
    gain  = delta.where(delta > 0, 0.0)
    loss  = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/length, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def compute_atr(df: pd.DataFrame, length: int = ATR_PERIOD) -> pd.Series:
    hl = df["high"] - df["low"]
    hc = (df["high"] - df["close"].shift()).abs()
    lc = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.ewm(alpha=1/length, adjust=False).mean()

def add_indicators(df: pd.DataFrame,
                   sma_fast: int = SMA_FAST,
                   sma_slow: int = SMA_SLOW,
                   rsi_period: int = RSI_PERIOD,
                   atr_period: int = ATR_PERIOD) -> pd.DataFrame:
    # Όλες οι στήλες είναι ήδη lowercase
    df["sma_fast"] = df["close"].rolling(sma_fast).mean()
    df["sma_slow"] = df["close"].rolling(sma_slow).mean()
    df["rsi"]      = compute_rsi(df["close"], rsi_period)
    df["atr"]      = compute_atr(df, atr_period)
    return df

