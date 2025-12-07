"""Pydantic schemas for market API requests/responses."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum

from .models import VALID_TRADER_NAMES, TraderType as ModelTraderType


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"


# ============ Request Schemas ============

class CreateOrderRequest(BaseModel):
    """Place a new limit order."""
    trader_name: str = Field(..., description="Trader identifier (must be valid enum)")
    side: OrderSide
    price: int = Field(..., ge=1, le=99, description="Price in cents (1-99)")
    quantity: int = Field(..., ge=1, le=10000, description="Number of contracts")

    def validate_trader_name(self):
        if self.trader_name not in VALID_TRADER_NAMES:
            raise ValueError(f"Invalid trader_name: {self.trader_name}")


class CancelOrderRequest(BaseModel):
    """Cancel an existing order."""
    order_id: str
    trader_name: str = Field(..., description="Must match order owner")


# ============ Response Schemas ============

class OrderResponse(BaseModel):
    """Order details."""
    id: str
    session_id: str
    trader_name: str
    side: OrderSide
    price: int
    quantity: int
    filled_quantity: int
    remaining_quantity: int
    status: OrderStatus
    created_at: datetime


class TradeResponse(BaseModel):
    """Trade execution details."""
    id: str
    session_id: str
    buyer_name: str
    seller_name: str
    price: int
    quantity: int
    created_at: datetime


class TraderType(str, Enum):
    FUNDAMENTAL = "fundamental"
    NOISE = "noise"
    USER = "user"


class TraderStateResponse(BaseModel):
    """Trader's current state."""
    session_id: str
    trader_type: TraderType
    name: str
    position: int
    cash: Decimal
    pnl: Decimal


class OrderBookLevel(BaseModel):
    """Single price level in order book."""
    price: int
    quantity: int
    order_count: int


class OrderBookResponse(BaseModel):
    """Full order book snapshot."""
    session_id: str
    bids: List[OrderBookLevel] = Field(description="Buy orders (sorted by price desc)")
    asks: List[OrderBookLevel] = Field(description="Sell orders (sorted by price asc)")
    last_price: Optional[int]
    spread: Optional[int] = Field(description="Best ask - best bid")
    volume: int


class CreateOrderResponse(BaseModel):
    """Response after placing an order."""
    order: OrderResponse
    trades: List[TradeResponse] = Field(default_factory=list, description="Immediate fills")
    trader_state: TraderStateResponse
