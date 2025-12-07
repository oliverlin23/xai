"""
Deterministic trading layer - converts agent beliefs to market orders.

This is pure plumbing with no intelligence:
1. Takes agent confidence/belief
2. Deterministically converts to trade parameters
3. Executes via MarketClient
4. Returns result

All logic is explicit and predictable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple
from decimal import Decimal

from .client import MarketClient


@dataclass
class TradeResult:
    """Result of a trade execution."""
    success: bool
    order_id: Optional[str] = None
    side: Optional[str] = None
    price: Optional[int] = None
    quantity: Optional[int] = None
    filled_quantity: int = 0
    trades_count: int = 0
    error: Optional[str] = None


@dataclass
class TradingConfig:
    """Configuration for trading behavior."""
    # Default quantity per trade
    default_quantity: int = 10
    
    # Minimum edge required to trade (confidence - market price)
    # Keep low (1-2%) so agents actually trade
    min_edge: int = 2
    
    # Price adjustment from confidence (how aggressive)
    # 0 = place at exactly your confidence
    # positive = more aggressive (cross spread)
    price_aggression: int = 0
    
    # Maximum position size per trader
    max_position: int = 100


class TradingOrchestrator:
    """
    Deterministic layer between agents and market.
    
    Takes agent beliefs, converts to orders, executes.
    No intelligence - just plumbing.
    """

    def __init__(
        self,
        client: Optional[MarketClient] = None,
        config: Optional[TradingConfig] = None,
    ):
        self.client = client or MarketClient()
        self.config = config or TradingConfig()

    def confidence_to_trade(
        self,
        confidence: float,
        market_price: Optional[float],
    ) -> Tuple[Optional[str], Optional[int]]:
        """
        Deterministically convert confidence to trade side and price.
        
        Args:
            confidence: Agent's belief (0.0 to 1.0)
            market_price: Current market mid price (0-100), or None if no market
        
        Returns:
            (side, price) or (None, None) if no trade
        
        Logic:
            - confidence > market_price + min_edge: buy at (confidence*100 - aggression)
            - confidence < market_price - min_edge: sell at (confidence*100 + aggression)
            - otherwise: no trade (not enough edge)
        """
        conf_price = int(confidence * 100)
        
        # Clamp to valid range
        conf_price = max(1, min(99, conf_price))
        
        if market_price is None:
            # No market yet - place order at confidence
            if confidence >= 0.5:
                return ("buy", conf_price - self.config.price_aggression)
            else:
                return ("sell", conf_price + self.config.price_aggression)
        
        edge = conf_price - market_price
        
        if edge >= self.config.min_edge:
            # Agent more bullish than market - buy
            price = conf_price - self.config.price_aggression
            return ("buy", max(1, min(99, price)))
        
        elif edge <= -self.config.min_edge:
            # Agent more bearish than market - sell
            price = conf_price + self.config.price_aggression
            return ("sell", max(1, min(99, price)))
        
        # Not enough edge
        return (None, None)

    def execute_belief(
        self,
        session_id: str,
        trader_name: str,
        confidence: float,
        quantity: Optional[int] = None,
    ) -> TradeResult:
        """
        Execute a trade based on agent's confidence.
        
        Args:
            session_id: Session/market to trade in
            trader_name: Trader placing the trade (must be valid enum)
            confidence: Agent's belief (0.0 to 1.0)
            quantity: Number of contracts (default from config)
        
        Returns:
            TradeResult with execution details
        """
        qty = quantity or self.config.default_quantity
        
        try:
            # Get current market state
            market_price = self.client.get_mid_price(session_id)
            
            # Convert confidence to trade
            side, price = self.confidence_to_trade(confidence, market_price)
            
            if side is None:
                return TradeResult(
                    success=True,
                    error="No trade - insufficient edge",
                )
            
            # Check position limits
            state = self.client.get_trader_state(session_id, trader_name)
            current_pos = state.get("position", 0)
            
            if side == "buy" and current_pos + qty > self.config.max_position:
                qty = max(0, self.config.max_position - current_pos)
            elif side == "sell" and current_pos - qty < -self.config.max_position:
                qty = max(0, self.config.max_position + current_pos)
            
            if qty <= 0:
                return TradeResult(
                    success=True,
                    error="No trade - position limit reached",
                )
            
            # Execute order
            result = self.client.place_order(
                session_id=session_id,
                trader_name=trader_name,
                side=side,
                price=price,
                quantity=qty,
            )
            
            order = result.get("order", {})
            trades = result.get("trades", [])
            
            return TradeResult(
                success=True,
                order_id=order.get("id"),
                side=side,
                price=price,
                quantity=qty,
                filled_quantity=order.get("filled_quantity", 0),
                trades_count=len(trades),
            )
            
        except Exception as e:
            return TradeResult(
                success=False,
                error=str(e),
            )

    def execute_prediction(
        self,
        session_id: str,
        trader_name: str,
        prediction: dict,
        quantity: Optional[int] = None,
    ) -> TradeResult:
        """
        Execute trade from a prediction dict (as returned by agents).
        
        Accepts various formats - extracts point estimate:
        - {"confidence": 0.65}  -> uses 0.65
        - {"mean": 0.65}  -> uses 0.65
        - {"mean": 0.65, "low": 0.55, "high": 0.75}  -> uses mean
        - {"probability": 0.65}  -> uses 0.65
        
        The agent/Grok can output whatever statistical format it wants.
        This layer just extracts the point estimate and trades on it.
        """
        # Try to extract point estimate from various formats
        confidence = (
            prediction.get("confidence") or
            prediction.get("mean") or
            prediction.get("probability") or
            prediction.get("estimate")
        )
        
        if confidence is None:
            return TradeResult(
                success=False,
                error="Prediction missing point estimate (confidence/mean/probability)",
            )
        
        return self.execute_belief(
            session_id=session_id,
            trader_name=trader_name,
            confidence=float(confidence),
            quantity=quantity,
        )

    def cancel_all_orders(self, session_id: str, trader_name: str) -> int:
        """Cancel all open orders for a trader. Returns count cancelled."""
        result = self.client.cancel_all_orders(session_id, trader_name)
        return result.get("cancelled", 0)

    def get_market_state(self, session_id: str) -> dict:
        """Get current market state for agent context."""
        orderbook = self.client.get_orderbook(session_id)
        
        best_bid = orderbook["bids"][0]["price"] if orderbook["bids"] else None
        best_ask = orderbook["asks"][0]["price"] if orderbook["asks"] else None
        
        return {
            "session_id": session_id,
            "last_price": orderbook.get("last_price"),
            "volume": orderbook.get("volume"),
            "best_bid": best_bid,
            "best_ask": best_ask,
            "mid_price": (best_bid + best_ask) / 2 if (best_bid and best_ask) else None,
            "spread": best_ask - best_bid if (best_bid and best_ask) else None,
        }
