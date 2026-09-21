# Advanced Risk Management Module
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import warnings

@dataclass
class RiskLimits:
    """Risk management configuration"""
    max_daily_loss: float = 0.05      # 5% max daily loss
    max_position_size: float = 0.1     # 10% max position size
    max_correlation: float = 0.7       # 70% max correlation
    max_drawdown: float = 0.15         # 15% max drawdown
    stop_loss_multiplier: float = 2.0  # 2x ATR for stop loss
    take_profit_multiplier: float = 3.0 # 3x ATR for take profit
    max_leverage: float = 2.0          # Max 2x leverage
    min_risk_reward: float = 1.5       # Min 1.5:1 risk/reward ratio

class PortfolioRiskManager:
    """Advanced portfolio-level risk management"""
    
    def __init__(self, risk_limits: RiskLimits = None):
        self.risk_limits = risk_limits or RiskLimits()
        self.positions = {}
        self.daily_pnl = 0.0
        self.peak_value = 0.0
        self.current_drawdown = 0.0
        self.correlation_matrix = pd.DataFrame()
        
    def calculate_position_size(self, 
                              portfolio_value: float, 
                              price: float, 
                              volatility: float,
                              confidence: float = 0.5) -> int:
        """Calculate optimal position size based on Kelly Criterion and risk limits"""
        
        # Kelly Criterion for position sizing
        win_rate = confidence
        avg_win = self.risk_limits.take_profit_multiplier * volatility
        avg_loss = self.risk_limits.stop_loss_multiplier * volatility
        
        if avg_loss > 0:
            kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
            kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Cap at 25%
        else:
            kelly_fraction = 0.1  # Default 10%
        
        # Apply risk limits
        max_position_value = portfolio_value * self.risk_limits.max_position_size
        kelly_position_value = portfolio_value * kelly_fraction
        
        # Use the more conservative approach
        position_value = min(max_position_value, kelly_position_value)
        
        # Calculate shares
        shares = int(position_value / price)
        
        return max(1, shares)  # Minimum 1 share
    
    def check_correlation_limits(self, 
                                new_symbol: str, 
                                existing_positions: Dict[str, float],
                                price_data: pd.DataFrame) -> bool:
        """Check if new position violates correlation limits"""
        
        if not existing_positions:
            return True
        
        # Calculate correlations
        symbols = list(existing_positions.keys()) + [new_symbol]
        returns = price_data[symbols].pct_change().dropna()
        
        if len(returns) < 30:  # Need minimum data
            return True
        
        correlation_matrix = returns.corr()
        
        # Check if new position correlates too highly with existing
        for symbol in existing_positions:
            if symbol != new_symbol:
                corr = abs(correlation_matrix.loc[new_symbol, symbol])
                if corr > self.risk_limits.max_correlation:
                    return False
        
        return True
    
    def calculate_portfolio_risk(self, 
                               positions: Dict[str, Dict],
                               price_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate comprehensive portfolio risk metrics"""
        
        if not positions:
            return {
                'total_risk': 0.0,
                'var_95': 0.0,
                'expected_shortfall': 0.0,
                'beta': 0.0,
                'sharpe_ratio': 0.0
            }
        
        # Calculate portfolio returns
        portfolio_returns = []
        weights = []
        
        for symbol, pos in positions.items():
            if symbol in price_data.columns:
                returns = price_data[symbol].pct_change().dropna()
                portfolio_returns.append(returns * pos['weight'])
                weights.append(pos['weight'])
        
        if not portfolio_returns:
            return {'total_risk': 0.0}
        
        portfolio_returns = pd.concat(portfolio_returns, axis=1).sum(axis=1)
        
        # Risk metrics
        total_risk = portfolio_returns.std() * np.sqrt(252)  # Annualized
        
        # Value at Risk (95% confidence)
        var_95 = np.percentile(portfolio_returns, 5)
        
        # Expected Shortfall (Conditional VaR)
        expected_shortfall = portfolio_returns[portfolio_returns <= var_95].mean()
        
        # Beta (if market data available)
        beta = 1.0  # Default
        if 'SPY' in price_data.columns:
            market_returns = price_data['SPY'].pct_change().dropna()
            if len(market_returns) > 0 and len(portfolio_returns) > 0:
                min_len = min(len(market_returns), len(portfolio_returns))
                beta = np.cov(portfolio_returns.iloc[-min_len:], 
                             market_returns.iloc[-min_len:])[0,1] / np.var(market_returns.iloc[-min_len:])
        
        # Sharpe Ratio (assuming 0% risk-free rate)
        sharpe_ratio = portfolio_returns.mean() / portfolio_returns.std() if portfolio_returns.std() > 0 else 0
        
        return {
            'total_risk': total_risk,
            'var_95': var_95,
            'expected_shortfall': expected_shortfall,
            'beta': beta,
            'sharpe_ratio': sharpe_ratio
        }
    
    def check_drawdown_limits(self, current_value: float, peak_value: float) -> bool:
        """Check if current drawdown exceeds limits"""
        
        if peak_value == 0:
            return True
        
        current_drawdown = (peak_value - current_value) / peak_value
        
        if current_drawdown > self.risk_limits.max_drawdown:
            return False
        
        return True
    
    def calculate_dynamic_stops(self, 
                               entry_price: float, 
                               atr: float, 
                               direction: str) -> Tuple[float, float]:
        """Calculate dynamic stop loss and take profit levels"""
        
        if direction == 'long':
            stop_loss = entry_price - (self.risk_limits.stop_loss_multiplier * atr)
            take_profit = entry_price + (self.risk_limits.take_profit_multiplier * atr)
        else:  # short
            stop_loss = entry_price + (self.risk_limits.stop_loss_multiplier * atr)
            take_profit = entry_price - (self.risk_limits.take_profit_multiplier * atr)
        
        return stop_loss, take_profit
    
    def update_trailing_stop(self, 
                            current_price: float, 
                            current_stop: float, 
                            atr: float,
                            direction: str) -> float:
        """Update trailing stop based on current price and ATR"""
        
        if direction == 'long':
            new_stop = current_price - (self.risk_limits.stop_loss_multiplier * atr)
            return max(new_stop, current_stop)  # Only move stop up
        else:  # short
            new_stop = current_price + (self.risk_limits.stop_loss_multiplier * atr)
            return min(new_stop, current_stop)  # Only move stop down
    
    def check_portfolio_constraints(self, 
                                  new_position: Dict,
                                  existing_positions: Dict,
                                  portfolio_value: float) -> Tuple[bool, str]:
        """Comprehensive portfolio constraint checking"""
        
        # Check position size limits
        position_value = new_position['shares'] * new_position['price']
        if position_value > portfolio_value * self.risk_limits.max_position_size:
            return False, f"Position size {position_value:.2f} exceeds limit {portfolio_value * self.risk_limits.max_position_size:.2f}"
        
        # Check leverage limits
        total_exposure = sum(pos['shares'] * pos['price'] for pos in existing_positions.values())
        total_exposure += position_value
        
        if total_exposure > portfolio_value * self.risk_limits.max_leverage:
            return False, f"Total exposure {total_exposure:.2f} exceeds leverage limit {portfolio_value * self.risk_limits.max_leverage:.2f}"
        
        # Check daily loss limits
        if self.daily_pnl < -portfolio_value * self.risk_limits.max_daily_loss:
            return False, f"Daily loss limit exceeded: {self.daily_pnl:.2f}"
        
        return True, "All constraints satisfied"
    
    def generate_risk_report(self, 
                            positions: Dict[str, Dict],
                            portfolio_value: float) -> Dict[str, any]:
        """Generate comprehensive risk report"""
        
        risk_metrics = self.calculate_portfolio_risk(positions, pd.DataFrame())
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'portfolio_value': portfolio_value,
            'total_positions': len(positions),
            'risk_metrics': risk_metrics,
            'position_concentration': {},
            'correlation_analysis': {},
            'risk_alerts': []
        }
        
        # Position concentration analysis
        for symbol, pos in positions.items():
            concentration = (pos['shares'] * pos['price']) / portfolio_value
            report['position_concentration'][symbol] = concentration
            
            if concentration > self.risk_limits.max_position_size:
                report['risk_alerts'].append(f"High concentration in {symbol}: {concentration:.2%}")
        
        # Risk alerts
        if risk_metrics['total_risk'] > 0.25:  # 25% annualized volatility
            report['risk_alerts'].append(f"High portfolio volatility: {risk_metrics['total_risk']:.2%}")
        
        if self.current_drawdown > self.risk_limits.max_drawdown * 0.8:  # 80% of limit
            report['risk_alerts'].append(f"Approaching drawdown limit: {self.current_drawdown:.2%}")
        
        return report

class TradeRiskManager:
    """Individual trade risk management"""
    
    def __init__(self, risk_limits: RiskLimits = None):
        self.risk_limits = risk_limits or RiskLimits()
    
    def calculate_risk_reward_ratio(self, 
                                   entry_price: float,
                                   stop_loss: float,
                                   take_profit: float,
                                   direction: str) -> float:
        """Calculate risk/reward ratio for a trade"""
        
        if direction == 'long':
            risk = entry_price - stop_loss
            reward = take_profit - entry_price
        else:  # short
            risk = stop_loss - entry_price
            reward = entry_price - take_profit
        
        if risk <= 0:
            return 0.0
        
        return reward / risk
    
    def validate_trade_setup(self, 
                           entry_price: float,
                           stop_loss: float,
                           take_profit: float,
                           direction: str) -> Tuple[bool, str]:
        """Validate trade setup meets risk requirements"""
        
        # Check risk/reward ratio
        rr_ratio = self.calculate_risk_reward_ratio(entry_price, stop_loss, take_profit, direction)
        
        if rr_ratio < self.risk_limits.min_risk_reward:
            return False, f"Risk/reward ratio {rr_ratio:.2f} below minimum {self.risk_limits.min_risk_reward}"
        
        # Check stop loss distance
        if direction == 'long':
            stop_distance = (entry_price - stop_loss) / entry_price
        else:
            stop_distance = (stop_loss - entry_price) / entry_price
        
        if stop_distance > 0.1:  # Max 10% stop loss
            return False, f"Stop loss distance {stop_distance:.2%} exceeds 10% limit"
        
        return True, "Trade setup valid"
    
    def calculate_position_risk(self, 
                               shares: int,
                               entry_price: float,
                               stop_loss: float) -> float:
        """Calculate absolute risk amount for position"""
        
        risk_per_share = abs(entry_price - stop_loss)
        total_risk = shares * risk_per_share
        
        return total_risk

# Convenience functions
def create_risk_manager(risk_limits: RiskLimits = None) -> PortfolioRiskManager:
    """Create a risk manager with default or custom limits"""
    return PortfolioRiskManager(risk_limits)

def create_trade_risk_manager(risk_limits: RiskLimits = None) -> TradeRiskManager:
    """Create a trade risk manager with default or custom limits"""
    return TradeRiskManager(risk_limits)
