# src/domain/entities.py
# Core Domain Entities for Trading Bot

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from decimal import Decimal
from enum import Enum
import uuid

from .value_objects import Money, Percentage, RiskLevel


class SignalType(Enum):
    """Trading signal types"""
    BUY = 1
    SELL = -1
    HOLD = 0


class OrderStatus(Enum):
    """Order status enumeration"""
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    PARTIALLY_FILLED = "partially_filled"


class PositionSide(Enum):
    """Position side enumeration"""
    LONG = "long"
    SHORT = "short"


@dataclass
class TradingSignal:
    """Trading signal entity"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()), init=False)
    symbol: str
    signal_type: SignalType
    confidence: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    price: Optional[Money] = None
    volume: Optional[int] = None
    technical_score: Optional[float] = None
    ml_score: Optional[float] = None
    fundamental_score: Optional[float] = None
    risk_level: RiskLevel = RiskLevel.MEDIUM
    
    def __post_init__(self):
        """Validate entity after initialization"""
        if not self.symbol or not self.symbol.strip():
            raise ValueError("Symbol cannot be empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
    
    @property
    def is_buy(self) -> bool:
        """Check if signal is buy"""
        return self.signal_type == SignalType.BUY
    
    @property
    def is_sell(self) -> bool:
        """Check if signal is sell"""
        return self.signal_type == SignalType.SELL
    
    @property
    def is_hold(self) -> bool:
        """Check if signal is hold"""
        return self.signal_type == SignalType.HOLD
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "signal_type": self.signal_type.value,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "price": float(self.price.amount) if self.price else None,
            "volume": self.volume,
            "technical_score": self.technical_score,
            "ml_score": self.ml_score,
            "fundamental_score": self.fundamental_score,
            "risk_level": self.risk_level.value
        }


@dataclass
class Order:
    """Trading order entity"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()), init=False)
    symbol: str
    side: PositionSide
    quantity: int
    price: Money
    order_type: str = "market"  # market, limit, stop, stop_limit
    status: OrderStatus = OrderStatus.PENDING
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    filled_at: Optional[datetime] = None
    filled_price: Optional[Money] = None
    filled_quantity: Optional[int] = None
    stop_loss: Optional[Money] = None
    take_profit: Optional[Money] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate entity after initialization"""
        if not self.symbol or not self.symbol.strip():
            raise ValueError("Symbol cannot be empty")
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.price.amount <= 0:
            raise ValueError("Price must be positive")
    
    @property
    def is_filled(self) -> bool:
        """Check if order is filled"""
        return self.status == OrderStatus.FILLED
    
    @property
    def is_pending(self) -> bool:
        """Check if order is pending"""
        return self.status == OrderStatus.PENDING
    
    @property
    def is_cancelled(self) -> bool:
        """Check if order is cancelled"""
        return self.status == OrderStatus.CANCELLED
    
    def fill(self, price: Money, quantity: int, timestamp: Optional[datetime] = None):
        """Fill the order"""
        if self.status != OrderStatus.PENDING:
            raise ValueError(f"Cannot fill order with status: {self.status}")
        
        self.status = OrderStatus.FILLED
        self.filled_at = timestamp or datetime.now(timezone.utc)
        self.filled_price = price
        self.filled_quantity = quantity
    
    def cancel(self):
        """Cancel the order"""
        if self.status not in [OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED]:
            raise ValueError(f"Cannot cancel order with status: {self.status}")
        
        self.status = OrderStatus.CANCELLED
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "price": float(self.price.amount),
            "order_type": self.order_type,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "filled_price": float(self.filled_price.amount) if self.filled_price else None,
            "filled_quantity": self.filled_quantity,
            "stop_loss": float(self.stop_loss.amount) if self.stop_loss else None,
            "take_profit": float(self.take_profit.amount) if self.take_profit else None,
            "metadata": self.metadata
        }


@dataclass
class Position:
    """Trading position entity"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()), init=False)
    symbol: str
    side: PositionSide
    quantity: int
    entry_price: Money
    current_price: Money
    entry_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    stop_loss: Optional[Money] = None
    take_profit: Optional[Money] = None
    trailing_stop: Optional[Money] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate entity after initialization"""
        if not self.symbol or not self.symbol.strip():
            raise ValueError("Symbol cannot be empty")
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.entry_price.amount <= 0:
            raise ValueError("Entry price must be positive")
        if self.current_price.amount <= 0:
            raise ValueError("Current price must be positive")
    
    @property
    def market_value(self) -> Money:
        """Calculate current market value"""
        return Money(self.current_price.amount * self.quantity)
    
    @property
    def entry_value(self) -> Money:
        """Calculate entry value"""
        return Money(self.entry_price.amount * self.quantity)
    
    @property
    def unrealized_pnl(self) -> Money:
        """Calculate unrealized P&L"""
        if self.side == PositionSide.LONG:
            return Money((self.current_price.amount - self.entry_price.amount) * self.quantity)
        else:  # SHORT
            return Money((self.entry_price.amount - self.current_price.amount) * self.quantity)
    
    @property
    def unrealized_pnl_percentage(self) -> Percentage:
        """Calculate unrealized P&L percentage"""
        if self.entry_value.amount == 0:
            return Percentage(Decimal("0"))
        
        pnl_pct = (self.unrealized_pnl.amount / self.entry_value.amount) * 100
        return Percentage(Decimal(str(pnl_pct)))
    
    def update_price(self, new_price: Money):
        """Update current price"""
        if new_price.amount <= 0:
            raise ValueError("Price must be positive")
        
        self.current_price = new_price
        self.last_update = datetime.now(timezone.utc)
    
    def set_stop_loss(self, stop_loss: Money):
        """Set stop loss price"""
        if self.side == PositionSide.LONG and stop_loss.amount >= self.current_price.amount:
            raise ValueError("Stop loss for long position must be below current price")
        if self.side == PositionSide.SHORT and stop_loss.amount <= self.current_price.amount:
            raise ValueError("Stop loss for short position must be above current price")
        
        self.stop_loss = stop_loss
    
    def set_take_profit(self, take_profit: Money):
        """Set take profit price"""
        if self.side == PositionSide.LONG and take_profit.amount <= self.current_price.amount:
            raise ValueError("Take profit for long position must be above current price")
        if self.side == PositionSide.SHORT and take_profit.amount >= self.current_price.amount:
            raise ValueError("Take profit for short position must be below current price")
        
        self.take_profit = take_profit
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "entry_price": float(self.entry_price.amount),
            "current_price": float(self.current_price.amount),
            "entry_timestamp": self.entry_timestamp.isoformat(),
            "last_update": self.last_update.isoformat(),
            "stop_loss": float(self.stop_loss.amount) if self.stop_loss else None,
            "take_profit": float(self.take_profit.amount) if self.take_profit else None,
            "trailing_stop": float(self.trailing_stop.amount) if self.trailing_stop else None,
            "market_value": float(self.market_value.amount),
            "entry_value": float(self.entry_value.amount),
            "unrealized_pnl": float(self.unrealized_pnl.amount),
            "unrealized_pnl_percentage": float(self.unrealized_pnl_percentage.value)
        }


@dataclass
class Portfolio:
    """Portfolio entity"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()), init=False)
    name: str
    cash: Money
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    positions: List[Position] = field(default_factory=list)
    orders: List[Order] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate entity after initialization"""
        if not self.name or not self.name.strip():
            raise ValueError("Portfolio name cannot be empty")
        if self.cash.amount < 0:
            raise ValueError("Cash cannot be negative")
    
    @property
    def total_positions_value(self) -> Money:
        """Calculate total value of all positions"""
        return Money(sum((pos.market_value.amount for pos in self.positions), Decimal("0")))
    
    @property
    def total_value(self) -> Money:
        """Calculate total portfolio value"""
        return Money(self.cash.amount + self.total_positions_value.amount)
    
    @property
    def total_unrealized_pnl(self) -> Money:
        """Calculate total unrealized P&L"""
        return Money(sum((pos.unrealized_pnl.amount for pos in self.positions), Decimal("0")))
    
    @property
    def total_unrealized_pnl_percentage(self) -> Percentage:
        """Calculate total unrealized P&L percentage"""
        if self.total_value.amount == 0:
            return Percentage(Decimal("0"))
        
        pnl_pct = (self.total_unrealized_pnl.amount / self.total_value.amount) * 100
        return Percentage(Decimal(str(pnl_pct)))

    @property
    def position_count(self) -> int:
        return len(self.positions)

    @property
    def open_orders_count(self) -> int:
        return sum(order.status in {OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED}
                   for order in self.orders)

    def get_position_by_symbol(self, symbol: str) -> Position | None:
        return next((position for position in self.positions if position.symbol == symbol), None)
    
    def add_position(self, position: Position):
        """Add a new position to the portfolio"""
        if not isinstance(position, Position):
            raise ValueError("Must be a Position entity")
        
        self.positions.append(position)
        self.last_update = datetime.now(timezone.utc)
    
    def remove_position(self, position_id: str):
        """Remove a position from the portfolio"""
        self.positions = [pos for pos in self.positions if pos.id != position_id]
        self.last_update = datetime.now(timezone.utc)
    
    def add_order(self, order: Order):
        """Add a new order to the portfolio"""
        if not isinstance(order, Order):
            raise ValueError("Must be an Order entity")
        
        self.orders.append(order)
        self.last_update = datetime.now(timezone.utc)
    
    def update_cash(self, amount: Money):
        """Update portfolio cash"""
        new_cash = Money(self.cash.amount + amount.amount)
        if new_cash.amount < 0:
            raise ValueError("Insufficient cash")
        
        self.cash = new_cash
        self.last_update = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "id": self.id,
            "name": self.name,
            "cash": float(self.cash.amount),
            "created_at": self.created_at.isoformat(),
            "last_update": self.last_update.isoformat(),
            "total_value": float(self.total_value.amount),
            "total_positions_value": float(self.total_positions_value.amount),
            "total_unrealized_pnl": float(self.total_unrealized_pnl.amount),
            "total_unrealized_pnl_percentage": float(self.total_unrealized_pnl_percentage.value),
            "position_count": len(self.positions),
            "order_count": len(self.orders),
            "metadata": self.metadata
        }
