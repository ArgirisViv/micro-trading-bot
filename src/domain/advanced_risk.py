# src/domain/advanced_risk.py
"""
Advanced Risk Management System
- Kelly Criterion for optimal position sizing
- Value at Risk (VaR) calculation
- Dynamic risk adjustment based on market conditions
- Portfolio heat management
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional, List
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

class AdvancedRiskManager:
    """
    Advanced risk management with Kelly Criterion and VaR
    """
    
    def __init__(self, 
                 max_portfolio_risk: float = 0.02,  # 2% max portfolio risk
                 max_position_risk: float = 0.01,   # 1% max position risk
                 confidence_level: float = 0.95,    # 95% VaR confidence
                 lookback_period: int = 252):       # 1 year of data
        
        self.max_portfolio_risk = max_portfolio_risk
        self.max_position_risk = max_position_risk
        self.confidence_level = confidence_level
        self.lookback_period = lookback_period
        
    def calculate_kelly_criterion(self, 
                                win_rate: float, 
                                avg_win: float, 
                                avg_loss: float) -> float:
        """
        Calculate Kelly Criterion for optimal position sizing
        
        Kelly % = (bp - q) / b
        where:
        - b = net odds received on the bet (= avg_win/avg_loss)
        - p = probability of winning
        - q = probability of losing (1 - p)
        """
        if avg_loss == 0:
            return 0.0
            
        b = avg_win / avg_loss
        q = 1 - win_rate
        
        kelly_pct = (b * win_rate - q) / b
        
        # Cap Kelly at reasonable levels (max 25% of capital)
        return max(0.0, min(0.25, kelly_pct))
    
    def calculate_var(self, 
                     returns: pd.Series, 
                     confidence_level: float = None) -> Dict[str, float]:
        """
        Calculate Value at Risk (VaR) using historical simulation
        
        Returns:
        - var_absolute: Absolute VaR in currency units
        - var_percentage: VaR as percentage of portfolio
        - expected_shortfall: Expected loss beyond VaR
        """
        if confidence_level is None:
            confidence_level = self.confidence_level
            
        if len(returns) < 30:  # Need minimum data
            return {
                'var_absolute': 0.0,
                'var_percentage': 0.0,
                'expected_shortfall': 0.0
            }
        
        # Calculate VaR
        var_percentile = (1 - confidence_level) * 100
        var_percentage = np.percentile(returns, var_percentile)
        
        # Expected Shortfall (Conditional VaR)
        tail_returns = returns[returns <= var_percentage]
        expected_shortfall = tail_returns.mean() if len(tail_returns) > 0 else var_percentage
        
        return {
            'var_absolute': abs(var_percentage),
            'var_percentage': abs(var_percentage),
            'expected_shortfall': abs(expected_shortfall)
        }
    
    def calculate_portfolio_heat(self, 
                               positions: Dict[str, Dict], 
                               current_prices: Dict[str, float],
                               portfolio_value: float) -> Dict[str, float]:
        """
        Calculate portfolio heat (risk concentration)
        
        Returns risk metrics for each position and overall portfolio
        """
        portfolio_heat = {}
        total_risk = 0.0
        
        for symbol, pos_data in positions.items():
            if symbol not in current_prices:
                continue
                
            current_price = current_prices[symbol]
            entry_price = pos_data.get('entry_price', current_price)
            quantity = pos_data.get('quantity', 0)
            
            if quantity == 0:
                continue
            
            # Position value and P&L
            position_value = abs(quantity * current_price)
            pnl = quantity * (current_price - entry_price)
            pnl_pct = pnl / (quantity * entry_price) if entry_price > 0 else 0
            
            # Risk metrics
            position_risk = position_value / portfolio_value
            volatility_risk = abs(pnl_pct) * position_risk
            
            portfolio_heat[symbol] = {
                'position_value': position_value,
                'position_risk': position_risk,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'volatility_risk': volatility_risk
            }
            
            total_risk += volatility_risk
        
        portfolio_heat['total'] = {
            'total_risk': total_risk,
            'concentration_risk': self._calculate_concentration_risk(portfolio_heat),
            'max_position_risk': max([p['position_risk'] for p in portfolio_heat.values() if isinstance(p, dict) and 'position_risk' in p], default=0.0)
        }
        
        return portfolio_heat
    
    def _calculate_concentration_risk(self, portfolio_heat: Dict) -> float:
        """Calculate portfolio concentration risk using Herfindahl index"""
        position_risks = [p['position_risk'] for p in portfolio_heat.values() 
                         if isinstance(p, dict) and 'position_risk' in p]
        
        if not position_risks:
            return 0.0
            
        # Herfindahl-Hirschman Index for concentration
        hhi = sum(risk ** 2 for risk in position_risks)
        return hhi
    
    def calculate_optimal_position_size(self,
                                     symbol: str,
                                     current_price: float,
                                     portfolio_value: float,
                                     volatility: float,
                                     win_rate: float = 0.55,
                                     avg_win_pct: float = 0.02,
                                     avg_loss_pct: float = 0.01,
                                     current_heat: Dict = None) -> Dict[str, float]:
        """
        Calculate optimal position size using multiple risk factors
        
        Returns:
        - kelly_size: Kelly Criterion based size
        - risk_adjusted_size: Risk-adjusted position size
        - max_safe_size: Maximum safe position size
        - recommended_size: Final recommended size
        """
        
        # 1. Kelly Criterion
        kelly_pct = self.calculate_kelly_criterion(win_rate, avg_win_pct, avg_loss_pct)
        kelly_size = portfolio_value * kelly_pct / current_price
        
        # 2. Risk-adjusted sizing based on volatility
        volatility_factor = 1.0 / (1.0 + volatility * 10)  # Higher volatility = smaller position
        risk_adjusted_size = kelly_size * volatility_factor
        
        # 3. Portfolio heat consideration
        heat_factor = 1.0
        if current_heat and 'total' in current_heat:
            total_risk = current_heat['total']['total_risk']
            if total_risk > self.max_portfolio_risk:
                heat_factor = self.max_portfolio_risk / total_risk
            concentration_risk = current_heat['total']['concentration_risk']
            if concentration_risk > 0.5:  # High concentration
                heat_factor *= 0.8
        
        # 4. Maximum safe size
        max_safe_size = portfolio_value * self.max_position_risk / current_price
        
        # 5. Final recommendation
        recommended_size = min(
            risk_adjusted_size * heat_factor,
            max_safe_size,
            kelly_size
        )
        
        return {
            'kelly_size': kelly_size,
            'risk_adjusted_size': risk_adjusted_size,
            'max_safe_size': max_safe_size,
            'recommended_size': max(1, int(recommended_size)),  # Minimum 1 share
            'kelly_pct': kelly_pct,
            'volatility_factor': volatility_factor,
            'heat_factor': heat_factor
        }
    
    def should_reduce_risk(self, 
                          portfolio_heat: Dict,
                          market_volatility: float,
                          recent_losses: int) -> Tuple[bool, str, float]:
        """
        Determine if we should reduce portfolio risk
        
        Returns:
        - should_reduce: Boolean flag
        - reason: Reason for risk reduction
        - reduction_factor: How much to reduce (0.0 to 1.0)
        """
        
        # Check portfolio heat
        if portfolio_heat and 'total' in portfolio_heat:
            total_risk = portfolio_heat['total']['total_risk']
            if total_risk > self.max_portfolio_risk * 1.5:
                return True, "High portfolio risk", 0.5
            
            concentration_risk = portfolio_heat['total']['concentration_risk']
            if concentration_risk > 0.7:
                return True, "High concentration risk", 0.7
        
        # Check market volatility
        if market_volatility > 0.03:  # 3% daily volatility threshold
            return True, "High market volatility", 0.8
        
        # Check recent losses
        if recent_losses >= 3:
            return True, "Recent losses streak", 0.6
        
        return False, "Normal conditions", 1.0
    
    def calculate_stop_loss_level(self,
                                entry_price: float,
                                volatility: float,
                                atr: float = None,
                                risk_tolerance: float = 0.02) -> Dict[str, float]:
        """
        Calculate dynamic stop loss levels
        
        Returns multiple stop loss options:
        - atr_stop: ATR-based stop
        - volatility_stop: Volatility-based stop
        - kelly_stop: Kelly Criterion based stop
        - recommended_stop: Final recommendation
        """
        
        # ATR-based stop
        atr_stop = entry_price - (atr * 2) if atr else entry_price * 0.98
        
        # Volatility-based stop
        volatility_stop = entry_price * (1 - volatility * 2)
        
        # Kelly-based stop (more aggressive for high win rate strategies)
        kelly_stop = entry_price * (1 - risk_tolerance)
        
        # Recommended stop (use the most conservative)
        recommended_stop = max(atr_stop, volatility_stop, kelly_stop)
        
        return {
            'atr_stop': atr_stop,
            'volatility_stop': volatility_stop,
            'kelly_stop': kelly_stop,
            'recommended_stop': recommended_stop,
            'stop_distance_pct': (entry_price - recommended_stop) / entry_price
        }
    
    def get_risk_summary(self, 
                        portfolio_heat: Dict,
                        market_volatility: float,
                        recent_performance: List[float]) -> Dict:
        """
        Get comprehensive risk summary
        
        Returns risk assessment and recommendations
        """
        
        if not portfolio_heat or 'total' not in portfolio_heat:
            return {'risk_level': 'UNKNOWN', 'recommendations': []}
        
        total_risk = portfolio_heat['total']['total_risk']
        concentration_risk = portfolio_heat['total']['concentration_risk']
        
        # Risk level assessment
        if total_risk > self.max_portfolio_risk * 1.5:
            risk_level = 'HIGH'
        elif total_risk > self.max_portfolio_risk:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'
        
        # Generate recommendations
        recommendations = []
        
        if total_risk > self.max_portfolio_risk:
            recommendations.append(f"Reduce portfolio risk from {total_risk:.2%} to {self.max_portfolio_risk:.2%}")
        
        if concentration_risk > 0.5:
            recommendations.append("Diversify portfolio to reduce concentration risk")
        
        if market_volatility > 0.03:
            recommendations.append("Consider reducing position sizes due to high market volatility")
        
        if recent_performance and len(recent_performance) >= 5:
            recent_avg = np.mean(recent_performance[-5:])
            if recent_avg < -0.01:  # Recent losses
                recommendations.append("Consider reducing risk due to recent poor performance")
        
        return {
            'risk_level': risk_level,
            'total_risk': total_risk,
            'concentration_risk': concentration_risk,
            'market_volatility': market_volatility,
            'recommendations': recommendations,
            'max_safe_risk': self.max_portfolio_risk
        }

def calculate_volatility(returns: pd.Series, window: int = 20) -> float:
    """Calculate rolling volatility"""
    if len(returns) < window:
        return 0.0
    return returns.rolling(window=window).std().iloc[-1]

def calculate_win_rate(trades: List[Dict]) -> Tuple[float, float, float]:
    """Calculate win rate and average win/loss from trade history"""
    if not trades:
        return 0.5, 0.02, 0.01
    
    wins = [t for t in trades if t.get('pnl', 0) > 0]
    losses = [t for t in trades if t.get('pnl', 0) < 0]
    
    win_rate = len(wins) / len(trades) if trades else 0.5
    
    avg_win = np.mean([t.get('pnl_pct', 0.02) for t in wins]) if wins else 0.02
    avg_loss = np.mean([abs(t.get('pnl_pct', 0.01)) for t in losses]) if losses else 0.01
    
    return win_rate, avg_win, avg_loss
