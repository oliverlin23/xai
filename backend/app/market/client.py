"""
Thin HTTP client for the Market API.

No business logic - just wraps the REST endpoints.
"""

from __future__ import annotations

import httpx
from typing import Optional, List
from dataclasses import dataclass


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
