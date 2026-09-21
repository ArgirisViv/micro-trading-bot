# src/application/dto.py
# Data Transfer Objects (DTOs) for Application Layer

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

from ..domain.value_objects import Money, Percentage, RiskLevel
from ..domain.entities import SignalType, PositionSide, OrderStatus


class TradingAction(Enum):
    """Trading action types"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"


class OrderType(Enum):
    """Order type enumeration"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


@dataclass
class TradingRequest:
    """Request DTO for trading operations"""
    symbol: str
    action: TradingAction
    quantity: Optional[int] = None
    price: Optional[float] = None
    order_type: OrderType = OrderType.MARKET
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_per_trade: Optional[float] = None  # Percentage as decimal (e.g., 0.01 for 1%)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate request data"""
        if not self.symbol or not self.symbol.strip():
            raise ValueError("Symbol cannot be empty")
        
        if self.action in [TradingAction.BUY, TradingAction.SELL] and self.quantity is None:
            raise ValueError("Quantity is required for BUY/SELL actions")
        
        if self.quantity is not None and self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        if self.price is not None and self.price <= 0:
            raise ValueError("Price must be positive")
        
        if self.risk_per_trade is not None and not (0 < self.risk_per_trade <= 1):
            raise ValueError("Risk per trade must be between 0 and 1")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "symbol": self.symbol,
            "action": self.action.value,
            "quantity": self.quantity,
            "price": self.price,
            "order_type": self.order_type.value,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "risk_per_trade": self.risk_per_trade,
            "metadata": self.metadata
        }


