"""
Thin HTTP client for the Market API.

No business logic - just wraps the REST endpoints.
Provides both sync (MarketClient) and async (AsyncMarketClient) versions.
"""

from __future__ import annotations

import httpx
import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MarketClient:
    """Synchronous client for the Market API."""
    
    base_url: str = "http://localhost:8000"
    timeout: float = 10.0

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make HTTP request and return JSON response."""
        with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
            response = client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()

    # ============ Order Book ============

    def get_orderbook(self, session_id: str) -> dict:
        """Get current order book snapshot."""
        return self._request("GET", f"/api/markets/{session_id}/orderbook")

    def get_best_bid(self, session_id: str) -> Optional[int]:
        """Get best bid price (highest buy order)."""
        ob = self.get_orderbook(session_id)
        return ob["bids"][0]["price"] if ob["bids"] else None

    def get_best_ask(self, session_id: str) -> Optional[int]:
        """Get best ask price (lowest sell order)."""
        ob = self.get_orderbook(session_id)
        return ob["asks"][0]["price"] if ob["asks"] else None

    def get_mid_price(self, session_id: str) -> Optional[float]:
        """Get mid price between best bid and ask."""
        ob = self.get_orderbook(session_id)
        bid = ob["bids"][0]["price"] if ob["bids"] else None
        ask = ob["asks"][0]["price"] if ob["asks"] else None
        if bid and ask:
            return (bid + ask) / 2
        return bid or ask

    # ============ Orders ============

    def place_order(
        self,
        session_id: str,
        trader_name: str,
        side: str,  # "buy" or "sell"
        price: int,  # 1-99
        quantity: int,
    ) -> dict:
        """Place a limit order."""
        return self._request(
            "POST",
            f"/api/markets/{session_id}/orders",
            json={
                "trader_name": trader_name,
                "side": side,
                "price": price,
                "quantity": quantity,
            },
        )

    def cancel_order(self, session_id: str, order_id: str, trader_name: str) -> dict:
        """Cancel an order."""
        return self._request(
            "DELETE",
            f"/api/markets/{session_id}/orders/{order_id}",
            params={"trader_name": trader_name},
        )

    def cancel_all_orders(self, session_id: str, trader_name: str) -> dict:
        """Cancel all orders for a trader."""
        return self._request(
            "DELETE",
            f"/api/markets/{session_id}/orders",
            params={"trader_name": trader_name},
        )

    def get_order(self, session_id: str, order_id: str) -> dict:
        """Get order details."""
        return self._request("GET", f"/api/markets/{session_id}/orders/{order_id}")

    # ============ Traders ============

    def get_trader_state(self, session_id: str, trader_name: str) -> dict:
        """Get trader's state (position, cash, P&L)."""
        return self._request(
            "GET", f"/api/markets/{session_id}/traders/{trader_name}"
        )

    def get_trader_orders(self, session_id: str, trader_name: str, active_only: bool = True) -> List[dict]:
        """Get all orders for a trader."""
        return self._request(
            "GET",
            f"/api/markets/{session_id}/traders/{trader_name}/orders",
            params={"active_only": active_only},
        )

    def list_trader_states(self, session_id: str) -> List[dict]:
        """List all trader states in a session."""
        return self._request("GET", f"/api/markets/{session_id}/traders")

    # ============ Trades ============

    def list_trades(self, session_id: str, limit: int = 50) -> List[dict]:
        """Get recent trades."""
        return self._request(
            "GET",
            f"/api/markets/{session_id}/trades",
            params={"limit": limit},
        )

    # ============ Settlement ============

    def settle(self, session_id: str, outcome: bool) -> dict:
        """Settle the market with final outcome."""
        return self._request(
            "POST",
            f"/api/markets/{session_id}/settle",
            params={"outcome": outcome},
        )


