# core/macro_factors.py
"""
Macro Factors Integration Module
Incorporates economic indicators, interest rates, and market sentiment
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
# yfinance removed - using mock data instead
import requests
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

@dataclass
class MacroEnvironment:
    """Macroeconomic environment classification"""
    economic_cycle: str  # 'expansion', 'contraction', 'peak', 'trough'
    monetary_policy: str  # 'accommodative', 'neutral', 'restrictive'
    market_sentiment: str  # 'bullish', 'bearish', 'neutral'
    volatility_regime: str  # 'low', 'medium', 'high'
    confidence_score: float  # 0-1

class MacroFactorsAnalyzer:
    """
    Analyzes macroeconomic factors and their impact on trading
    """
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 update_frequency: str = 'daily'):
        self.api_key = api_key
        self.update_frequency = update_frequency
        self.cache = {}
        self.last_update = None
        
    def analyze_macro_environment(self, symbol: Optional[str] = None) -> MacroEnvironment:
        """
        Analyze current macroeconomic environment
        """
        try:
            # Get economic indicators
            economic_data = self._get_economic_indicators()
            
            # Get monetary policy indicators
            monetary_data = self._get_monetary_indicators()
            
            # Get market sentiment
            sentiment_data = self._get_market_sentiment(symbol)
            
            # Get volatility indicators
            volatility_data = self._get_volatility_indicators()
            
            # Classify environment
            economic_cycle = self._classify_economic_cycle(economic_data)
            monetary_policy = self._classify_monetary_policy(monetary_data)
            market_sentiment = self._classify_market_sentiment(sentiment_data)
            volatility_regime = self._classify_volatility_regime(volatility_data)
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                economic_data, monetary_data, sentiment_data, volatility_data
            )
            
            return MacroEnvironment(
                economic_cycle=economic_cycle,
                monetary_policy=monetary_policy,
                market_sentiment=market_sentiment,
                volatility_regime=volatility_regime,
                confidence_score=confidence_score
            )
            
        except Exception as e:
            print(f"Warning: Macro analysis failed: {e}")
            return self._default_macro_environment()
    
    def _get_economic_indicators(self) -> Dict[str, float]:
        """Mock economic indicators - yfinance removed for stability"""
        # Return default indicators to avoid errors
        return {
            'gdp_growth_proxy': 0.0,
            'employment_proxy': 0.0,
            'inflation_proxy': 0.0,
            'consumer_confidence': 0.0
        }
    
    def _get_monetary_indicators(self) -> Dict[str, float]:
        """Return no live indicators while the external provider is disabled."""
        return {}
    
    def _get_market_sentiment(self, symbol: Optional[str] = None) -> Dict[str, float]:
        """Return no live sentiment while the external provider is disabled."""
        return {}
    
    def _get_volatility_indicators(self) -> Dict[str, float]:
        """Return no live volatility data while the external provider is disabled."""
        return {}
    
    def _classify_economic_cycle(self, data: Dict[str, float]) -> str:
        """Classify economic cycle based on indicators"""
        try:
            if not data:
                return 'neutral'
            
            # Calculate economic score
            score = 0.0
            weights = 0.0
            
            if 'gdp_growth_proxy' in data:
                gdp_score = np.tanh(data['gdp_growth_proxy'] * 5)  # Normalize to -1 to 1
                score += gdp_score * 0.4
                weights += 0.4
            
            if 'employment_proxy' in data:
                emp_score = np.tanh(data['employment_proxy'] * 5)
                score += emp_score * 0.3
                weights += 0.3
            
            if 'consumer_confidence' in data:
                cons_score = np.tanh(data['consumer_confidence'] * 5)
                score += cons_score * 0.3
                weights += 0.3
            
            if weights > 0:
                normalized_score = score / weights
                
                if normalized_score > 0.3:
                    return 'expansion'
                elif normalized_score < -0.3:
                    return 'contraction'
                elif normalized_score > 0.1:
                    return 'peak'
                else:
                    return 'trough'
            
            return 'neutral'
            
        except:
            return 'neutral'
    
    def _classify_monetary_policy(self, data: Dict[str, float]) -> str:
        """Classify monetary policy stance"""
        try:
            if not data:
                return 'neutral'
            
            score = 0.0
            weights = 0.0
            
            if 'yield_curve_spread' in data:
                # Steep curve = accommodative, flat/inverted = restrictive
                curve_score = np.tanh(data['yield_curve_spread'] * 0.1)
                score += curve_score * 0.4
                weights += 0.4
            
            if 'fed_funds_proxy' in data:
                # Low rates = accommodative, high rates = restrictive
                rate_score = -np.tanh(data['fed_funds_proxy'] * 0.1)
                score += rate_score * 0.3
                weights += 0.3
            
            if 'dollar_strength' in data:
                # Strong dollar = restrictive, weak dollar = accommodative
                dollar_score = -np.tanh(data['dollar_strength'] * 2)
                score += dollar_score * 0.3
                weights += 0.3
            
            if weights > 0:
                normalized_score = score / weights
                
                if normalized_score > 0.3:
                    return 'accommodative'
                elif normalized_score < -0.3:
                    return 'restrictive'
                else:
                    return 'neutral'
            
            return 'neutral'
            
        except:
            return 'neutral'
    
    def _classify_market_sentiment(self, data: Dict[str, float]) -> str:
        """Classify market sentiment"""
        try:
            if not data:
                return 'neutral'
            
            score = 0.0
            weights = 0.0
            
            if 'fear_greed' in data:
                score += data['fear_greed'] * 0.4
                weights += 0.4
            
            if 'risk_sentiment' in data:
                risk_score = np.tanh(data['risk_sentiment'] * 2)
                score += risk_score * 0.3
                weights += 0.3
            
            if 'sector_dispersion' in data:
                # High dispersion = bearish, low dispersion = bullish
                disp_score = -np.tanh(data['sector_dispersion'] * 10)
                score += disp_score * 0.3
                weights += 0.3
            
            if weights > 0:
                normalized_score = score / weights
                
                if normalized_score > 0.2:
                    return 'bullish'
                elif normalized_score < -0.2:
                    return 'bearish'
                else:
                    return 'neutral'
            
            return 'neutral'
            
        except:
            return 'neutral'
    
    def _classify_volatility_regime(self, data: Dict[str, float]) -> str:
        """Classify volatility regime"""
        try:
            if not data:
                return 'medium'
            
            if 'current_vix' in data:
                vix = data['current_vix']
                
                if vix < 15:
                    return 'low'
                elif vix > 25:
                    return 'high'
                else:
                    return 'medium'
            
            return 'medium'
            
        except:
            return 'medium'
    
    def _calculate_confidence_score(self, 
                                  economic_data: Dict[str, float],
                                  monetary_data: Dict[str, float],
                                  sentiment_data: Dict[str, float],
                                  volatility_data: Dict[str, float]) -> float:
        """Calculate confidence score for macro analysis"""
        try:
            # Count available indicators
            total_indicators = len(economic_data) + len(monetary_data) + len(sentiment_data) + len(volatility_data)
            
            if total_indicators == 0:
                return 0.5
            
            # Base confidence on data availability
            data_confidence = min(1.0, total_indicators / 20)  # Normalize to 0-1
            
            # Adjust based on data quality (volatility of indicators)
            quality_scores = []
            
            for data_dict in [economic_data, monetary_data, sentiment_data, volatility_data]:
                if data_dict:
                    values = list(data_dict.values())
                    if len(values) > 1:
                        # Lower volatility = higher quality
                        vol = np.std(values)
                        quality = max(0, 1 - vol)
                        quality_scores.append(quality)
            
            if quality_scores:
                avg_quality = np.mean(quality_scores)
                final_confidence = (data_confidence + avg_quality) / 2
            else:
                final_confidence = data_confidence
            
            return max(0.1, min(0.95, final_confidence))
            
        except:
            return 0.5
    
    def _default_macro_environment(self) -> MacroEnvironment:
        """Return default macro environment when analysis fails"""
        return MacroEnvironment(
            economic_cycle='neutral',
            monetary_policy='neutral',
            market_sentiment='neutral',
            volatility_regime='medium',
            confidence_score=0.5
        )
    
    def get_strategy_adaptations(self, macro_env: MacroEnvironment) -> Dict[str, float]:
        """Get strategy adaptation parameters based on macro environment"""
        adaptations = {}
        
        # Economic cycle adaptations
        if macro_env.economic_cycle == 'expansion':
            adaptations.update({
                'growth_weight': 0.8,
                'value_weight': 0.2,
                'momentum_multiplier': 1.2,
                'risk_tolerance': 1.1
            })
        elif macro_env.economic_cycle == 'contraction':
            adaptations.update({
                'growth_weight': 0.2,
                'value_weight': 0.8,
                'momentum_multiplier': 0.8,
                'risk_tolerance': 0.9
            })
        else:
            adaptations.update({
                'growth_weight': 0.5,
                'value_weight': 0.5,
                'momentum_multiplier': 1.0,
                'risk_tolerance': 1.0
            })
        
        # Monetary policy adaptations
        if macro_env.monetary_policy == 'accommodative':
            adaptations.update({
                'duration_multiplier': 1.2,
                'growth_bias': 1.1,
                'leverage_multiplier': 1.1
            })
        elif macro_env.monetary_policy == 'restrictive':
            adaptations.update({
                'duration_multiplier': 0.8,
                'growth_bias': 0.9,
                'leverage_multiplier': 0.9
            })
        else:
            adaptations.update({
                'duration_multiplier': 1.0,
                'growth_bias': 1.0,
                'leverage_multiplier': 1.0
            })
        
        # Market sentiment adaptations
        if macro_env.market_sentiment == 'bullish':
            adaptations.update({
                'trend_following_weight': 0.7,
                'mean_reversion_weight': 0.3,
                'position_size_multiplier': 1.1
            })
        elif macro_env.market_sentiment == 'bearish':
            adaptations.update({
                'trend_following_weight': 0.3,
                'mean_reversion_weight': 0.7,
                'position_size_multiplier': 0.9
            })
        else:
            adaptations.update({
                'trend_following_weight': 0.5,
                'mean_reversion_weight': 0.5,
                'position_size_multiplier': 1.0
            })
        
        # Volatility regime adaptations
        if macro_env.volatility_regime == 'high':
            adaptations.update({
                'stop_loss_multiplier': 1.5,
                'take_profit_multiplier': 1.5,
                'position_size_multiplier': 0.7
            })
        elif macro_env.volatility_regime == 'low':
            adaptations.update({
                'stop_loss_multiplier': 0.8,
                'take_profit_multiplier': 0.8,
                'position_size_multiplier': 1.2
            })
        else:
            adaptations.update({
                'stop_loss_multiplier': 1.0,
                'take_profit_multiplier': 1.0,
                'position_size_multiplier': 1.0
            })
        
        return adaptations

def analyze_macro_factors(symbol: str | None = None) -> MacroEnvironment:
    """
    Convenience function to analyze macro factors
    """
    analyzer = MacroFactorsAnalyzer()
    return analyzer.analyze_macro_environment(symbol)

def get_macro_adaptations(macro_env: MacroEnvironment) -> Dict[str, float]:
    """
    Convenience function to get macro-based strategy adaptations
    """
    analyzer = MacroFactorsAnalyzer()
    return analyzer.get_strategy_adaptations(macro_env)
