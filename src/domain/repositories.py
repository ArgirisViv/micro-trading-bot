# src/domain/repositories.py
# Repository Interfaces for Domain Layer

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from .entities import Order, Position, TradingSignal, Portfolio


class TradingRepository(ABC):
    """Abstract trading repository interface"""

    @abstractmethod
    def get_portfolio(self, portfolio_id: str) -> Optional[Portfolio]:
        """Get a portfolio by ID."""
        pass

    @abstractmethod
    def save_portfolio(self, portfolio: Portfolio) -> bool:
        """Save a portfolio."""
        pass
    
    @abstractmethod
    def save_order(self, order: Order) -> bool:
        """Save order to repository"""
        pass
    
    @abstractmethod
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        pass
    
    @abstractmethod
    def get_orders_by_symbol(self, symbol: str) -> List[Order]:
        """Get all orders for a symbol"""
        pass
    
    @abstractmethod
    def get_open_orders(self) -> List[Order]:
        """Get all open/pending orders"""
        pass
    
    @abstractmethod
    def get_filled_orders(self, start_date: Optional[datetime] = None, 
                         end_date: Optional[datetime] = None) -> List[Order]:
        """Get filled orders within date range"""
        pass
    
    @abstractmethod
    def update_order_status(self, order_id: str, status: str, 
                          filled_price: Optional[float] = None,
                          filled_quantity: Optional[int] = None) -> bool:
        """Update order status"""
        pass
    
    @abstractmethod
    def save_position(self, position: Position) -> bool:
        """Save position to repository"""
        pass
    
    @abstractmethod
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position by symbol"""
        pass
    
    @abstractmethod
    def get_all_positions(self) -> List[Position]:
        """Get all positions"""
        pass
    
    @abstractmethod
    def update_position_price(self, symbol: str, new_price: float) -> bool:
        """Update position current price"""
        pass
    
    @abstractmethod
    def close_position(self, symbol: str) -> bool:
        """Close position (remove from repository)"""
        pass
    
    @abstractmethod
    def get_position_history(self, symbol: str, 
                           start_date: Optional[datetime] = None,
                           end_date: Optional[datetime] = None) -> List[Position]:
        """Get position history for symbol"""
        pass


class DataRepository(ABC):
    """Abstract data repository interface"""
    
    @abstractmethod
    def save_market_data(self, symbol: str, data: Any, 
                        timestamp: Optional[datetime] = None) -> bool:
        """Save market data for symbol"""
        pass
    
    @abstractmethod
    def get_market_data(self, symbol: str, 
                       start_date: Optional[datetime] = None,
                       end_date: Optional[datetime] = None,
                       limit: Optional[int] = None) -> Optional[Any]:
        """Get market data for symbol"""
        pass
    
    @abstractmethod
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get latest price for symbol"""
        pass
    
    @abstractmethod
    def get_symbols(self) -> List[str]:
        """Get all available symbols"""
        pass
    
    @abstractmethod
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get symbol information"""
        pass
    
    @abstractmethod
    def save_technical_indicators(self, symbol: str, indicators: Dict[str, Any],
                                timestamp: Optional[datetime] = None) -> bool:
        """Save technical indicators for symbol"""
        pass
    
    @abstractmethod
    def get_technical_indicators(self, symbol: str,
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """Get technical indicators for symbol"""
        pass


class NotificationRepository(ABC):
    """Abstract notification repository interface"""
    
    @abstractmethod
    def save_notification(self, notification: Dict[str, Any]) -> bool:
        """Save notification to repository"""
        pass
    
    @abstractmethod
    def get_notifications(self, limit: int = 100, 
                         notification_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent notifications"""
        pass
    
    @abstractmethod
    def mark_as_read(self, notification_id: str) -> bool:
        """Mark notification as read"""
        pass
    
    @abstractmethod
    def get_unread_count(self) -> int:
        """Get count of unread notifications"""
        pass
    
    @abstractmethod
    def delete_notification(self, notification_id: str) -> bool:
        """Delete notification"""
        pass


