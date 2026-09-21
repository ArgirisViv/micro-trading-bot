"""
Advanced Risk Management for Trading Bot Dashboard
Provides comprehensive risk analysis including VaR, Sharpe ratio, correlation matrix, and drawdown analysis
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

@dataclass
class RiskConfig:
    """Risk management configuration"""
    var_confidence: float = 0.95
    max_position_size: float = 0.1  # 10% max per position
    max_portfolio_risk: float = 0.25  # 25% max portfolio risk
    risk_free_rate: float = 0.02  # 2% risk-free rate
    correlation_threshold: float = 0.7  # High correlation threshold

class AdvancedRiskManager:
    """Advanced risk management system for portfolio analysis"""
    
    def __init__(self, config: RiskConfig = None):
        self.config = config or RiskConfig()
        self.portfolio_value = 100000
        self.logger = logging.getLogger(__name__)
        
    def update_portfolio_value(self, value: float):
        """Update current portfolio value"""
        self.portfolio_value = value
        
    def calculate_portfolio_risk(self, positions: Dict) -> Dict:
        """Calculate comprehensive portfolio risk metrics"""
        try:
            if not positions:
                return self._get_default_risk_metrics()
            
            # Calculate position weights
            total_value = sum(pos['value'] for pos in positions.values())
            weights = {symbol: pos['value'] / total_value for symbol, pos in positions.items()}
            
            # Calculate returns matrix
            returns_data = {}
            for symbol, pos in positions.items():
                if 'returns' in pos and len(pos['returns']) > 0:
                    returns_data[symbol] = pos['returns'].dropna()
            
            if not returns_data:
                return self._get_default_risk_metrics()
            
            # Align returns data
            returns_df = pd.DataFrame(returns_data)
            returns_df = returns_df.dropna()
            
            if len(returns_df) < 30:  # Need sufficient data
                return self._get_default_risk_metrics()
            
            # Calculate portfolio metrics
            portfolio_returns = self._calculate_portfolio_returns(returns_df, weights)
            
            # Risk metrics
            volatility = portfolio_returns.std()
            sharpe_ratio = self._calculate_sharpe_ratio(portfolio_returns)
            var_95 = self._calculate_var(portfolio_returns, 0.95)
            var_99 = self._calculate_var(portfolio_returns, 0.99)
            
            # Maximum drawdown
            cumulative_returns = (1 + portfolio_returns).cumprod()
            max_drawdown = self._calculate_max_drawdown(cumulative_returns)
            
            # Position concentration risk
            concentration_risk = max(weights.values()) if weights else 0
            
            return {
                'total_risk': volatility,
                'sharpe_ratio': sharpe_ratio,
                'var_95': var_95,
                'var_99': var_99,
                'max_drawdown': max_drawdown,
                'concentration_risk': concentration_risk,
                'portfolio_returns': portfolio_returns,
                'position_weights': weights
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio risk: {e}")
            return self._get_default_risk_metrics()
    
    def calculate_correlation_matrix(self, positions: Dict) -> pd.DataFrame:
        """Calculate correlation matrix between positions"""
        try:
            if not positions:
                return pd.DataFrame()
            
            # Extract returns data
            returns_data = {}
            for symbol, pos in positions.items():
                if 'returns' in pos and len(pos['returns']) > 0:
                    returns_data[symbol] = pos['returns'].dropna()
            
            if len(returns_data) < 2:
                return pd.DataFrame()
            
            # Create returns DataFrame
            returns_df = pd.DataFrame(returns_data)
            returns_df = returns_df.dropna()
            
            if len(returns_df) < 30:
                return pd.DataFrame()
            
            # Calculate correlation matrix
            correlation_matrix = returns_df.corr()
            
            # Round to 3 decimal places
            correlation_matrix = correlation_matrix.round(3)
            
            return correlation_matrix
            
        except Exception as e:
            self.logger.error(f"Error calculating correlation matrix: {e}")
            return pd.DataFrame()
    
    def calculate_var(self, positions: Dict, confidence: float = None) -> Dict:
        """Calculate Value at Risk (VaR) for portfolio"""
        try:
            if not positions:
                return {'var': 0, 'var_amount': 0}
            
            confidence = confidence or self.config.var_confidence
            
            # Calculate portfolio returns
            total_value = sum(pos['value'] for pos in positions.values())
            weights = {symbol: pos['value'] / total_value for symbol, pos in positions.items()}
            
            returns_data = {}
            for symbol, pos in positions.items():
                if 'returns' in pos and len(pos['returns']) > 0:
                    returns_data[symbol] = pos['returns'].dropna()
            
            if not returns_data:
                return {'var': 0, 'var_amount': 0}
            
            returns_df = pd.DataFrame(returns_data)
            returns_df = returns_df.dropna()
            
            if len(returns_df) < 30:
                return {'var': 0, 'var_amount': 0}
            
            portfolio_returns = self._calculate_portfolio_returns(returns_df, weights)
            
            # Calculate VaR
            var_percentile = np.percentile(portfolio_returns, (1 - confidence) * 100)
            var_amount = abs(var_percentile) * total_value
            
            return {
                'var': abs(var_percentile),
                'var_amount': var_amount,
                'confidence': confidence,
                'portfolio_value': total_value
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating VaR: {e}")
            return {'var': 0, 'var_amount': 0}
    
    def calculate_drawdown(self, equity_curve: pd.Series) -> Dict:
        """Calculate drawdown metrics"""
        try:
            if len(equity_curve) < 2:
                return {}
            
            # Calculate drawdown
            running_max = equity_curve.expanding().max()
            drawdown = (equity_curve - running_max) / running_max
            
            # Current drawdown
            current_drawdown = drawdown.iloc[-1]
            
            # Maximum drawdown
            max_drawdown = drawdown.min()
            
            # Drawdown duration
            max_dd_idx = drawdown.idxmin()
            recovery_idx = drawdown[max_dd_idx:][drawdown[max_dd_idx:] >= 0].index
            
            if len(recovery_idx) > 0:
                recovery_time = (recovery_idx[0] - max_dd_idx).days if hasattr(recovery_idx[0] - max_dd_idx, 'days') else 0
            else:
                recovery_time = 0
            
            return {
                'current_drawdown': current_drawdown,
                'max_drawdown': max_drawdown,
                'max_drawdown_date': max_dd_idx,
                'recovery_time_days': recovery_time,
                'drawdown_series': drawdown
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating drawdown: {e}")
            return {}
    
    def get_risk_summary(self) -> Dict:
        """Get comprehensive risk summary"""
        try:
            # This would typically use current portfolio data
            # For now, return a sample summary
            return {
                'risk_level': 'MEDIUM',
                'overall_risk_score': 0.15,
                'risk_factors': [
                    'Portfolio concentration',
                    'Market volatility',
                    'Correlation risk'
                ],
                'recommendations': [
                    'Diversify positions',
                    'Monitor correlation',
                    'Set stop losses'
                ]
            }
        except Exception as e:
            self.logger.error(f"Error getting risk summary: {e}")
            return {
                'risk_level': 'UNKNOWN',
                'overall_risk_score': 0,
                'risk_factors': [],
                'recommendations': []
            }
    
    def _calculate_portfolio_returns(self, returns_df: pd.DataFrame, weights: Dict) -> pd.Series:
        """Calculate weighted portfolio returns"""
        try:
            # Ensure all symbols have weights
            for symbol in returns_df.columns:
                if symbol not in weights:
                    weights[symbol] = 0
            
            # Calculate weighted returns
            weighted_returns = returns_df * pd.Series(weights)
            portfolio_returns = weighted_returns.sum(axis=1)
            
            return portfolio_returns
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio returns: {e}")
            return pd.Series()
    
    def _calculate_sharpe_ratio(self, returns: pd.Series) -> float:
        """Calculate Sharpe ratio"""
        try:
            if len(returns) < 2:
                return 0
            
            excess_returns = returns - self.config.risk_free_rate / 252  # Daily risk-free rate
            if excess_returns.std() == 0:
                return 0
            
            sharpe = excess_returns.mean() / excess_returns.std()
            return sharpe * np.sqrt(252)  # Annualized
            
        except Exception as e:
            self.logger.error(f"Error calculating Sharpe ratio: {e}")
            return 0
    
    def _calculate_var(self, returns: pd.Series, confidence: float) -> float:
        """Calculate Value at Risk"""
        try:
            if len(returns) < 2:
                return 0
            
            var_percentile = np.percentile(returns, (1 - confidence) * 100)
            return abs(var_percentile)
            
        except Exception as e:
            self.logger.error(f"Error calculating VaR: {e}")
            return 0
    
    def _calculate_max_drawdown(self, equity_curve: pd.Series) -> float:
        """Calculate maximum drawdown"""
        try:
            if len(equity_curve) < 2:
                return 0
            
            running_max = equity_curve.expanding().max()
            drawdown = (equity_curve - running_max) / running_max
            return drawdown.min()
            
        except Exception as e:
            self.logger.error(f"Error calculating max drawdown: {e}")
            return 0
    
    def _get_default_risk_metrics(self) -> Dict:
        """Get default risk metrics when insufficient data"""
        return {
            'total_risk': 0,
            'sharpe_ratio': 0,
            'var_95': 0,
            'var_99': 0,
            'max_drawdown': 0,
            'concentration_risk': 0,
            'portfolio_returns': pd.Series(),
            'position_weights': {}
        }
