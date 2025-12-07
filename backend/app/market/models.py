"""
Market models - aligned with Supabase schema (003_create_trading_tables.sql).

Simplified: everyone trades probability of YES (0-100 cents).
- Buy = think probability is higher
- Sell = think probability is lower
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from decimal import Decimal
from enum import Enum
from typing import Optional
import uuid


# Matches DB enum: order_side
class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


# Matches DB enum: order_status
class OrderStatus(str, Enum):
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"


# Valid trader names (matches DB enum: trader_name)
VALID_TRADER_NAMES = {
    # Fundamental traders
    "1", "2", "3", "4", "5",
    # Noise traders (spheres)
    "eacc_sovereign", "america_first", "blue_establishment", "progressive_left",
    "optimizer_idw", "fintwit_market", "builder_engineering", "academic_research", "osint_intel",
}


def validate_trader_name(name: str) -> str:
    """Validate trader name matches DB enum."""
    if name not in VALID_TRADER_NAMES:
        raise ValueError(f"Invalid trader name: {name}. Must be one of {VALID_TRADER_NAMES}")
    return name


@dataclass
class Order:
    """
    A limit order in the order book.
    
    Price is in cents (0-100) representing probability.
    - Buy at 60 = "I'll pay 60 cents, betting probability > 60%"
    - Sell at 60 = "I'll take 60 cents, betting probability < 60%"
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    trader_name: str = ""  # Must be valid trader_name enum value
    side: OrderSide = OrderSide.BUY
    price: int = 50  # 0-100 cents
    quantity: int = 1
    filled_quantity: int = 0
    status: OrderStatus = OrderStatus.OPEN
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self):
        if self.trader_name:
            validate_trader_name(self.trader_name)

    @property
    def remaining_quantity(self) -> int:
        return self.quantity - self.filled_quantity

    @property
    def is_active(self) -> bool:
        return self.status in (OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED)

    def fill(self, qty: int) -> None:
        """Fill some quantity of this order."""
        self.filled_quantity += qty
        if self.filled_quantity >= self.quantity:
            self.status = OrderStatus.FILLED
        elif self.filled_quantity > 0:
            self.status = OrderStatus.PARTIALLY_FILLED

    def cancel(self) -> None:
        """Cancel this order."""
        self.status = OrderStatus.CANCELLED


@dataclass
class Trade:
    """A matched trade between a buyer and seller."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    buyer_name: str = ""
    seller_name: str = ""
    price: int = 0  # Execution price
    quantity: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class TraderState:
    """
    A trader's current state in a session.
    Matches trader_state_live table.
    """
    session_id: str = ""
    name: str = ""
    system_prompt: str = ""
    position: int = 0  # Positive = long, negative = short
    cash: Decimal = Decimal("1000.00")
    pnl: Decimal = Decimal("0")

    def __post_init__(self):
        if self.name:
            validate_trader_name(self.name)
