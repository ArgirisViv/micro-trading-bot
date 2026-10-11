# src/domain/value_objects.py
# Value Objects for Domain Layer

from dataclasses import dataclass
from decimal import Decimal
from typing import Union, Optional
from enum import Enum


class RiskLevel(Enum):
    """Risk level enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass(frozen=True)
class Money:
    """Money value object - immutable"""
    amount: Decimal
    
    def __post_init__(self):
        """Validate money amount"""
        if not isinstance(self.amount, (int, float, Decimal)):
            raise ValueError("Amount must be numeric")
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))
    
    def __add__(self, other: 'Money') -> 'Money':
        """Add two money amounts"""
        if not isinstance(other, Money):
            raise TypeError("Can only add Money to Money")
        return Money(self.amount + other.amount)
    
    def __sub__(self, other: 'Money') -> 'Money':
        """Subtract money amounts"""
        if not isinstance(other, Money):
            raise TypeError("Can only subtract Money from Money")
        return Money(self.amount - other.amount)
    
    def __mul__(self, multiplier: Union[int, float, Decimal]) -> 'Money':
        """Multiply money by scalar"""
        if not isinstance(multiplier, (int, float, Decimal)):
            raise TypeError("Multiplier must be numeric")
        return Money(self.amount * Decimal(str(multiplier)))
    
    def __truediv__(self, divisor: Union[int, float, Decimal]) -> 'Money':
        """Divide money by scalar"""
        if not isinstance(divisor, (int, float, Decimal)):
            raise TypeError("Divisor must be numeric")
        decimal_divisor = Decimal(str(divisor))
        if decimal_divisor == 0:
            raise ValueError("Cannot divide by zero")
        return Money(self.amount / decimal_divisor)
    
    def __lt__(self, other: 'Money') -> bool:
        """Less than comparison"""
        if not isinstance(other, Money):
            raise TypeError("Can only compare Money with Money")
        return self.amount < other.amount
    
    def __le__(self, other: 'Money') -> bool:
        """Less than or equal comparison"""
        if not isinstance(other, Money):
            raise TypeError("Can only compare Money with Money")
        return self.amount <= other.amount
    
    def __eq__(self, other: 'Money') -> bool:
        """Equality comparison"""
        if not isinstance(other, Money):
            return False
        return self.amount == other.amount
    
    def __gt__(self, other: 'Money') -> bool:
        """Greater than comparison"""
        if not isinstance(other, Money):
            raise TypeError("Can only compare Money with Money")
        return self.amount > other.amount
    
    def __ge__(self, other: 'Money') -> bool:
        """Greater than or equal comparison"""
        if not isinstance(other, Money):
            raise TypeError("Can only compare Money with Money")
        return self.amount >= other.amount
    
    def __str__(self) -> str:
        """String representation"""
        return f"${self.amount:,.2f}"
    
    def __repr__(self) -> str:
        """Representation for debugging"""
        return f"Money({self.amount})"
    
    @classmethod
    def from_float(cls, amount: float) -> 'Money':
        """Create Money from float"""
        return cls(Decimal(str(amount)))
    
    @classmethod
    def from_int(cls, amount: int) -> 'Money':
        """Create Money from integer"""
        return cls(Decimal(amount))
    
    @classmethod
    def zero(cls) -> 'Money':
        """Create zero Money"""
        return cls(Decimal('0'))
    
    def to_float(self) -> float:
        """Convert to float"""
        return float(self.amount)
    
    def to_int(self) -> int:
        """Convert to integer (rounded)"""
        return int(round(self.amount))


@dataclass(frozen=True)
class Percentage:
    """Percentage value object - immutable"""
    value: Decimal
    
    def __post_init__(self):
        """Validate percentage value"""
        if not isinstance(self.value, (int, float, Decimal)):
            raise ValueError("Value must be numeric")
        if not isinstance(self.value, Decimal):
            object.__setattr__(self, "value", Decimal(str(self.value)))
        if self.value < -100 or self.value > 1000:  # Allow up to 1000% for extreme cases
            raise ValueError("Percentage must be between -100% and 1000%")
    
    def __add__(self, other: 'Percentage') -> 'Percentage':
        """Add two percentages"""
        if not isinstance(other, Percentage):
            raise TypeError("Can only add Percentage to Percentage")
        return Percentage(self.value + other.value)
    
    def __sub__(self, other: 'Percentage') -> 'Percentage':
        """Subtract percentages"""
        if not isinstance(other, Percentage):
            raise TypeError("Can only subtract Percentage from Percentage")
        return Percentage(self.value - other.value)
    
    def __mul__(self, multiplier: Union[int, float, Decimal]) -> 'Percentage':
        """Multiply percentage by scalar"""
        if not isinstance(multiplier, (int, float, Decimal)):
            raise TypeError("Multiplier must be numeric")
        return Percentage(self.value * Decimal(str(multiplier)))
    
    def __truediv__(self, divisor: Union[int, float, Decimal]) -> 'Percentage':
        """Divide percentage by scalar"""
        if not isinstance(divisor, (int, float, Decimal)):
            raise TypeError("Divisor must be numeric")
        decimal_divisor = Decimal(str(divisor))
        if decimal_divisor == 0:
            raise ValueError("Cannot divide by zero")
        return Percentage(self.value / decimal_divisor)
    
    def __lt__(self, other: 'Percentage') -> bool:
        """Less than comparison"""
        if not isinstance(other, Percentage):
            raise TypeError("Can only compare Percentage with Percentage")
        return self.value < other.value
    
    def __le__(self, other: 'Percentage') -> bool:
        """Less than or equal comparison"""
        if not isinstance(other, Percentage):
            raise TypeError("Can only compare Percentage with Percentage")
        return self.value <= other.value
    
    def __eq__(self, other: 'Percentage') -> bool:
        """Equality comparison"""
        if not isinstance(other, Percentage):
            return False
        return self.value == other.value
    
    def __gt__(self, other: 'Percentage') -> bool:
        """Greater than comparison"""
        if not isinstance(other, Percentage):
            raise TypeError("Can only compare Percentage with Percentage")
        return self.value > other.value
    
    def __ge__(self, other: 'Percentage') -> bool:
        """Greater than or equal comparison"""
        if not isinstance(other, Percentage):
            raise TypeError("Can only compare Percentage with Percentage")
        return self.value >= other.value
    
    def __str__(self) -> str:
        """String representation"""
        return f"{self.value:+.2f}%"
    
    def __repr__(self) -> str:
        """Representation for debugging"""
        return f"Percentage({self.value})"
    
    @classmethod
    def from_float(cls, value: float) -> 'Percentage':
        """Create Percentage from float"""
        return cls(Decimal(str(value)))
    
    @classmethod
    def from_int(cls, value: int) -> 'Percentage':
        """Create Percentage from integer"""
        return cls(Decimal(value))
    
    @classmethod
    def zero(cls) -> 'Percentage':
        """Create zero Percentage"""
        return cls(Decimal('0'))
    
    def to_float(self) -> float:
        """Convert to float"""
        return float(self.value)
    
    def to_int(self) -> int:
        """Convert to integer (rounded)"""
        return int(round(self.value))
    
    def is_positive(self) -> bool:
        """Check if percentage is positive"""
        return self.value > 0
    
    def is_negative(self) -> bool:
        """Check if percentage is negative"""
        return self.value < 0
    
    def is_zero(self) -> bool:
        """Check if percentage is zero"""
        return self.value == 0
    
    def to_decimal(self) -> Decimal:
        """Convert to decimal (as fraction, not percentage)"""
        return self.value / Decimal('100')


@dataclass(frozen=True)
class Quantity:
    """Quantity value object - immutable"""
    value: int
    
    def __post_init__(self):
        """Validate quantity value"""
        if not isinstance(self.value, int):
            raise ValueError("Value must be integer")
        if self.value < 0:
            raise ValueError("Quantity cannot be negative")
    
    def __add__(self, other: 'Quantity') -> 'Quantity':
        """Add two quantities"""
        if not isinstance(other, Quantity):
            raise TypeError("Can only add Quantity to Quantity")
        return Quantity(self.value + other.value)
    
    def __sub__(self, other: 'Quantity') -> 'Quantity':
        """Subtract quantities"""
        if not isinstance(other, Quantity):
            raise TypeError("Can only subtract Quantity from Quantity")
        result = self.value - other.value
        if result < 0:
            raise ValueError("Result cannot be negative")
        return Quantity(result)
    
    def __mul__(self, multiplier: int) -> 'Quantity':
        """Multiply quantity by integer"""
        if not isinstance(multiplier, int):
            raise TypeError("Multiplier must be integer")
        if multiplier < 0:
            raise ValueError("Multiplier cannot be negative")
        return Quantity(self.value * multiplier)
    
    def __truediv__(self, divisor: int) -> 'Quantity':
        """Divide quantity by integer"""
        if not isinstance(divisor, int):
            raise TypeError("Divisor must be integer")
        if divisor <= 0:
            raise ValueError("Divisor must be positive")
        return Quantity(self.value // divisor)
    
    def __lt__(self, other: 'Quantity') -> bool:
        """Less than comparison"""
        if not isinstance(other, Quantity):
            raise TypeError("Can only compare Quantity with Quantity")
        return self.value < other.value
    
    def __le__(self, other: 'Quantity') -> bool:
        """Less than or equal comparison"""
        if not isinstance(other, Quantity):
            raise TypeError("Can only compare Quantity with Quantity")
        return self.value <= other.value
    
    def __eq__(self, other: 'Quantity') -> bool:
        """Equality comparison"""
        if not isinstance(other, Quantity):
            return False
        return self.value == other.value
    
    def __gt__(self, other: 'Quantity') -> bool:
        """Greater than comparison"""
        if not isinstance(other, Quantity):
            raise TypeError("Can only compare Quantity with Quantity")
        return self.value > other.value
    
    def __ge__(self, other: 'Quantity') -> bool:
        """Greater than or equal comparison"""
        if not isinstance(other, Quantity):
            raise TypeError("Can only compare Quantity with Quantity")
        return self.value >= other.value
    
    def __str__(self) -> str:
        """String representation"""
        return str(self.value)
    
    def __repr__(self) -> str:
        """Representation for debugging"""
        return f"Quantity({self.value})"
    
    @classmethod
    def from_int(cls, value: int) -> 'Quantity':
        """Create Quantity from integer"""
        return cls(value)
    
    @classmethod
    def zero(cls) -> 'Quantity':
        """Create zero Quantity"""
        return cls(0)
    
    def to_int(self) -> int:
        """Convert to integer"""
        return self.value
    
    def is_zero(self) -> bool:
        """Check if quantity is zero"""
        return self.value == 0
    
    def is_positive(self) -> bool:
        """Check if quantity is positive"""
        return self.value > 0


@dataclass(frozen=True)
class Confidence:
    """Confidence value object - immutable (0.0 to 1.0)"""
    value: Decimal
    
    def __post_init__(self):
        """Validate confidence value"""
        if not isinstance(self.value, (int, float, Decimal)):
            raise ValueError("Value must be numeric")
        if not isinstance(self.value, Decimal):
            object.__setattr__(self, "value", Decimal(str(self.value)))
        if self.value < 0 or self.value > 1:
            raise ValueError("Confidence must be between 0.0 and 1.0")
    
    def __add__(self, other: 'Confidence') -> 'Confidence':
        """Add two confidence values (capped at 1.0)"""
        if not isinstance(other, Confidence):
            raise TypeError("Can only add Confidence to Confidence")
        result = min(self.value + other.value, Decimal('1.0'))
        return Confidence(result)
    
    def __sub__(self, other: 'Confidence') -> 'Confidence':
        """Subtract confidence values (capped at 0.0)"""
        if not isinstance(other, Confidence):
            raise TypeError("Can only subtract Confidence from Confidence")
        result = max(self.value - other.value, Decimal('0.0'))
        return Confidence(result)
    
    def __mul__(self, multiplier: Union[int, float, Decimal]) -> 'Confidence':
        """Multiply confidence by scalar (capped at 1.0)"""
        if not isinstance(multiplier, (int, float, Decimal)):
            raise TypeError("Multiplier must be numeric")
        result = min(self.value * Decimal(str(multiplier)), Decimal('1.0'))
        return Confidence(result)
    
    def __truediv__(self, divisor: Union[int, float, Decimal]) -> 'Confidence':
        """Divide confidence by scalar"""
        if not isinstance(divisor, (int, float, Decimal)):
            raise TypeError("Divisor must be numeric")
        decimal_divisor = Decimal(str(divisor))
        if decimal_divisor == 0:
            raise ValueError("Cannot divide by zero")
        result = self.value / decimal_divisor
        return Confidence(min(result, Decimal('1.0')))
    
    def __lt__(self, other: 'Confidence') -> bool:
        """Less than comparison"""
        if not isinstance(other, Confidence):
            raise TypeError("Can only compare Confidence with Confidence")
        return self.value < other.value
    
    def __le__(self, other: 'Confidence') -> bool:
        """Less than or equal comparison"""
        if not isinstance(other, Confidence):
            raise TypeError("Can only compare Confidence with Confidence")
        return self.value <= other.value
    
    def __eq__(self, other: 'Confidence') -> bool:
        """Equality comparison"""
        if not isinstance(other, Confidence):
            return False
        return self.value == other.value
    
    def __gt__(self, other: 'Confidence') -> bool:
        """Greater than comparison"""
        if not isinstance(other, Confidence):
            raise TypeError("Can only compare Confidence with Confidence")
        return self.value > other.value
    
    def __ge__(self, other: 'Confidence') -> bool:
        """Greater than or equal comparison"""
        if not isinstance(other, Confidence):
            raise TypeError("Can only compare Confidence with Confidence")
        return self.value >= other.value
    
    def __str__(self) -> str:
        """String representation"""
        return f"{float(self.value):.1%}"
    
    def __repr__(self) -> str:
        """Representation for debugging"""
        return f"Confidence({self.value})"
    
    @classmethod
    def from_float(cls, value: float) -> 'Confidence':
        """Create Confidence from float"""
        return cls(Decimal(str(value)))
    
    @classmethod
    def from_percentage(cls, percentage: Union[int, float]) -> 'Confidence':
        """Create Confidence from percentage (e.g., 75 -> 0.75)"""
        if not isinstance(percentage, (int, float)):
            raise ValueError("Percentage must be numeric")
        if percentage < 0 or percentage > 100:
            raise ValueError("Percentage must be between 0 and 100")
        return cls(Decimal(str(percentage / 100)))
    
    @classmethod
    def zero(cls) -> 'Confidence':
        """Create zero Confidence"""
        return cls(Decimal('0'))
    
    @classmethod
    def one(cls) -> 'Confidence':
        """Create full Confidence"""
        return cls(Decimal('1'))
    
    def to_float(self) -> float:
        """Convert to float"""
        return float(self.value)
    
    def to_percentage(self) -> float:
        """Convert to percentage (0-100)"""
        return float(self.value * 100)
    
    def is_zero(self) -> bool:
        """Check if confidence is zero"""
        return self.value == 0
    
    def is_full(self) -> bool:
        """Check if confidence is full (1.0)"""
        return self.value == 1
    
    def is_low(self) -> bool:
        """Check if confidence is low (< 0.3)"""
        return self.value < Decimal('0.3')
    
    def is_medium(self) -> bool:
        """Check if confidence is medium (0.3 - 0.7)"""
        return Decimal('0.3') <= self.value <= Decimal('0.7')
    
    def is_high(self) -> bool:
        """Check if confidence is high (> 0.7)"""
        return self.value > Decimal('0.7')