@dataclass
class TradingResponse:
    """Response DTO for trading operations"""
    success: bool
    order_id: Optional[str] = None
    message: str = ""
    error_code: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now())
    execution_price: Optional[float] = None
    execution_quantity: Optional[int] = None
    fees: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate response data"""
        if not self.message:
            if self.success:
                self.message = "Operation completed successfully"
            else:
                self.message = "Operation failed"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "success": self.success,
            "order_id": self.order_id,
            "message": self.message,
            "error_code": self.error_code,
            "timestamp": self.timestamp.isoformat(),
            "execution_price": self.execution_price,
            "execution_quantity": self.execution_quantity,
            "fees": self.fees,
            "metadata": self.metadata
        }


@dataclass
class PortfolioUpdate:
    """DTO for portfolio updates"""
    portfolio_id: str
    cash_change: float = 0.0
    positions_added: List[Dict[str, Any]] = field(default_factory=list)
    positions_removed: List[str] = field(default_factory=list)  # Position IDs
    orders_added: List[Dict[str, Any]] = field(default_factory=list)
    orders_updated: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate portfolio update data"""
        if not self.portfolio_id or not self.portfolio_id.strip():
            raise ValueError("Portfolio ID cannot be empty")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "portfolio_id": self.portfolio_id,
            "cash_change": self.cash_change,
            "positions_added": self.positions_added,
            "positions_removed": self.positions_removed,
            "orders_added": self.orders_added,
            "orders_updated": self.orders_updated,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class SignalRequest:
    """Request DTO for signal generation"""
    symbol: str
    timeframe: str = "1h"
    lookback_periods: int = 100
    strategy_parameters: Optional[Dict[str, Any]] = None
    include_indicators: bool = True
    include_ml: bool = False
    include_fundamentals: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate signal request data"""
        if not self.symbol or not self.symbol.strip():
            raise ValueError("Symbol cannot be empty")
        
        if self.lookback_periods <= 0:
            raise ValueError("Lookback periods must be positive")
        
        if self.strategy_parameters is None:
            self.strategy_parameters = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "lookback_periods": self.lookback_periods,
            "strategy_parameters": self.strategy_parameters,
            "include_indicators": self.include_indicators,
            "include_ml": self.include_ml,
            "include_fundamentals": self.include_fundamentals,
            "metadata": self.metadata
        }


@dataclass
class SignalResponse:
    """Response DTO for signal generation"""
    symbol: str
    signals: List[Dict[str, Any]] = field(default_factory=list)
    confidence_score: float = 0.0
    risk_level: str = "medium"
    technical_indicators: Optional[Dict[str, Any]] = None
    ml_predictions: Optional[Dict[str, Any]] = None
    fundamental_analysis: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate signal response data"""
        if not self.symbol or not self.symbol.strip():
            raise ValueError("Symbol cannot be empty")
        
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
        
        if self.technical_indicators is None:
            self.technical_indicators = {}
        
        if self.ml_predictions is None:
            self.ml_predictions = {}
        
        if self.fundamental_analysis is None:
            self.fundamental_analysis = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "symbol": self.symbol,
            "signals": self.signals,
            "confidence_score": self.confidence_score,
            "risk_level": self.risk_level,
            "technical_indicators": self.technical_indicators,
            "ml_predictions": self.ml_predictions,
            "fundamental_analysis": self.fundamental_analysis,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class RiskAssessmentRequest:
    """Request DTO for risk assessment"""
    portfolio_id: str
    include_positions: bool = True
    include_orders: bool = True
    include_historical: bool = False
    risk_metrics: List[str] = field(default_factory=lambda: ["var", "sharpe", "drawdown"])
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate risk assessment request data"""
        if not self.portfolio_id or not self.portfolio_id.strip():
            raise ValueError("Portfolio ID cannot be empty")
        
        valid_metrics = ["var", "sharpe", "drawdown", "volatility", "correlation", "concentration"]
        for metric in self.risk_metrics:
            if metric not in valid_metrics:
                raise ValueError(f"Invalid risk metric: {metric}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "portfolio_id": self.portfolio_id,
            "include_positions": self.include_positions,
            "include_orders": self.include_orders,
            "include_historical": self.include_historical,
            "risk_metrics": self.risk_metrics,
            "metadata": self.metadata
        }


@dataclass
class RiskAssessmentResponse:
    """Response DTO for risk assessment"""
    portfolio_id: str
    overall_risk_level: str = "medium"
    risk_score: float = 0.5
    risk_metrics: Dict[str, Any] = field(default_factory=dict)
    risk_alerts: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate risk assessment response data"""
        if not self.portfolio_id or not self.portfolio_id.strip():
            raise ValueError("Portfolio ID cannot be empty")
        
        if not 0.0 <= self.risk_score <= 1.0:
            raise ValueError("Risk score must be between 0.0 and 1.0")
        
        if self.risk_metrics is None:
            self.risk_metrics = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "portfolio_id": self.portfolio_id,
            "overall_risk_level": self.overall_risk_level,
            "risk_score": self.risk_score,
            "risk_metrics": self.risk_metrics,
            "risk_alerts": self.risk_alerts,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class ConfigurationRequest:
    """Request DTO for configuration operations"""
    action: str  # "get", "set", "delete", "reload"
    key: Optional[str] = None
    value: Optional[Any] = None
    section: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration request data"""
        valid_actions = ["get", "set", "delete", "reload"]
        if self.action not in valid_actions:
            raise ValueError(f"Invalid action: {self.action}")
        
        if self.action in ["get", "set", "delete"] and not self.key:
            raise ValueError("Key is required for get/set/delete actions")
        
        if self.action == "set" and self.value is None:
            raise ValueError("Value is required for set action")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "action": self.action,
            "key": self.key,
            "value": self.value,
            "section": self.section,
            "metadata": self.metadata
        }


@dataclass
class ConfigurationResponse:
    """Response DTO for configuration operations"""
    success: bool
    action: str
    key: Optional[str] = None
    value: Optional[Any] = None
    message: str = ""
    error_code: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration response data"""
        if not self.message:
            if self.success:
                self.message = f"Configuration {self.action} completed successfully"
            else:
                self.message = f"Configuration {self.action} failed"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "success": self.success,
            "action": self.action,
            "key": self.key,
            "value": self.value,
            "message": self.message,
            "error_code": self.error_code,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


# Convenience functions for creating DTOs
def create_trading_request(symbol: str, action: str, **kwargs) -> TradingRequest:
    """Create TradingRequest with validation"""
    try:
        trading_action = TradingAction(action.lower())
    except ValueError:
        raise ValueError(f"Invalid action: {action}. Must be one of {[a.value for a in TradingAction]}")
    
    return TradingRequest(symbol=symbol, action=trading_action, **kwargs)


def create_signal_request(symbol: str, **kwargs) -> SignalRequest:
    """Create SignalRequest with validation"""
    return SignalRequest(symbol=symbol, **kwargs)


def create_risk_assessment_request(portfolio_id: str, **kwargs) -> RiskAssessmentRequest:
    """Create RiskAssessmentRequest with validation"""
    return RiskAssessmentRequest(portfolio_id=portfolio_id, **kwargs)
