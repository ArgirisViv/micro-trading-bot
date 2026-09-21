# core/enhanced_indicators.py
"""
Enhanced Technical Indicators for Advanced Trading Strategy
Includes MACD, Bollinger Bands, Stochastic RSI, Volume Analysis
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional

def compute_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Compute MACD (Moving Average Convergence Divergence)
    Returns: (macd_line, signal_line, histogram)
    """
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def compute_bollinger_bands(series: pd.Series, length: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Compute Bollinger Bands
    Returns: (upper_band, middle_band, lower_band)
    """
    middle = series.rolling(window=length).mean()
    std = series.rolling(window=length).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    return upper, middle, lower

def compute_stochastic_rsi(series: pd.Series, rsi_length: int = 14, stoch_length: int = 14) -> pd.Series:
    """
    Compute Stochastic RSI for better momentum detection
    """
    # First compute RSI
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/rsi_length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/rsi_length, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    # Then compute Stochastic of RSI
    rsi_min = rsi.rolling(window=stoch_length).min()
    rsi_max = rsi.rolling(window=stoch_length).max()
    stoch_rsi = (rsi - rsi_min) / (rsi_max - rsi_min)
    return stoch_rsi

def compute_volume_weighted_indicators(df: pd.DataFrame, length: int = 20) -> pd.DataFrame:
    """
    Compute Volume-Weighted indicators for better signal quality
    """
    df = df.copy()
    
    # Volume Weighted Average Price (VWAP)
    df['vwap'] = (df['close'] * df['volume']).rolling(window=length).sum() / df['volume'].rolling(window=length).sum()
    
    # Volume Weighted RSI
    volume_rsi = df['volume'] * df['close']
    df['volume_rsi'] = compute_rsi(volume_rsi, length)
    
    # Volume Momentum
    df['volume_momentum'] = df['volume'].pct_change(periods=length)
    
    # Price-Volume Trend
    df['pvt'] = ((df['close'] - df['close'].shift(1)) / df['close'].shift(1) * df['volume']).cumsum()
    
    return df

def compute_rsi(series: pd.Series, length: int = 14) -> pd.Series:
    """Helper function for RSI calculation"""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/length, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def compute_advanced_momentum(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute advanced momentum indicators
    """
    df = df.copy()
    
    # Rate of Change
    df['roc'] = df['close'].pct_change(periods=10)
    
    # Williams %R
    high_14 = df['high'].rolling(window=14).max()
    low_14 = df['low'].rolling(window=14).min()
    df['williams_r'] = -100 * (high_14 - df['close']) / (high_14 - low_14)
    
    # Commodity Channel Index (CCI)
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    sma_tp = typical_price.rolling(window=20).mean()
    mad = typical_price.rolling(window=20).apply(lambda x: np.mean(np.abs(x - x.mean())))
    df['cci'] = (typical_price - sma_tp) / (0.015 * mad)
    
    return df

def add_enhanced_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all enhanced indicators to DataFrame
    """
    df = df.copy()
    
    # Basic indicators (keep existing)
    df['sma_fast'] = df['close'].rolling(10).mean()
    df['sma_slow'] = df['close'].rolling(30).mean()
    df['rsi'] = compute_rsi(df['close'], 14)
    df['atr'] = compute_atr(df, 14)
    
    # Enhanced indicators
    df['macd'], df['macd_signal'], df['macd_histogram'] = compute_macd(df['close'])
    df['bb_upper'], df['bb_middle'], df['bb_lower'] = compute_bollinger_bands(df['close'])
    df['stoch_rsi'] = compute_stochastic_rsi(df['close'])
    
    # Volume analysis
    df = compute_volume_weighted_indicators(df)
    
    # Advanced momentum
    df = compute_advanced_momentum(df)
    
    # Bollinger Band width and %B
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
    df['bb_percent_b'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
    
    return df

def compute_atr(df: pd.DataFrame, length: int = 14) -> pd.Series:
    """Helper function for ATR calculation"""
    hl = df['high'] - df['low']
    hc = (df['high'] - df['close'].shift()).abs()
    lc = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return tr.ewm(alpha=1/length, adjust=False).mean()

def generate_enhanced_signals(df: pd.DataFrame, *, require_volume=True) -> pd.Series:
    """
    Generate enhanced trading signals using multiple indicators
    Returns: 1 (buy), -1 (sell), 0 (hold)
    """
    signals = pd.Series(0, index=df.index)
    
    # MACD signals
    macd_bullish = (df['macd'] > df['macd_signal']) & (df['macd_histogram'] > 0)
    macd_bearish = (df['macd'] < df['macd_signal']) & (df['macd_histogram'] < 0)
    
    # Bollinger Bands signals
    bb_bullish = (df['close'] < df['bb_lower']) & (df['bb_percent_b'] < 0.2)
    bb_bearish = (df['close'] > df['bb_upper']) & (df['bb_percent_b'] > 0.8)
    
    # RSI signals
    rsi_oversold = df['rsi'] < 30
    rsi_overbought = df['rsi'] > 70
    
    # Stochastic RSI signals
    stoch_oversold = df['stoch_rsi'] < 0.2
    stoch_overbought = df['stoch_rsi'] > 0.8
    
    # Volume confirmation
    volume_high = df['volume'] > df['volume'].rolling(20).mean() * 1.5
    if not require_volume:
        volume_high = pd.Series(True, index=df.index)
    
    # Combined signals
    buy_signals = (
        (macd_bullish | bb_bullish) & 
        (rsi_oversold | stoch_oversold) & 
        volume_high
    )
    
    sell_signals = (
        (macd_bearish | bb_bearish) & 
        (rsi_overbought | stoch_overbought) & 
        volume_high
    )
    
    signals[buy_signals] = 1
    signals[sell_signals] = -1
    
    return signals
