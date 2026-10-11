"""
Enhanced Technical Indicators for Trading Bot Dashboard
Provides comprehensive technical analysis indicators including RSI, MACD, Bollinger Bands, and more
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional, Dict
import logging
import warnings
warnings.filterwarnings('ignore')

class EnhancedIndicators:
    """Enhanced technical indicators for trading analysis"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index (RSI)"""
        try:
            if len(prices) < period + 1:
                return pd.Series(index=prices.index, dtype=float)
            
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi.fillna(50)  # Fill NaN with neutral RSI value
            
        except Exception as e:
            self.logger.error(f"Error calculating RSI: {e}")
            return pd.Series(index=prices.index, dtype=float)
    
    def calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        try:
            if len(prices) < slow + signal:
                empty_series = pd.Series(index=prices.index, dtype=float)
                return empty_series, empty_series, empty_series
            
            # Calculate EMAs
            ema_fast = prices.ewm(span=fast).mean()
            ema_slow = prices.ewm(span=slow).mean()
            
            # MACD line
            macd_line = ema_fast - ema_slow
            
            # Signal line
            signal_line = macd_line.ewm(span=signal).mean()
            
            # Histogram
            histogram = macd_line - signal_line
            
            return macd_line, signal_line, histogram
            
        except Exception as e:
            self.logger.error(f"Error calculating MACD: {e}")
            empty_series = pd.Series(index=prices.index, dtype=float)
            return empty_series, empty_series, empty_series
    
    def calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: int = 2) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        try:
            if len(prices) < period:
                empty_series = pd.Series(index=prices.index, dtype=float)
                return empty_series, empty_series, empty_series
            
            # Middle band (SMA)
            middle_band = prices.rolling(window=period).mean()
            
            # Standard deviation
            std = prices.rolling(window=period).std()
            
            # Upper and lower bands
            upper_band = middle_band + (std * std_dev)
            lower_band = middle_band - (std * std_dev)
            
            return upper_band, middle_band, lower_band
            
        except Exception as e:
            self.logger.error(f"Error calculating Bollinger Bands: {e}")
            empty_series = pd.Series(index=prices.index, dtype=float)
            return empty_series, empty_series, empty_series
    
    def calculate_stochastic(self, high: pd.Series, low: pd.Series, close: pd.Series, 
                           k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Calculate Stochastic Oscillator"""
        try:
            if len(close) < k_period:
                empty_series = pd.Series(index=close.index, dtype=float)
                return empty_series, empty_series
            
            # %K line
            lowest_low = low.rolling(window=k_period).min()
            highest_high = high.rolling(window=k_period).max()
            
            k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
            
            # %D line (SMA of %K)
            d_percent = k_percent.rolling(window=d_period).mean()
            
            return k_percent, d_percent
            
        except Exception as e:
            self.logger.error(f"Error calculating Stochastic: {e}")
            empty_series = pd.Series(index=close.index, dtype=float)
            return empty_series, empty_series
    
    def calculate_williams_r(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Williams %R"""
        try:
            if len(close) < period:
                return pd.Series(index=close.index, dtype=float)
            
            highest_high = high.rolling(window=period).max()
            lowest_low = low.rolling(window=period).min()
            
            williams_r = -100 * ((highest_high - close) / (highest_high - lowest_low))
            
            return williams_r
            
        except Exception as e:
            self.logger.error(f"Error calculating Williams %R: {e}")
            return pd.Series(index=close.index, dtype=float)
    
    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average True Range (ATR)"""
        try:
            if len(close) < period + 1:
                return pd.Series(index=close.index, dtype=float)
            
            # True Range calculations
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            
            # True Range is the maximum of the three
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # ATR is the moving average of True Range
            atr = true_range.rolling(window=period).mean()
            
            return atr
            
        except Exception as e:
            self.logger.error(f"Error calculating ATR: {e}")
            return pd.Series(index=close.index, dtype=float)
    
    def calculate_adx(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Average Directional Index (ADX)"""
        try:
            if len(close) < period * 2:
                return pd.Series(index=close.index, dtype=float)
            
            # Directional Movement
            dm_plus = high.diff()
            dm_minus = low.diff()
            
            # Only positive values
            dm_plus = dm_plus.where(dm_plus > 0, 0)
            dm_minus = dm_minus.where(dm_minus < 0, 0)
            dm_minus = abs(dm_minus)
            
            # True Range
            tr = self.calculate_atr(high, low, close, period)
            
            # Smoothed DM and TR
            dm_plus_smooth = dm_plus.rolling(window=period).mean()
            dm_minus_smooth = dm_minus.rolling(window=period).mean()
            tr_smooth = tr.rolling(window=period).mean()
            
            # Directional Indicators
            di_plus = 100 * (dm_plus_smooth / tr_smooth)
            di_minus = 100 * (dm_minus_smooth / tr_smooth)
            
            # Directional Index
            dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus)
            
            # ADX
            adx = dx.rolling(window=period).mean()
            
            return adx
            
        except Exception as e:
            self.logger.error(f"Error calculating ADX: {e}")
            return pd.Series(index=close.index, dtype=float)
    
    def calculate_cci(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
        """Calculate Commodity Channel Index (CCI)"""
        try:
            if len(close) < period:
                return pd.Series(index=close.index, dtype=float)
            
            # Typical Price
            typical_price = (high + low + close) / 3
            
            # Simple Moving Average of Typical Price
            sma_tp = typical_price.rolling(window=period).mean()
            
            # Mean Deviation
            mean_deviation = typical_price.rolling(window=period).apply(
                lambda x: np.mean(np.abs(x - x.mean()))
            )
            
            # CCI
            cci = (typical_price - sma_tp) / (0.015 * mean_deviation)
            
            return cci
            
        except Exception as e:
            self.logger.error(f"Error calculating CCI: {e}")
            return pd.Series(index=close.index, dtype=float)
    
    def calculate_momentum(self, prices: pd.Series, period: int = 10) -> pd.Series:
        """Calculate Momentum indicator"""
        try:
            if len(prices) < period:
                return pd.Series(index=prices.index, dtype=float)
            
            momentum = prices - prices.shift(period)
            return momentum
            
        except Exception as e:
            self.logger.error(f"Error calculating Momentum: {e}")
            return pd.Series(index=prices.index, dtype=float)
    
    def calculate_rate_of_change(self, prices: pd.Series, period: int = 10) -> pd.Series:
        """Calculate Rate of Change (ROC)"""
        try:
            if len(prices) < period:
                return pd.Series(index=prices.index, dtype=float)
            
            roc = ((prices - prices.shift(period)) / prices.shift(period)) * 100
            return roc
            
        except Exception as e:
            self.logger.error(f"Error calculating ROC: {e}")
            return pd.Series(index=prices.index, dtype=float)
    
    def calculate_moving_averages(self, prices: pd.Series, periods: list = [5, 10, 20, 50, 200]) -> Dict[str, pd.Series]:
        """Calculate multiple moving averages"""
        try:
            moving_averages = {}
            
            for period in periods:
                if len(prices) >= period:
                    # Simple Moving Average
                    sma = prices.rolling(window=period).mean()
                    moving_averages[f'SMA_{period}'] = sma
                    
                    # Exponential Moving Average
                    ema = prices.ewm(span=period).mean()
                    moving_averages[f'EMA_{period}'] = ema
            
            return moving_averages
            
        except Exception as e:
            self.logger.error(f"Error calculating moving averages: {e}")
            return {}
    
    def calculate_volume_indicators(self, prices: pd.Series, volume: pd.Series, period: int = 20) -> Dict[str, pd.Series]:
        """Calculate volume-based indicators"""
        try:
            if len(prices) < period or len(volume) < period:
                return {}
            
            indicators = {}
            
            # Volume SMA
            indicators['Volume_SMA'] = volume.rolling(window=period).mean()
            
            # Volume Ratio
            indicators['Volume_Ratio'] = volume / indicators['Volume_SMA']
            
            # On-Balance Volume (OBV)
            obv = pd.Series(index=prices.index, dtype=float)
            obv.iloc[0] = volume.iloc[0]
            
            for i in range(1, len(prices)):
                if prices.iloc[i] > prices.iloc[i-1]:
                    obv.iloc[i] = obv.iloc[i-1] + volume.iloc[i]
                elif prices.iloc[i] < prices.iloc[i-1]:
                    obv.iloc[i] = obv.iloc[i-1] - volume.iloc[i]
                else:
                    obv.iloc[i] = obv.iloc[i-1]
            
            indicators['OBV'] = obv
            
            # Volume Price Trend (VPT)
            vpt = (volume * prices.pct_change()).cumsum()
            indicators['VPT'] = vpt
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"Error calculating volume indicators: {e}")
            return {}
    
    def get_support_resistance(self, prices: pd.Series, window: int = 20) -> Dict[str, float]:
        """Identify potential support and resistance levels"""
        try:
            if len(prices) < window:
                return {'support': 0, 'resistance': 0}
            
            # Recent high and low
            recent_high = prices.tail(window).max()
            recent_low = prices.tail(window).min()
            
            # Current price
            current_price = prices.iloc[-1]
            
            # Support and resistance levels
            support = recent_low
            resistance = recent_high
            
            return {
                'support': support,
                'resistance': resistance,
                'current_price': current_price,
                'distance_to_support': current_price - support,
                'distance_to_resistance': resistance - current_price
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating support/resistance: {e}")
            return {'support': 0, 'resistance': 0}
    
    def get_indicator_summary(self, prices: pd.Series, high: Optional[pd.Series] = None,
                            low: Optional[pd.Series] = None,
                            volume: Optional[pd.Series] = None) -> Dict:
        """Get summary of all indicators"""
        try:
            summary = {}
            
            # Basic indicators
            summary['rsi'] = self.calculate_rsi(prices).iloc[-1] if len(prices) > 14 else 50
            summary['macd'], summary['macd_signal'], summary['macd_histogram'] = self.calculate_macd(prices)
            
            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands(prices)
            summary['bb_upper'] = bb_upper.iloc[-1] if not bb_upper.empty else prices.iloc[-1]
            summary['bb_lower'] = bb_lower.iloc[-1] if not bb_lower.empty else prices.iloc[-1]
            
            # Moving averages
            mas = self.calculate_moving_averages(prices, [5, 20, 50])
            for name, ma in mas.items():
                summary[name] = ma.iloc[-1] if not ma.empty else prices.iloc[-1]
            
            # Support and resistance
            if high is not None and low is not None:
                sr = self.get_support_resistance(prices)
                summary.update(sr)
            
            # Volume indicators
            if volume is not None:
                vol_indicators = self.calculate_volume_indicators(prices, volume)
                for name, indicator in vol_indicators.items():
                    summary[name] = indicator.iloc[-1] if not indicator.empty else 0
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting indicator summary: {e}")
            return {}


def add_enhanced_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add enhanced technical indicators to DataFrame
    """
    try:
        if df.empty:
            return df
            
        # Create instance
        indicators = EnhancedIndicators()
        
        # Add basic moving averages
        df['sma_fast'] = df['close'].rolling(window=10).mean()
        df['sma_slow'] = df['close'].rolling(window=30).mean()
        
        # Add RSI
        df['rsi'] = indicators.calculate_rsi(df['close'])
        
        # Add MACD
        macd, signal, histogram = indicators.calculate_macd(df['close'])
        df['macd'] = macd
        df['macd_signal'] = signal
        df['macd_histogram'] = histogram
        
        # Add Bollinger Bands
        bb_upper, bb_middle, bb_lower = indicators.calculate_bollinger_bands(df['close'])
        df['bb_upper'] = bb_upper
        df['bb_middle'] = bb_middle
        df['bb_lower'] = bb_lower
        
        # Add ATR
        if 'high' in df.columns and 'low' in df.columns:
            df['atr'] = indicators.calculate_atr(df['high'], df['low'], df['close'])
        
        # Add Stochastic
        if 'high' in df.columns and 'low' in df.columns:
            stoch_k, stoch_d = indicators.calculate_stochastic(df['high'], df['low'], df['close'])
            df['stoch_k'] = stoch_k
            df['stoch_d'] = stoch_d
        
        # Fill NaN values
        df = df.ffill().fillna(0)
        
        return df
        
    except Exception as e:
        print(f"Error adding enhanced indicators: {e}")
        return df


def generate_enhanced_signals(df: pd.DataFrame) -> pd.Series:
    """
    Generate enhanced trading signals
    """
    try:
        if df.empty:
            return pd.Series(dtype=int)
        
        signals = pd.Series(0, index=df.index)
        
        # RSI signals
        rsi_bullish = (df['rsi'] < 30) & (df['rsi'].shift(1) >= 30)
        rsi_bearish = (df['rsi'] > 70) & (df['rsi'].shift(1) <= 70)
        
        # MACD signals
        macd_bullish = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))
        macd_bearish = (df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1))
        
        # Moving average signals
        ma_bullish = (df['close'] > df['sma_fast']) & (df['sma_fast'] > df['sma_slow'])
        ma_bearish = (df['close'] < df['sma_fast']) & (df['sma_fast'] < df['sma_slow'])
        
        # Bollinger Bands signals
        bb_bullish = df['close'] < df['bb_lower']
        bb_bearish = df['close'] > df['bb_upper']
        
        # Combine signals
        signals = signals.where(~rsi_bullish, 1)
        signals = signals.where(~rsi_bearish, -1)
        signals = signals.where(~macd_bullish, 1)
        signals = signals.where(~macd_bearish, -1)
        signals = signals.where(~ma_bullish, 1)
        signals = signals.where(~ma_bearish, -1)
        signals = signals.where(~bb_bullish, 1)
        signals = signals.where(~bb_bearish, -1)
        
        return signals.fillna(0)
        
    except Exception as e:
        print(f"Error generating enhanced signals: {e}")
        return pd.Series(0, index=df.index)