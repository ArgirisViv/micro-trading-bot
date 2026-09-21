# core/portfolio_allocator.py
"""
Portfolio Allocation Engine - Hybrid Strategy
Dynamic allocation between Active Trading (70%) and Value Investing (30%)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

@dataclass
class PortfolioAllocation:
    """Portfolio allocation strategy"""
    active_trading_allocation: float  # 0.0 - 1.0
    value_investing_allocation: float  # 0.0 - 1.0
    risk_parity_weights: Dict[str, float]
    rebalancing_needed: bool
    target_allocation: Dict[str, float]
    current_allocation: Dict[str, float]

@dataclass
class StrategyPerformance:
    """Strategy performance metrics"""
    active_trading_return: float
    value_investing_return: float
    combined_return: float
    active_trading_volatility: float
    value_investing_volatility: float
    combined_volatility: float
    sharpe_ratio: float
    max_drawdown: float

class PortfolioAllocator:
    """
    Dynamic portfolio allocation between active trading and value investing
    """
    
    def __init__(self, 
                 base_active_allocation: float = 0.7,
                 base_value_allocation: float = 0.3,
                 rebalancing_threshold: float = 0.05,
                 risk_free_rate: float = 0.02):
        self.base_active_allocation = base_active_allocation
        self.base_value_allocation = base_value_allocation
        self.rebalancing_threshold = rebalancing_threshold
        self.risk_free_rate = risk_free_rate
        self.performance_history = []
        
    def calculate_optimal_allocation(self, 
                                   market_regime: str,
                                   macro_environment: str,
                                   active_performance: Dict,
                                   value_performance: Dict) -> PortfolioAllocation:
        """
        Calculate optimal portfolio allocation based on current conditions
        """
        try:
            # Base allocation
            target_active = self.base_active_allocation
            target_value = self.base_value_allocation
            
            # Market regime adjustments
            regime_adjustments = self._get_regime_adjustments(market_regime)
            target_active *= regime_adjustments['active_multiplier']
            target_value *= regime_adjustments['value_multiplier']
            
            # Macro environment adjustments
            macro_adjustments = self._get_macro_adjustments(macro_environment)
            target_active *= macro_adjustments['active_multiplier']
            target_value *= macro_adjustments['value_multiplier']
            
            # Performance-based adjustments
            perf_adjustments = self._get_performance_adjustments(active_performance, value_performance)
            target_active *= perf_adjustments['active_multiplier']
            target_value *= perf_adjustments['value_multiplier']
            
            # Normalize allocations
            total = target_active + target_value
            target_active /= total
            target_value /= total
            
            # Calculate risk parity weights
            risk_weights = self._calculate_risk_parity_weights(active_performance, value_performance)
            
            # Check if rebalancing is needed
            current_allocation = self._get_current_allocation()
            rebalancing_needed = self._check_rebalancing_needed(
                target_active, target_value, current_allocation
            )
            
            return PortfolioAllocation(
                active_trading_allocation=target_active,
                value_investing_allocation=target_value,
                risk_parity_weights=risk_weights,
                rebalancing_needed=rebalancing_needed,
                target_allocation={'active': target_active, 'value': target_value},
                current_allocation=current_allocation
            )
            
        except Exception as e:
            print(f"Warning: Allocation calculation failed: {e}")
            return self._default_allocation()
    
    def _get_regime_adjustments(self, market_regime: str) -> Dict[str, float]:
        """Get allocation adjustments based on market regime"""
        adjustments = {
            'trending_bull': {'active_multiplier': 1.2, 'value_multiplier': 0.8},
            'trending_bear': {'active_multiplier': 0.8, 'value_multiplier': 1.2},
            'ranging_high_vol': {'active_multiplier': 0.9, 'value_multiplier': 1.1},
            'ranging_low_vol': {'active_multiplier': 1.0, 'value_multiplier': 1.0},
            'volatile_breakout': {'active_multiplier': 1.1, 'value_multiplier': 0.9}
        }
        
        return adjustments.get(market_regime, {'active_multiplier': 1.0, 'value_multiplier': 1.0})
    
    def _get_macro_adjustments(self, macro_environment: str) -> Dict[str, float]:
        """Get allocation adjustments based on macro environment"""
        adjustments = {
            'expansion': {'active_multiplier': 1.1, 'value_multiplier': 0.9},
            'contraction': {'active_multiplier': 0.9, 'value_multiplier': 1.1},
            'peak': {'active_multiplier': 1.0, 'value_multiplier': 1.0},
            'trough': {'active_multiplier': 0.8, 'value_multiplier': 1.2},
            'neutral': {'active_multiplier': 1.0, 'value_multiplier': 1.0}
        }
        
        return adjustments.get(macro_environment, {'active_multiplier': 1.0, 'value_multiplier': 1.0})
    
    def _get_performance_adjustments(self, 
                                   active_performance: Dict, 
                                   value_performance: Dict) -> Dict[str, float]:
        """Get allocation adjustments based on recent performance"""
        try:
            # Calculate performance ratios
            active_sharpe = active_performance.get('sharpe_ratio', 0)
            value_sharpe = value_performance.get('sharpe_ratio', 0)
            
            # Normalize to 0-1 range
            active_sharpe_norm = max(0, min(1, (active_sharpe + 1) / 2))
            value_sharpe_norm = max(0, min(1, (value_sharpe + 1) / 2))
            
            # Calculate performance multipliers
            active_multiplier = 0.8 + (active_sharpe_norm * 0.4)  # 0.8 - 1.2
            value_multiplier = 0.8 + (value_sharpe_norm * 0.4)   # 0.8 - 1.2
            
            return {
                'active_multiplier': active_multiplier,
                'value_multiplier': value_multiplier
            }
            
        except:
            return {'active_multiplier': 1.0, 'value_multiplier': 1.0}
    
    def _calculate_risk_parity_weights(self, 
                                     active_performance: Dict, 
                                     value_performance: Dict) -> Dict[str, float]:
        """Calculate risk parity weights for optimal risk distribution"""
        try:
            # Get volatility estimates
            active_vol = active_performance.get('volatility', 0.2)
            value_vol = value_performance.get('volatility', 0.15)
            
            # Risk parity: equal risk contribution
            if active_vol > 0 and value_vol > 0:
                # Calculate weights that equalize risk contribution
                total_risk = active_vol + value_vol
                active_weight = value_vol / total_risk
                value_weight = active_vol / total_risk
            else:
                # Default to equal weights if volatility data missing
                active_weight = 0.5
                value_weight = 0.5
            
            return {
                'active_trading': active_weight,
                'value_investing': value_weight
            }
            
        except:
            return {'active_trading': 0.5, 'value_investing': 0.5}
    
    def _get_current_allocation(self) -> Dict[str, float]:
        """Get current portfolio allocation (placeholder)"""
        # In real implementation, this would read from portfolio state
        return {'active': 0.7, 'value': 0.3}
    
    def _check_rebalancing_needed(self, 
                                 target_active: float, 
                                 target_value: float, 
                                 current_allocation: Dict[str, float]) -> bool:
        """Check if rebalancing is needed"""
        try:
            current_active = current_allocation.get('active', 0.7)
            current_value = current_allocation.get('value', 0.3)
            
            # Check if deviation exceeds threshold
            active_deviation = abs(target_active - current_active)
            value_deviation = abs(target_value - current_value)
            
            return (active_deviation > self.rebalancing_threshold or 
                   value_deviation > self.rebalancing_threshold)
            
        except:
            return False
    
    def _default_allocation(self) -> PortfolioAllocation:
        """Return default allocation when calculation fails"""
        return PortfolioAllocation(
            active_trading_allocation=self.base_active_allocation,
            value_investing_allocation=self.base_value_allocation,
            risk_parity_weights={'active_trading': 0.5, 'value_investing': 0.5},
            rebalancing_needed=False,
            target_allocation={'active': self.base_active_allocation, 'value': self.base_value_allocation},
            current_allocation={'active': self.base_active_allocation, 'value': self.base_value_allocation}
        )
    
    def calculate_strategy_performance(self, 
                                    active_returns: List[float],
                                    value_returns: List[float]) -> StrategyPerformance:
        """Calculate combined strategy performance metrics"""
        try:
            if not active_returns or not value_returns:
                return self._default_strategy_performance()
            
            # Calculate individual strategy metrics
            active_return = np.mean(active_returns)
            value_return = np.mean(value_returns)
            
            active_vol = np.std(active_returns)
            value_vol = np.std(value_returns)
            
            # Calculate combined metrics
            combined_return = (active_return * self.base_active_allocation + 
                             value_return * self.base_value_allocation)
            
            # Combined volatility (simplified)
            combined_vol = np.sqrt(
                (self.base_active_allocation ** 2) * (active_vol ** 2) +
                (self.base_value_allocation ** 2) * (value_vol ** 2)
            )
            
            # Sharpe ratio
            sharpe_ratio = (combined_return - self.risk_free_rate) / combined_vol if combined_vol > 0 else 0
            
            # Max drawdown (simplified)
            cumulative_returns = np.cumprod([1 + r for r in active_returns + value_returns])
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdown = (cumulative_returns - running_max) / running_max
            max_drawdown = np.min(drawdown)
            
            return StrategyPerformance(
                active_trading_return=active_return,
                value_investing_return=value_return,
                combined_return=combined_return,
                active_trading_volatility=active_vol,
                value_investing_volatility=value_vol,
                combined_volatility=combined_vol,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown
            )
            
        except Exception as e:
            print(f"Warning: Performance calculation failed: {e}")
            return self._default_strategy_performance()
    
    def _default_strategy_performance(self) -> StrategyPerformance:
        """Return default performance metrics when calculation fails"""
        return StrategyPerformance(
            active_trading_return=0.0,
            value_investing_return=0.0,
            combined_return=0.0,
            active_trading_volatility=0.2,
            value_investing_volatility=0.15,
            combined_volatility=0.18,
            sharpe_ratio=0.0,
            max_drawdown=0.0
        )
    
    def get_rebalancing_instructions(self, allocation: PortfolioAllocation) -> Dict[str, Any]:
        """Get specific rebalancing instructions"""
        if not allocation.rebalancing_needed:
            return {'action': 'HOLD', 'reason': 'Allocation within acceptable range'}
        
        try:
            current = allocation.current_allocation
            target = allocation.target_allocation
            
            # Calculate required changes
            active_change = target['active'] - current['active']
            value_change = target['value'] - current['value']
            
            instructions = {
                'action': 'REBALANCE',
                'reason': 'Allocation deviation exceeds threshold',
                'changes': {
                    'active_trading': {
                        'current': current['active'],
                        'target': target['active'],
                        'change': active_change,
                        'action': 'BUY' if active_change > 0 else 'SELL'
                    },
                    'value_investing': {
                        'current': current['value'],
                        'target': target['value'],
                        'change': value_change,
                        'action': 'BUY' if value_change > 0 else 'SELL'
                    }
                },
                'risk_weights': allocation.risk_parity_weights
            }
            
            return instructions
            
        except Exception as e:
            return {'action': 'ERROR', 'reason': f'Calculation failed: {e}'}

def calculate_optimal_allocation(market_regime: str,
                               macro_environment: str,
                               active_performance: Dict,
                               value_performance: Dict) -> PortfolioAllocation:
    """
    Convenience function to calculate optimal allocation
    """
    allocator = PortfolioAllocator()
    return allocator.calculate_optimal_allocation(
        market_regime, macro_environment, active_performance, value_performance
    )

def get_rebalancing_instructions(allocation: PortfolioAllocation) -> Dict[str, Any]:
    """
    Convenience function to get rebalancing instructions
    """
    allocator = PortfolioAllocator()
    return allocator.get_rebalancing_instructions(allocation)
