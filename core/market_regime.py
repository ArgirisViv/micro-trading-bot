"""
Market Regime Detection for Trading Bot Dashboard
Provides market trend analysis, volatility regime detection, and market state classification
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
import warnings
warnings.filterwarnings('ignore')

class MarketRegimeDetector:
    """Market regime detection and analysis system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def detect_market_regime(self, data: pd.DataFrame) -> str:
        """Detect overall market regime"""
        try:
            if 'close' not in data.columns or len(data) < 50:
                return "UNKNOWN"
            
            prices = data['close']
            
            # Calculate key metrics
            returns = prices.pct_change().dropna()
            volatility = returns.rolling(window=20).std()
            trend = self.detect_trend(prices)
            volatility_regime = self.detect_volatility_regime(prices)
            
            # Determine regime based on trend and volatility
            if trend == "UPTREND" and volatility_regime == "LOW":
                return "BULL_MARKET"
            elif trend == "UPTREND" and volatility_regime == "HIGH":
                return "BULL_VOLATILE"
            elif trend == "DOWNTREND" and volatility_regime == "LOW":
                return "BEAR_MARKET"
            elif trend == "DOWNTREND" and volatility_regime == "HIGH":
                return "BEAR_VOLATILE"
            elif trend == "SIDEWAYS" and volatility_regime == "LOW":
                return "CONSOLIDATION"
            elif trend == "SIDEWAYS" and volatility_regime == "HIGH":
                return "CHOPPY"
            else:
                return "MIXED"
                
        except Exception as e:
            self.logger.error(f"Error detecting market regime: {e}")
            return "UNKNOWN"
    
    def detect_trend(self, prices: pd.Series, short_period: int = 20, long_period: int = 50) -> str:
        """Detect market trend using moving averages"""
        try:
            if len(prices) < long_period:
                return "UNKNOWN"
            
            # Calculate moving averages
            short_ma = prices.rolling(window=short_period).mean()
            long_ma = prices.rolling(window=long_period).mean()
            
            # Get current values
            current_short = short_ma.iloc[-1]
            current_long = long_ma.iloc[-1]
            current_price = prices.iloc[-1]
            
            # Trend determination
            if current_price > current_short > current_long:
                return "UPTREND"
            elif current_price < current_short < current_long:
                return "DOWNTREND"
            elif abs(current_short - current_long) / current_long < 0.02:  # Less than 2% difference
                return "SIDEWAYS"
            else:
                return "MIXED"
                
        except Exception as e:
            self.logger.error(f"Error detecting trend: {e}")
            return "UNKNOWN"
    
    def detect_volatility_regime(self, prices: pd.Series, window: int = 20) -> str:
        """Detect volatility regime"""
        try:
            if len(prices) < window:
                return "UNKNOWN"
            
            # Calculate returns and volatility
            returns = prices.pct_change().dropna()
            volatility = returns.rolling(window=window).std()
            
            # Get current volatility
            current_vol = volatility.iloc[-1]
            
            # Calculate historical volatility percentiles
            vol_percentiles = volatility.quantile([0.25, 0.75])
            vol_25 = vol_percentiles[0.25]
            vol_75 = vol_percentiles[0.75]
            
            # Regime classification
            if current_vol < vol_25:
                return "LOW"
            elif current_vol > vol_75:
                return "HIGH"
            else:
                return "MEDIUM"
                
        except Exception as e:
            self.logger.error(f"Error detecting volatility regime: {e}")
            return "UNKNOWN"
    
    def detect_momentum_regime(self, prices: pd.Series, period: int = 14) -> str:
        """Detect momentum regime using RSI"""
        try:
            if len(prices) < period:
                return "UNKNOWN"
            
            # Calculate RSI
            rsi = self._calculate_rsi(prices, period)
            current_rsi = rsi.iloc[-1]
            
            # Momentum classification
            if current_rsi > 70:
                return "OVERBOUGHT"
            elif current_rsi < 30:
                return "OVERSOLD"
            elif 40 <= current_rsi <= 60:
                return "NEUTRAL"
            else:
                return "MIXED"
                
        except Exception as e:
            self.logger.error(f"Error detecting momentum regime: {e}")
            return "UNKNOWN"
    
    def detect_support_resistance_regime(self, prices: pd.Series, window: int = 20) -> str:
        """Detect if price is near support or resistance"""
        try:
            if len(prices) < window:
                return "UNKNOWN"
            
            current_price = prices.iloc[-1]
            
            # Calculate recent support and resistance
            recent_high = prices.tail(window).max()
            recent_low = prices.tail(window).min()
            
            # Calculate distances
            distance_to_high = (recent_high - current_price) / current_price
            distance_to_low = (current_price - recent_low) / current_price
            
            # Threshold for "near" support/resistance (5%)
            threshold = 0.05
            
            if distance_to_high <= threshold:
                return "NEAR_RESISTANCE"
            elif distance_to_low <= threshold:
                return "NEAR_SUPPORT"
            else:
                return "MIDDLE_RANGE"
                
        except Exception as e:
            self.logger.error(f"Error detecting support/resistance regime: {e}")
            return "UNKNOWN"
    
    def detect_volume_regime(self, data: pd.DataFrame, window: int = 20) -> str:
        """Detect volume regime"""
        try:
            if 'volume' not in data.columns or len(data) < window:
                return "UNKNOWN"
            
            volume = data['volume']
            current_volume = volume.iloc[-1]
            
            # Calculate volume moving average
            volume_ma = volume.rolling(window=window).mean()
            current_volume_ma = volume_ma.iloc[-1]
            
            # Volume ratio
            volume_ratio = current_volume / current_volume_ma if current_volume_ma > 0 else 1
            
            # Regime classification
            if volume_ratio > 1.5:
                return "HIGH_VOLUME"
            elif volume_ratio < 0.5:
                return "LOW_VOLUME"
            else:
                return "NORMAL_VOLUME"
                
        except Exception as e:
            self.logger.error(f"Error detecting volume regime: {e}")
            return "UNKNOWN"
    
    def detect_correlation_regime(self, data: pd.DataFrame, window: int = 30) -> str:
        """Detect correlation regime between different assets"""
        try:
            if len(data.columns) < 2 or len(data) < window:
                return "UNKNOWN"
            
            # Calculate returns for all columns
            returns_data = {}
            for col in data.columns:
                if col in ['open', 'high', 'low', 'close', 'volume']:
                    continue
                returns_data[col] = data[col].pct_change().dropna()
            
            if len(returns_data) < 2:
                return "UNKNOWN"
            
            # Create returns DataFrame
            returns_df = pd.DataFrame(returns_data)
            returns_df = returns_df.dropna()
            
            if len(returns_df) < window:
                return "UNKNOWN"
            
            # Calculate rolling correlation
            correlation_matrix = returns_df.tail(window).corr()
            
            # Get average correlation (excluding diagonal)
            mask = ~np.eye(correlation_matrix.shape[0], dtype=bool)
            avg_correlation = correlation_matrix[mask].mean()
            
            # Regime classification
            if avg_correlation > 0.7:
                return "HIGH_CORRELATION"
            elif avg_correlation < 0.3:
                return "LOW_CORRELATION"
            else:
                return "MEDIUM_CORRELATION"
                
        except Exception as e:
            self.logger.error(f"Error detecting correlation regime: {e}")
            return "UNKNOWN"
    
    def get_regime_summary(self, data: pd.DataFrame) -> Dict:
        """Get comprehensive market regime summary"""
        try:
            if 'close' not in data.columns:
                return {}
            
            prices = data['close']
            
            summary = {
                'overall_regime': self.detect_market_regime(data),
                'trend': self.detect_trend(prices),
                'volatility_regime': self.detect_volatility_regime(prices),
                'momentum_regime': self.detect_momentum_regime(prices),
                'support_resistance_regime': self.detect_support_resistance_regime(prices),
                'volume_regime': self.detect_volume_regime(data),
                'correlation_regime': self.detect_correlation_regime(data)
            }
            
            # Add confidence scores
            summary['confidence'] = self._calculate_regime_confidence(summary)
            
            # Add regime characteristics
            summary['characteristics'] = self._get_regime_characteristics(summary)
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting regime summary: {e}")
            return {}
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator"""
        try:
            if len(prices) < period + 1:
                return pd.Series(index=prices.index, dtype=float)
            
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi.fillna(50)
            
        except Exception as e:
            self.logger.error(f"Error calculating RSI: {e}")
            return pd.Series(index=prices.index, dtype=float)
    
    def _calculate_regime_confidence(self, regime_summary: Dict) -> float:
        """Calculate confidence in regime detection"""
        try:
            # Count how many regimes are not "UNKNOWN"
            known_regimes = sum(1 for regime in regime_summary.values() if regime != "UNKNOWN")
            total_regimes = len(regime_summary) - 1  # Exclude confidence field
            
            if total_regimes == 0:
                return 0
            
            confidence = known_regimes / total_regimes
            
            # Boost confidence if overall regime is clear
            if regime_summary.get('overall_regime') not in ["UNKNOWN", "MIXED"]:
                confidence += 0.1
            
            return min(confidence, 1.0)
            
        except Exception as e:
            self.logger.error(f"Error calculating regime confidence: {e}")
            return 0
    
    def _get_regime_characteristics(self, regime_summary: Dict) -> List[str]:
        """Get characteristics of the detected regime"""
        try:
            characteristics = []
            
            # Trend characteristics
            trend = regime_summary.get('trend', 'UNKNOWN')
            if trend == "UPTREND":
                characteristics.append("Bullish momentum")
            elif trend == "DOWNTREND":
                characteristics.append("Bearish momentum")
            elif trend == "SIDEWAYS":
                characteristics.append("Range-bound trading")
            
            # Volatility characteristics
            volatility = regime_summary.get('volatility_regime', 'UNKNOWN')
            if volatility == "HIGH":
                characteristics.append("High volatility")
            elif volatility == "LOW":
                characteristics.append("Low volatility")
            
            # Momentum characteristics
            momentum = regime_summary.get('momentum_regime', 'UNKNOWN')
            if momentum == "OVERBOUGHT":
                characteristics.append("Potential reversal")
            elif momentum == "OVERSOLD":
                characteristics.append("Potential bounce")
            
            # Volume characteristics
            volume = regime_summary.get('volume_regime', 'UNKNOWN')
            if volume == "HIGH_VOLUME":
                characteristics.append("High participation")
            elif volume == "LOW_VOLUME":
                characteristics.append("Low participation")
            
            return characteristics
            
        except Exception as e:
            self.logger.error(f"Error getting regime characteristics: {e}")
            return []
    
    def get_regime_recommendations(self, regime_summary: Dict) -> List[str]:
        """Get trading recommendations based on regime"""
        try:
            recommendations = []
            
            overall_regime = regime_summary.get('overall_regime', 'UNKNOWN')
            trend = regime_summary.get('trend', 'UNKNOWN')
            volatility = regime_summary.get('volatility_regime', 'UNKNOWN')
            
            # Overall regime recommendations
            if overall_regime == "BULL_MARKET":
                recommendations.extend([
                    "Consider long positions",
                    "Use pullbacks as entry opportunities",
                    "Set trailing stops"
                ])
            elif overall_regime == "BEAR_MARKET":
                recommendations.extend([
                    "Consider short positions",
                    "Use rallies as entry opportunities",
                    "Set tight stops"
                ])
            elif overall_regime == "CONSOLIDATION":
                recommendations.extend([
                    "Range trading strategies",
                    "Buy support, sell resistance",
                    "Use oscillators for timing"
                ])
            
            # Volatility-based recommendations
            if volatility == "HIGH":
                recommendations.extend([
                    "Wider stops due to volatility",
                    "Reduce position sizes",
                    "Consider options strategies"
                ])
            elif volatility == "LOW":
                recommendations.extend([
                    "Tighter stops possible",
                    "Normal position sizes",
                    "Trend-following strategies"
                ])
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error getting regime recommendations: {e}")
            return []