class ConfigurationRepository(ABC):
    """Abstract configuration repository interface"""
    
    @abstractmethod
    def save_configuration(self, key: str, value: Any) -> bool:
        """Save configuration value"""
        pass
    
    @abstractmethod
    def get_configuration(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        pass
    
    @abstractmethod
    def get_all_configurations(self) -> Dict[str, Any]:
        """Get all configuration values"""
        pass
    
    @abstractmethod
    def delete_configuration(self, key: str) -> bool:
        """Delete configuration value"""
        pass
    
    @abstractmethod
    def has_configuration(self, key: str) -> bool:
        """Check if configuration exists"""
        pass
    
    @abstractmethod
    def get_configuration_keys(self) -> List[str]:
        """Get all configuration keys"""
        pass


class PerformanceRepository(ABC):
    """Abstract performance repository interface"""
    
    @abstractmethod
    def save_performance_metric(self, metric_name: str, value: float,
                              timestamp: Optional[datetime] = None,
                              metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Save performance metric"""
        pass
    
    @abstractmethod
    def get_performance_metrics(self, metric_name: str,
                              start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None,
                              limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get performance metrics"""
        pass
    
    @abstractmethod
    def get_latest_metric(self, metric_name: str) -> Optional[Dict[str, Any]]:
        """Get latest value for metric"""
        pass
    
    @abstractmethod
    def get_metric_names(self) -> List[str]:
        """Get all available metric names"""
        pass
    
    @abstractmethod
    def calculate_average(self, metric_name: str,
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None) -> Optional[float]:
        """Calculate average for metric"""
        pass
    
    @abstractmethod
    def calculate_sum(self, metric_name: str,
                     start_date: Optional[datetime] = None,
                     end_date: Optional[datetime] = None) -> Optional[float]:
        """Calculate sum for metric"""
        pass
    
    @abstractmethod
    def get_metric_statistics(self, metric_name: str,
                            start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None) -> Optional[Dict[str, float]]:
        """Get statistical summary for metric"""
        pass


class PortfolioRepository(ABC):
    """Abstract portfolio repository interface"""
    
    @abstractmethod
    def save_portfolio(self, portfolio: Portfolio) -> bool:
        """Save portfolio to repository"""
        pass
    
    @abstractmethod
    def get_portfolio(self, portfolio_id: str) -> Optional[Portfolio]:
        """Get portfolio by ID"""
        pass
    
    @abstractmethod
    def get_portfolio_by_name(self, name: str) -> Optional[Portfolio]:
        """Get portfolio by name"""
        pass
    
    @abstractmethod
    def get_all_portfolios(self) -> List[Portfolio]:
        """Get all portfolios"""
        pass
    
    @abstractmethod
    def update_portfolio_cash(self, portfolio_id: str, new_cash: float) -> bool:
        """Update portfolio cash balance"""
        pass
    
    @abstractmethod
    def add_portfolio_position(self, portfolio_id: str, position: Position) -> bool:
        """Add position to portfolio"""
        pass
    
    @abstractmethod
    def remove_portfolio_position(self, portfolio_id: str, symbol: str) -> bool:
        """Remove position from portfolio"""
        pass
    
    @abstractmethod
    def add_portfolio_order(self, portfolio_id: str, order: Order) -> bool:
        """Add order to portfolio"""
        pass
    
    @abstractmethod
    def get_portfolio_positions(self, portfolio_id: str) -> List[Position]:
        """Get all positions for portfolio"""
        pass
    
    @abstractmethod
    def get_portfolio_orders(self, portfolio_id: str) -> List[Order]:
        """Get all orders for portfolio"""
        pass
    
    @abstractmethod
    def delete_portfolio(self, portfolio_id: str) -> bool:
        """Delete portfolio"""
        pass


class StrategyRepository(ABC):
    """Abstract strategy repository interface"""
    
    @abstractmethod
    def save_strategy(self, strategy: Dict[str, Any]) -> bool:
        """Save trading strategy"""
        pass
    
    @abstractmethod
    def get_strategy(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """Get strategy by ID"""
        pass
    
    @abstractmethod
    def get_all_strategies(self) -> List[Dict[str, Any]]:
        """Get all strategies"""
        pass
    
    @abstractmethod
    def update_strategy(self, strategy_id: str, updates: Dict[str, Any]) -> bool:
        """Update strategy"""
        pass
    
    @abstractmethod
    def delete_strategy(self, strategy_id: str) -> bool:
        """Delete strategy"""
        pass
    
    @abstractmethod
    def get_active_strategies(self) -> List[Dict[str, Any]]:
        """Get all active strategies"""
        pass
    
    @abstractmethod
    def save_strategy_performance(self, strategy_id: str, performance: Dict[str, Any]) -> bool:
        """Save strategy performance metrics"""
        pass
    
    @abstractmethod
    def get_strategy_performance(self, strategy_id: str,
                               start_date: Optional[datetime] = None,
                               end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get strategy performance history"""
        pass


class RiskRepository(ABC):
    """Abstract risk repository interface"""
    
    @abstractmethod
    def save_risk_assessment(self, assessment: Dict[str, Any]) -> bool:
        """Save risk assessment"""
        pass
    
    @abstractmethod
    def get_latest_risk_assessment(self, portfolio_id: str) -> Optional[Dict[str, Any]]:
        """Get latest risk assessment for portfolio"""
        pass
    
    @abstractmethod
    def get_risk_history(self, portfolio_id: str,
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get risk assessment history"""
        pass
    
    @abstractmethod
    def save_risk_alert(self, alert: Dict[str, Any]) -> bool:
        """Save risk alert"""
        pass
    
    @abstractmethod
    def get_active_risk_alerts(self, portfolio_id: str) -> List[Dict[str, Any]]:
        """Get active risk alerts for portfolio"""
        pass
    
    @abstractmethod
    def mark_alert_resolved(self, alert_id: str) -> bool:
        """Mark risk alert as resolved"""
        pass
    
    @abstractmethod
    def get_risk_metrics(self, portfolio_id: str,
                        metric_names: Optional[List[str]] = None) -> Dict[str, float]:
        """Get current risk metrics for portfolio"""
        pass