class AsyncMarketClient:
    """Async client for the Market API."""
    
    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 30.0):
        self.base_url = base_url
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy init async client."""
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
        return self._client
    
    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make async HTTP request and return JSON response."""
        client = await self._get_client()
        response = await client.request(method, path, **kwargs)
        response.raise_for_status()
        return response.json()
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    # ============ Order Book ============

    async def get_orderbook(self, session_id: str) -> dict:
        """Get current order book snapshot."""
        return await self._request("GET", f"/api/markets/{session_id}/orderbook")

    async def get_best_bid(self, session_id: str) -> Optional[int]:
        """Get best bid price (highest buy order)."""
        ob = await self.get_orderbook(session_id)
        return ob["bids"][0]["price"] if ob["bids"] else None

    async def get_best_ask(self, session_id: str) -> Optional[int]:
        """Get best ask price (lowest sell order)."""
        ob = await self.get_orderbook(session_id)
        return ob["asks"][0]["price"] if ob["asks"] else None

    async def get_mid_price(self, session_id: str) -> Optional[float]:
        """Get mid price between best bid and ask."""
        ob = await self.get_orderbook(session_id)
        bid = ob["bids"][0]["price"] if ob["bids"] else None
        ask = ob["asks"][0]["price"] if ob["asks"] else None
        if bid and ask:
            return (bid + ask) / 2
        return bid or ask

    # ============ Orders ============

    async def place_order(
        self,
        session_id: str,
        trader_name: str,
        side: str,
        price: int,
        quantity: int,
    ) -> dict:
        """Place a limit order."""
        return await self._request(
            "POST",
            f"/api/markets/{session_id}/orders",
            json={
                "trader_name": trader_name,
                "side": side,
                "price": price,
                "quantity": quantity,
            },
        )

    async def cancel_order(self, session_id: str, order_id: str, trader_name: str) -> dict:
        """Cancel an order."""
        return await self._request(
            "DELETE",
            f"/api/markets/{session_id}/orders/{order_id}",
            params={"trader_name": trader_name},
        )

    async def cancel_all_orders(self, session_id: str, trader_name: str) -> dict:
        """Cancel all orders for a trader."""
        return await self._request(
            "DELETE",
            f"/api/markets/{session_id}/orders",
            params={"trader_name": trader_name},
        )

    async def get_order(self, session_id: str, order_id: str) -> dict:
        """Get order details."""
        return await self._request("GET", f"/api/markets/{session_id}/orders/{order_id}")

    # ============ Traders ============

    async def get_trader_state(self, session_id: str, trader_name: str) -> dict:
        """Get trader's state (position, cash, P&L)."""
        return await self._request(
            "GET", f"/api/markets/{session_id}/traders/{trader_name}"
        )

    async def get_trader_orders(self, session_id: str, trader_name: str, active_only: bool = True) -> List[dict]:
        """Get all orders for a trader."""
        return await self._request(
            "GET",
            f"/api/markets/{session_id}/traders/{trader_name}/orders",
            params={"active_only": active_only},
        )

    async def list_trader_states(self, session_id: str) -> List[dict]:
        """List all trader states in a session."""
        return await self._request("GET", f"/api/markets/{session_id}/traders")

    # ============ Trades ============

    async def list_trades(self, session_id: str, limit: int = 50) -> List[dict]:
        """Get recent trades."""
        return await self._request(
            "GET",
            f"/api/markets/{session_id}/trades",
            params={"limit": limit},
        )

    # ============ Settlement ============

    async def settle(self, session_id: str, outcome: bool) -> dict:
        """Settle the market with final outcome."""
        return await self._request(
            "POST",
            f"/api/markets/{session_id}/settle",
            params={"outcome": outcome},
        )


