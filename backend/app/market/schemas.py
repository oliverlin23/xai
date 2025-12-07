"""Pydantic schemas for market API requests/responses."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum


class OrderSide(str, Enum):
    YES = "yes"
    NO = "no"


class OrderStatus(str, Enum):
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class MarketStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    RESOLVED = "resolved"


# ============ Request Schemas ============

class CreateMarketRequest(BaseModel):
    """Create a new prediction market."""
    question: str = Field(..., min_length=10, max_length=500)
    description: str = Field(default="", max_length=2000)
    session_id: Optional[str] = Field(default=None, description="Link to forecast session")
    closes_at: Optional[datetime] = Field(default=None, description="When market closes for trading")


class CreateOrderRequest(BaseModel):
    """Place a new limit order."""
    market_id: str
    agent_id: str = Field(..., description="ID of the agent placing the order")
    side: OrderSide
    price: int = Field(..., ge=1, le=99, description="Price in cents (1-99)")
    quantity: int = Field(..., ge=1, le=10000, description="Number of contracts")


class CancelOrderRequest(BaseModel):
    """Cancel an existing order."""
    order_id: str
    agent_id: str = Field(..., description="Must match order owner")


class ResolveMarketRequest(BaseModel):
    """Resolve a market with final outcome."""
    outcome: bool = Field(..., description="True = YES wins, False = NO wins")


# ============ Response Schemas ============

class OrderResponse(BaseModel):
    """Order details."""
    id: str
    market_id: str
    agent_id: str
    side: OrderSide
    price: int
    quantity: int
    filled_quantity: int
    remaining_quantity: int
    status: OrderStatus
    created_at: datetime
    updated_at: datetime


class TradeResponse(BaseModel):
    """Trade execution details."""
    id: str
    market_id: str
    buyer_agent_id: str
    seller_agent_id: str
    price: int
    quantity: int
    created_at: datetime


class PositionResponse(BaseModel):
    """Agent's position in a market."""
    agent_id: str
    market_id: str
    yes_quantity: int
    no_quantity: int
    net_position: int
    avg_yes_price: Decimal
    avg_no_price: Decimal
    realized_pnl: Decimal


class OrderBookLevel(BaseModel):
    """Single price level in order book."""
    price: int
    quantity: int
    order_count: int


class OrderBookResponse(BaseModel):
    """Full order book snapshot."""
    market_id: str
    bids: List[OrderBookLevel] = Field(description="YES orders (sorted by price desc)")
    asks: List[OrderBookLevel] = Field(description="NO orders (sorted by price asc)")
    last_price: Optional[int]
    spread: Optional[int] = Field(description="Best ask - best bid")


class MarketResponse(BaseModel):
    """Market details."""
    id: str
    question: str
    description: str
    session_id: Optional[str]
    status: MarketStatus
    resolution: Optional[bool]
    last_price: Optional[int]
    volume: int
    created_at: datetime
    closes_at: Optional[datetime]
    resolved_at: Optional[datetime]


class CreateOrderResponse(BaseModel):
    """Response after placing an order."""
    order: OrderResponse
    trades: List[TradeResponse] = Field(default_factory=list, description="Immediate fills")
    position: PositionResponse


class MarketSummary(BaseModel):
    """Brief market summary for listings."""
    id: str
    question: str
    status: MarketStatus
    last_price: Optional[int]
    volume: int
    best_bid: Optional[int]
    best_ask: Optional[int]

