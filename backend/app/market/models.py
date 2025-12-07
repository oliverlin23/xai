"""
Market models - in-memory for now, can be persisted to DB later.

Inspired by Kalshi/Polymarket but simplified for agent trading.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from decimal import Decimal
from enum import Enum
from typing import Optional
import uuid


class OrderSide(str, Enum):
    """Order side - YES means betting the event happens, NO means against."""
    YES = "yes"
    NO = "no"


class OrderStatus(str, Enum):
    """Order lifecycle status."""
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class MarketStatus(str, Enum):
    """Market lifecycle status."""
    OPEN = "open"
    CLOSED = "closed"
    RESOLVED = "resolved"


@dataclass
class Order:
    """
    A limit order in the order book.
    
    Price is in cents (0-100) representing probability.
    - YES at 60 means "I'll pay 60 cents to win $1 if event happens"
    - NO at 60 means "I'll pay 60 cents to win $1 if event doesn't happen"
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    market_id: str = ""
    agent_id: str = ""  # Which agent placed this order
    side: OrderSide = OrderSide.YES
    price: int = 50  # 0-100 cents
    quantity: int = 1  # Number of contracts
    filled_quantity: int = 0
    status: OrderStatus = OrderStatus.OPEN
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def remaining_quantity(self) -> int:
        return self.quantity - self.filled_quantity

    @property
    def is_active(self) -> bool:
        return self.status in (OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED)

    def fill(self, qty: int) -> None:
        """Fill some quantity of this order."""
        self.filled_quantity += qty
        self.updated_at = datetime.now(UTC)
        if self.filled_quantity >= self.quantity:
            self.status = OrderStatus.FILLED
        elif self.filled_quantity > 0:
            self.status = OrderStatus.PARTIALLY_FILLED

    def cancel(self) -> None:
        """Cancel this order."""
        self.status = OrderStatus.CANCELLED
        self.updated_at = datetime.now(UTC)


@dataclass
class Trade:
    """A matched trade between two orders."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    market_id: str = ""
    buy_order_id: str = ""
    sell_order_id: str = ""
    buyer_agent_id: str = ""
    seller_agent_id: str = ""
    price: int = 0  # Execution price
    quantity: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Position:
    """An agent's position in a market."""
    agent_id: str = ""
    market_id: str = ""
    yes_quantity: int = 0  # Contracts betting YES
    no_quantity: int = 0   # Contracts betting NO
    avg_yes_price: Decimal = Decimal("0")
    avg_no_price: Decimal = Decimal("0")
    realized_pnl: Decimal = Decimal("0")

    @property
    def net_position(self) -> int:
        """Positive = net long YES, negative = net long NO."""
        return self.yes_quantity - self.no_quantity


@dataclass
class Market:
    """
    A prediction market for a binary question.
    
    Settlement: If event happens, YES pays $1, NO pays $0.
                If event doesn't happen, YES pays $0, NO pays $1.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    question: str = ""
    description: str = ""
    session_id: Optional[str] = None  # Link to forecast session
    status: MarketStatus = MarketStatus.OPEN
    resolution: Optional[bool] = None  # True = YES wins, False = NO wins
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    closes_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    # Cached market stats
    last_price: Optional[int] = None
    volume: int = 0  # Total contracts traded

    def resolve(self, outcome: bool) -> None:
        """Resolve the market with final outcome."""
        self.resolution = outcome
        self.status = MarketStatus.RESOLVED
        self.resolved_at = datetime.now(UTC)

    def close(self) -> None:
        """Close the market for new orders."""
        self.status = MarketStatus.CLOSED