class MarketMaker:
    """
    Market-making helper that places/cancels orders via the Market API.
    
    Provides higher-level operations like placing bid/ask spreads around
    a target price and automatically cancelling stale orders.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 30.0):
        self._client = AsyncMarketClient(base_url=base_url, timeout=timeout)
    
    async def get_orderbook(self, session_id: str) -> Dict[str, Any]:
        """Fetch current orderbook snapshot, with error handling."""
        try:
            return await self._client.get_orderbook(session_id)
        except Exception as e:
            logger.warning(f"Failed to fetch orderbook: {e}")
            return {"bids": [], "asks": [], "last_price": None, "spread": None, "volume": 0}
    
    async def get_recent_trades(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent trades from market, with error handling."""
        try:
            return await self._client.list_trades(session_id, limit=limit)
        except Exception as e:
            logger.warning(f"Failed to fetch trades: {e}")
            return []
    
    async def cancel_all_orders(self, session_id: str, trader_name: str) -> int:
        """Cancel all orders for a trader, with error handling."""
        try:
            result = await self._client.cancel_all_orders(session_id, trader_name)
            return result.get("cancelled", 0)
        except Exception as e:
            logger.warning(f"Failed to cancel orders: {e}")
            return 0
    
    async def place_order(
        self,
        session_id: str,
        trader_name: str,
        side: str,
        price: int,
        quantity: int,
    ) -> Optional[Dict[str, Any]]:
        """Place a limit order, with error handling."""
        try:
            return await self._client.place_order(session_id, trader_name, side, price, quantity)
        except Exception as e:
            logger.warning(f"Failed to place order: {e}")
            return None
    
    async def place_market_making_orders(
        self,
        session_id: str,
        trader_name: str,
        prediction: int,
        spread: int = 4,
        quantity: int = 100,
    ) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        Cancel existing orders and place new bid/ask around prediction.
        
        Args:
            session_id: Market session ID
            trader_name: Trader name (must be valid trader in the system)
            prediction: Probability prediction (0-100 cents)
            spread: Total spread width (default 4 = bid at pred-2, ask at pred+2)
            quantity: Order quantity
        
        Returns:
            Tuple of (bid_result, ask_result)
        """
        # Cancel existing orders first
        cancelled = await self.cancel_all_orders(session_id, trader_name)
        if cancelled > 0:
            logger.info(f"Cancelled {cancelled} existing orders for {trader_name}")
        
        # Calculate bid and ask prices
        half_spread = spread // 2
        bid_price = max(1, min(99, prediction - half_spread))
        ask_price = max(1, min(99, prediction + half_spread))
        
        # Place bid (buy at lower price)
        bid_result = await self.place_order(session_id, trader_name, "buy", bid_price, quantity)
        # Place ask (sell at higher price)
        ask_result = await self.place_order(session_id, trader_name, "sell", ask_price, quantity)
        
        return bid_result, ask_result
    
    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.close()


class SupabaseMarketMaker:
    """
    Market-making helper that reads/writes directly to Supabase tables.
    
    Uses the orderbook_live, trades tables directly instead of going through
    a separate market server. Order matching is handled by:
    1. Database trigger that calls the match-orders Edge Function
    2. Or manual call to match_orders_for_session() SQL function
    """
    
    def __init__(self):
        from app.db.client import get_db_client
        self._client = get_db_client()
    
    def get_orderbook(self, session_id: str) -> Dict[str, Any]:
        """Fetch current orderbook snapshot from Supabase."""
        try:
            # Get bids (buy orders) - highest price first
            bids_result = self._client.table("orderbook_live").select("*").eq(
                "session_id", session_id
            ).eq("side", "buy").in_(
                "status", ["open", "partially_filled"]
            ).order("price", desc=True).execute()
            
            # Get asks (sell orders) - lowest price first
            asks_result = self._client.table("orderbook_live").select("*").eq(
                "session_id", session_id
            ).eq("side", "sell").in_(
                "status", ["open", "partially_filled"]
            ).order("price", desc=False).execute()
            
            # Aggregate by price level
            def aggregate_levels(orders: List[Dict], descending: bool = False) -> List[Dict]:
                levels: Dict[int, Dict] = {}
                for order in orders:
                    price = order["price"]
                    remaining = order["quantity"] - order["filled_quantity"]
                    if remaining > 0:
                        if price not in levels:
                            levels[price] = {"price": price, "quantity": 0, "order_count": 0}
                        levels[price]["quantity"] += remaining
                        levels[price]["order_count"] += 1
                
                sorted_levels = sorted(levels.values(), key=lambda x: x["price"], reverse=descending)
                return sorted_levels
            
            bids = aggregate_levels(bids_result.data or [], descending=True)
            asks = aggregate_levels(asks_result.data or [], descending=False)
            
            # Calculate spread and last price
            best_bid = bids[0]["price"] if bids else None
            best_ask = asks[0]["price"] if asks else None
            spread = (best_ask - best_bid) if (best_bid is not None and best_ask is not None) else None
            
            # Get last trade price
            last_trade = self._client.table("trades").select("price").eq(
                "session_id", session_id
            ).order("created_at", desc=True).limit(1).execute()
            
            last_price = last_trade.data[0]["price"] if last_trade.data else None
            
            # Get total volume
            volume_result = self._client.table("trades").select("quantity").eq(
                "session_id", session_id
            ).execute()
            volume = sum(t["quantity"] for t in (volume_result.data or []))
            
            return {
                "session_id": session_id,
                "bids": bids,
                "asks": asks,
                "last_price": last_price,
                "spread": spread,
                "volume": volume,
            }
        except Exception as e:
            logger.warning(f"Failed to fetch orderbook from Supabase: {e}")
            return {"bids": [], "asks": [], "last_price": None, "spread": None, "volume": 0}
    
    def get_recent_trades(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent trades from Supabase."""
        try:
            result = self._client.table("trades").select("*").eq(
                "session_id", session_id
            ).order("created_at", desc=True).limit(limit).execute()
            
            return result.data or []
        except Exception as e:
            logger.warning(f"Failed to fetch trades from Supabase: {e}")
            return []
    
    def cancel_all_orders(self, session_id: str, trader_name: str) -> int:
        """Cancel all open orders for a trader by updating status to 'cancelled'."""
        try:
            # Get count of orders to cancel
            count_result = self._client.table("orderbook_live").select(
                "id", count="exact"
            ).eq("session_id", session_id).eq(
                "trader_name", trader_name
            ).in_("status", ["open", "partially_filled"]).execute()
            
            count = count_result.count or 0
            
            if count > 0:
                # Update status to cancelled
                self._client.table("orderbook_live").update(
                    {"status": "cancelled"}
                ).eq("session_id", session_id).eq(
                    "trader_name", trader_name
                ).in_("status", ["open", "partially_filled"]).execute()
            
            return count
        except Exception as e:
            logger.warning(f"Failed to cancel orders in Supabase: {e}")
            return 0
    
    def place_order(
        self,
        session_id: str,
        trader_name: str,
        side: str,
        price: int,
        quantity: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Place a limit order by inserting into orderbook_live.
        The database trigger will automatically call the match-orders Edge Function.
        """
        try:
            result = self._client.table("orderbook_live").insert({
                "session_id": session_id,
                "trader_name": trader_name,
                "side": side,
                "price": price,
                "quantity": quantity,
                "filled_quantity": 0,
                "status": "open",
            }).execute()
            
            if result.data:
                logger.info(f"Placed {side} order: {quantity} @ {price} for {trader_name}")
                return result.data[0]
            return None
        except Exception as e:
            logger.warning(f"Failed to place order in Supabase: {e}")
            return None
    
    def place_market_making_orders(
        self,
        session_id: str,
        trader_name: str,
        prediction: int,
        spread: int = 4,
        quantity: int = 100,
    ) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        Cancel existing orders and place new bid/ask around prediction.
        
        Args:
            session_id: Market session ID (UUID string)
            trader_name: Trader name (must be valid trader_name enum value)
            prediction: Probability prediction (0-100 cents)
            spread: Total spread width (default 4 = bid at pred-2, ask at pred+2)
            quantity: Order quantity
        
        Returns:
            Tuple of (bid_result, ask_result)
        """
        # Cancel existing orders first
        cancelled = self.cancel_all_orders(session_id, trader_name)
        if cancelled > 0:
            logger.info(f"Cancelled {cancelled} existing orders for {trader_name}")
        
        # Calculate bid and ask prices
        half_spread = spread // 2
        bid_price = max(1, min(99, prediction - half_spread))
        ask_price = max(1, min(99, prediction + half_spread))
        
        # Place bid (buy at lower price)
        bid_result = self.place_order(session_id, trader_name, "buy", bid_price, quantity)
        # Place ask (sell at higher price)
        ask_result = self.place_order(session_id, trader_name, "sell", ask_price, quantity)
        
        return bid_result, ask_result
    
    def trigger_matching(self, session_id: str) -> Dict[str, Any]:
        """
        Manually trigger order matching using the SQL function.
        Use this if the Edge Function trigger is not set up or not working.
        """
        try:
            result = self._client.rpc("match_orders_for_session", {"p_session_id": session_id}).execute()
            if result.data:
                return {"trades_count": result.data[0]["trades_count"], "volume": result.data[0]["volume"]}
            return {"trades_count": 0, "volume": 0}
        except Exception as e:
            logger.warning(f"Failed to trigger matching: {e}")
            return {"trades_count": 0, "volume": 0, "error": str(e)}
