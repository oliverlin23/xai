"""
Market maker client that reads/writes directly to Supabase tables.

Uses orderbook_live and trades tables. Order matching is handled by the
place_market_making_orders SQL function which does cancel + place + match atomically.
"""

from __future__ import annotations

import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


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
    ) -> Dict[str, Any]:
        """
        Atomically cancel existing orders, place new bid/ask, and trigger matching.
        
        This uses a single database transaction via the place_market_making_orders
        SQL function, ensuring:
        1. All existing orders are cancelled
        2. New bid and ask orders are placed
        3. Order matching runs immediately
        4. All happens atomically (no race conditions)
        
        Args:
            session_id: Market session ID (UUID string)
            trader_name: Trader name (must be valid trader_name enum value)
            prediction: Probability prediction (0-100 cents)
            spread: Total spread width (default 4 = bid at pred-2, ask at pred+2)
            quantity: Order quantity
        
        Returns:
            Dict with: cancelled_count, bid_id, ask_id, bid_price, ask_price, 
                       quantity, trades_count, volume
        """
        # Calculate bid and ask prices
        half_spread = spread // 2
        bid_price = max(1, min(99, prediction - half_spread))
        ask_price = max(1, min(99, prediction + half_spread))
        
        try:
            # Call atomic SQL function that does cancel + place + match in one transaction
            result = self._client.rpc("place_market_making_orders", {
                "p_session_id": session_id,
                "p_trader_name": trader_name,
                "p_bid_price": bid_price,
                "p_ask_price": ask_price,
                "p_quantity": quantity,
            }).execute()
            
            if result.data:
                data = result.data
                if data.get("cancelled_count", 0) > 0:
                    logger.info(f"Cancelled {data['cancelled_count']} existing orders for {trader_name}")
                logger.info(f"Placed buy order: {quantity} @ {bid_price} for {trader_name}")
                logger.info(f"Placed sell order: {quantity} @ {ask_price} for {trader_name}")
                if data.get("trades_count", 0) > 0:
                    logger.info(f"Matched {data['trades_count']} trades, volume={data['volume']}")
                return data
            
            return {"error": "No data returned from place_market_making_orders"}
        except Exception as e:
            logger.warning(f"Failed to place market making orders: {e}")
            return {"error": str(e)}
    
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
