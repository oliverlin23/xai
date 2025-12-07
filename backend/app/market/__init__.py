"""Prediction market module - order book and trading."""

from .router import router
from .models import (
    Order, Trade, TraderState, OrderSide, OrderStatus, TraderType,
    VALID_TRADER_NAMES, FUNDAMENTAL_TRADERS, NOISE_TRADERS, USER_TRADERS,
    get_trader_type, validate_trader_name,
)
from .orderbook import OrderBook
from .client import MarketClient, AsyncMarketClient, MarketMaker, SupabaseMarketMaker
from .trading import TradingOrchestrator, TradingConfig, TradeResult

__all__ = [
    "router",
    "Order",
    "Trade",
    "TraderState",
    "OrderSide",
    "OrderStatus",
    "TraderType",
    "VALID_TRADER_NAMES",
    "FUNDAMENTAL_TRADERS",
    "NOISE_TRADERS",
    "USER_TRADERS",
    "get_trader_type",
    "validate_trader_name",
    "OrderBook",
    "MarketClient",
    "AsyncMarketClient",
    "MarketMaker",
    "SupabaseMarketMaker",
    "TradingOrchestrator",
    "TradingConfig",
    "TradeResult",
]
