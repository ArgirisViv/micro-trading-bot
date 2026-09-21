# core/hybrid_strategy.py
"""
Hybrid Trading Strategy - Best of Both Worlds
Combines Active Trading (70%) + Value Investing (30%) with Dynamic Allocation
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

@dataclass
class HybridSignal:
    """Hybrid strategy trading signal"""
    symbol: str
    active_trading_signal: int  # -1, 0, 1
    value_investing_signal: int  # -1, 0, 1
    combined_signal: int  # -1, 0, 1
    confidence_score: float  # 0-1
    strategy_weights: Dict[str, float]
    allocation: Dict[str, float]
    recommendation: str

@dataclass
class PortfolioState:
    """Current portfolio state"""
    active_trading_value: float
    value_investing_value: float
    total_value: float
    allocation_ratio: Dict[str, float]
    performance_metrics: Dict[str, float]

class HybridStrategy:
    """
    Hybrid strategy combining active trading and value investing
    """
    
    def __init__(self, 
                 base_active_allocation: float = 0.7,
                 base_value_allocation: float = 0.3,
                 confidence_threshold: float = 0.6,
                 rebalancing_threshold: float = 0.05):
        self.base_active_allocation = base_active_allocation
        self.base_value_allocation = base_value_allocation
        self.confidence_threshold = confidence_threshold
        self.rebalancing_threshold = rebalancing_threshold
        
        # Import required modules
        from .enhanced_strategy import apply_enhanced_strategy
        from .enhanced_fundamentals import analyze_business_quality
        from .portfolio_allocator import calculate_optimal_allocation
        from .market_regime import detect_market_regime
        from .macro_factors import analyze_macro_factors
        
        self.apply_enhanced_strategy = apply_enhanced_strategy
        self.analyze_business_quality = analyze_business_quality
        self.calculate_optimal_allocation = calculate_optimal_allocation
        self.detect_market_regime = detect_market_regime
        self.analyze_macro_factors = analyze_macro_factors
    
    def generate_hybrid_signals(self, 
                               symbols: List[str],
                               market_data: Dict[str, pd.DataFrame],
                               portfolio_state: PortfolioState = None) -> List[HybridSignal]:
        """
        Generate hybrid trading signals for all symbols
        """
        try:
            # Detect market regime and macro environment
            market_regime = self._detect_market_conditions(symbols, market_data)
            
            # Calculate optimal allocation
            allocation = self._calculate_dynamic_allocation(market_regime, portfolio_state)
            
            # Generate signals for each symbol
            signals = []
            for symbol in symbols:
                if symbol in market_data:
                    signal = self._generate_symbol_signal(
                        symbol, market_data[symbol], market_regime, allocation
                    )
                    signals.append(signal)
            
            return signals
            
        except Exception as e:
            print(f"Warning: Hybrid signal generation failed: {e}")
            return []
    
    def _detect_market_conditions(self, symbols: List[str], market_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Detect market regime and macro environment"""
        try:
            # Use first symbol for market regime detection
            if symbols and symbols[0] in market_data:
                first_symbol = symbols[0]
                df = market_data[first_symbol]
                
                # Detect market regime
                market_regime = self.detect_market_regime(df)
                
                # Analyze macro factors
                macro_env = self.analyze_macro_factors(first_symbol)
                
                return {
                    'market_regime': market_regime.regime_type,
                    'regime_confidence': market_regime.confidence,
                    'macro_environment': macro_env.economic_cycle,
                    'macro_confidence': macro_env.confidence_score
                }
            
            return {
                'market_regime': 'ranging_low_vol',
                'regime_confidence': 0.5,
                'macro_environment': 'neutral',
                'macro_confidence': 0.5
            }
            
        except Exception as e:
            print(f"Warning: Market condition detection failed: {e}")
            return {
                'market_regime': 'ranging_low_vol',
                'regime_confidence': 0.5,
                'macro_environment': 'neutral',
                'macro_confidence': 0.5
            }
    
    def _calculate_dynamic_allocation(self, market_conditions: Dict[str, Any], 
                                    portfolio_state: PortfolioState = None) -> Dict[str, float]:
        """Calculate dynamic allocation between strategies"""
        try:
            # Get current performance (placeholder - in real implementation would be actual data)
            active_performance = {'sharpe_ratio': 0.8, 'volatility': 0.2}
            value_performance = {'sharpe_ratio': 0.6, 'volatility': 0.15}
            
            # Calculate optimal allocation
            allocation_result = self.calculate_optimal_allocation(
                market_conditions['market_regime'],
                market_conditions['macro_environment'],
                active_performance,
                value_performance
            )
            
            return {
                'active_trading': allocation_result.active_trading_allocation,
                'value_investing': allocation_result.value_investing_allocation,
                'rebalancing_needed': allocation_result.rebalancing_needed,
                'risk_weights': allocation_result.risk_parity_weights
            }
            
        except Exception as e:
            print(f"Warning: Allocation calculation failed: {e}")
            return {
                'active_trading': self.base_active_allocation,
                'value_investing': self.base_value_allocation,
                'rebalancing_needed': False,
                'risk_weights': {'active_trading': 0.5, 'value_investing': 0.5}
            }
    
    def _generate_symbol_signal(self, 
                               symbol: str, 
                               df: pd.DataFrame, 
                               market_conditions: Dict[str, Any],
                               allocation: Dict[str, float]) -> HybridSignal:
        """Generate hybrid signal for specific symbol"""
        try:
            # Generate active trading signal
            active_signal = self._generate_active_trading_signal(symbol, df)
            
            # Generate value investing signal
            value_signal = self._generate_value_investing_signal(symbol)
            
            # Combine signals with allocation weights
            combined_signal = self._combine_signals(
                active_signal, value_signal, allocation
            )
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                active_signal, value_signal, allocation, market_conditions
            )
            
            # Generate recommendation
            recommendation = self._generate_recommendation(combined_signal, confidence_score)
            
            return HybridSignal(
                symbol=symbol,
                active_trading_signal=active_signal['signal'],
                value_investing_signal=value_signal['signal'],
                combined_signal=combined_signal,
                confidence_score=confidence_score,
                strategy_weights=allocation,
                allocation=allocation,
                recommendation=recommendation
            )
            
        except Exception as e:
            print(f"Warning: Signal generation failed for {symbol}: {e}")
            return self._default_signal(symbol, allocation)
    
    def _generate_active_trading_signal(self, symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate active trading signal using enhanced strategy"""
        try:
            # Apply enhanced strategy
            result_df = self.apply_enhanced_strategy(df, symbol)
            
            # Get latest signal
            if not result_df.empty and 'signal' in result_df.columns:
                latest_signal = result_df['signal'].iloc[-1]
                confidence = result_df['confidence_score'].iloc[-1] if 'confidence_score' in result_df.columns else 0.5
                
                return {
                    'signal': latest_signal,
                    'confidence': confidence,
                    'strategy': 'enhanced_strategy'
                }
            
            return {'signal': 0, 'confidence': 0.5, 'strategy': 'enhanced_strategy'}
            
        except Exception as e:
            print(f"Warning: Active trading signal failed for {symbol}: {e}")
            return {'signal': 0, 'confidence': 0.5, 'strategy': 'enhanced_strategy'}
    
    def _generate_value_investing_signal(self, symbol: str) -> Dict[str, Any]:
        """Generate value investing signal using fundamental analysis"""
        try:
            # Analyze business quality
            quality = self.analyze_business_quality(symbol)
            
            # Convert recommendation to signal
            signal_map = {
                'STRONG_BUY': 1,
                'BUY': 1,
                'HOLD': 0,
                'SELL': -1,
                'STRONG_SELL': -1
            }
            
            signal = signal_map.get(quality.recommendation, 0)
            confidence = quality.overall_score / 100.0
            
            return {
                'signal': signal,
                'confidence': confidence,
                'strategy': 'value_investing',
                'quality_score': quality.overall_score,
                'risk_level': quality.risk_level
            }
            
        except Exception as e:
            print(f"Warning: Value investing signal failed for {symbol}: {e}")
            return {'signal': 0, 'confidence': 0.5, 'strategy': 'value_investing'}
    
    def _combine_signals(self, 
                         active_signal: Dict[str, Any], 
                         value_signal: Dict[str, Any],
                         allocation: Dict[str, float]) -> int:
        """Combine signals using allocation weights"""
        try:
            # Weighted signal combination
            active_weight = allocation['active_trading']
            value_weight = allocation['value_investing']
            
            # Calculate weighted signal
            weighted_signal = (
                active_signal['signal'] * active_weight * active_signal['confidence'] +
                value_signal['signal'] * value_weight * value_signal['confidence']
            )
            
            # Convert to discrete signal
            if weighted_signal > self.confidence_threshold:
                return 1
            elif weighted_signal < -self.confidence_threshold:
                return -1
            else:
                return 0
                
        except:
            return 0
    
    def _calculate_confidence_score(self, 
                                  active_signal: Dict[str, Any], 
                                  value_signal: Dict[str, Any],
                                  allocation: Dict[str, float],
                                  market_conditions: Dict[str, Any]) -> float:
        """Calculate combined confidence score"""
        try:
            # Weighted confidence
            active_weight = allocation['active_trading']
            value_weight = allocation['value_investing']
            
            # Base confidence
            base_confidence = (
                active_signal['confidence'] * active_weight +
                value_signal['confidence'] * value_weight
            )
            
            # Market condition adjustment
            regime_confidence = market_conditions.get('regime_confidence', 0.5)
            macro_confidence = market_conditions.get('macro_confidence', 0.5)
            
            # Final confidence
            final_confidence = (base_confidence * 0.6 + 
                              regime_confidence * 0.2 + 
                              macro_confidence * 0.2)
            
            return max(0.0, min(1.0, final_confidence))
            
        except:
            return 0.5
    
    def _generate_recommendation(self, signal: int, confidence: float) -> str:
        """Generate human-readable recommendation"""
        if confidence < 0.5:
            return 'LOW_CONFIDENCE'
        
        if signal == 1:
            if confidence > 0.8:
                return 'STRONG_BUY'
            else:
                return 'BUY'
        elif signal == -1:
            if confidence > 0.8:
                return 'STRONG_SELL'
            else:
                return 'SELL'
        else:
            return 'HOLD'
    
    def _default_signal(self, symbol: str, allocation: Dict[str, float]) -> HybridSignal:
        """Return default signal when generation fails"""
        return HybridSignal(
            symbol=symbol,
            active_trading_signal=0,
            value_investing_signal=0,
            combined_signal=0,
            confidence_score=0.5,
            strategy_weights=allocation,
            allocation=allocation,
            recommendation='HOLD'
        )
    
    def get_portfolio_summary(self, signals: List[HybridSignal]) -> Dict[str, Any]:
        """Get portfolio summary from signals"""
        try:
            if not signals:
                return {}
            
            # Count signals by type
            buy_signals = sum(1 for s in signals if s.combined_signal == 1)
            sell_signals = sum(1 for s in signals if s.combined_signal == -1)
            hold_signals = sum(1 for s in signals if s.combined_signal == 0)
            
            # Calculate average confidence
            avg_confidence = np.mean([s.confidence_score for s in signals])
            
            # Strategy allocation
            avg_active_weight = np.mean([s.strategy_weights['active_trading'] for s in signals])
            avg_value_weight = np.mean([s.strategy_weights['value_investing'] for s in signals])
            
            # High confidence opportunities
            high_confidence = sum(1 for s in signals if s.confidence_score > 0.8)
            
            return {
                'total_symbols': len(signals),
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'hold_signals': hold_signals,
                'avg_confidence': avg_confidence,
                'active_trading_weight': avg_active_weight,
                'value_investing_weight': avg_value_weight,
                'high_confidence_opportunities': high_confidence,
                'signal_quality': 'HIGH' if avg_confidence > 0.7 else 'MEDIUM' if avg_confidence > 0.5 else 'LOW'
            }
            
        except Exception as e:
            print(f"Warning: Portfolio summary failed: {e}")
            return {}

def generate_hybrid_signals(symbols: List[str],
                          market_data: Dict[str, pd.DataFrame],
                          portfolio_state: PortfolioState = None) -> List[HybridSignal]:
    """
    Convenience function to generate hybrid signals
    """
    strategy = HybridStrategy()
    return strategy.generate_hybrid_signals(symbols, market_data, portfolio_state)

def get_hybrid_portfolio_summary(signals: List[HybridSignal]) -> Dict[str, Any]:
    """
    Convenience function to get portfolio summary
    """
    strategy = HybridStrategy()
    return strategy.get_portfolio_summary(signals)
