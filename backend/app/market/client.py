"""
Thin HTTP client for the Market API.

No business logic - just wraps the REST endpoints.
"""

from __future__ import annotations

import httpx
from typing import Optional, List, Any
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

    # ============ Markets ============

    def create_market(
        self,
        question: str,
        description: str = "",
        session_id: Optional[str] = None,
    ) -> dict:
        """Create a new prediction market."""
        return self._request(
            "POST",
            "/api/markets",
            json={
                "question": question,
                "description": description,
                "session_id": session_id,
            },
        )

    def get_market(self, market_id: str) -> dict:
        """Get market details."""
        return self._request("GET", f"/api/markets/{market_id}")

    def list_markets(self, status: Optional[str] = None) -> List[dict]:
        """List all markets."""
        params = {"status": status} if status else {}
        return self._request("GET", "/api/markets", params=params)

    def resolve_market(self, market_id: str, outcome: bool) -> dict:
        """Resolve market with final outcome."""
        return self._request(
            "POST",
            f"/api/markets/{market_id}/resolve",
            json={"outcome": outcome},
        )

    # ============ Order Book ============

    def get_orderbook(self, market_id: str) -> dict:
        """Get current order book snapshot."""
        return self._request("GET", f"/api/markets/{market_id}/orderbook")

    def get_best_bid(self, market_id: str) -> Optional[int]:
        """Get best bid price (highest YES order)."""
        ob = self.get_orderbook(market_id)
        return ob["bids"][0]["price"] if ob["bids"] else None

    def get_best_ask(self, market_id: str) -> Optional[int]:
        """Get best ask price (lowest NO order)."""
        return ob["asks"][0]["price"] if ob["asks"] else None

    def get_mid_price(self, market_id: str) -> Optional[float]:
        """Get mid price between best bid and ask."""
        ob = self.get_orderbook(market_id)
        bid = ob["bids"][0]["price"] if ob["bids"] else None
        ask = ob["asks"][0]["price"] if ob["asks"] else None
        if bid and ask:
            return (bid + ask) / 2
        return bid or ask

    # ============ Orders ============

    def place_order(
        self,
        market_id: str,
        agent_id: str,
        side: str,  # "yes" or "no"
        price: int,  # 1-99
        quantity: int,
    ) -> dict:
        """Place a limit order."""
        return self._request(
            "POST",
            f"/api/markets/{market_id}/orders",
            json={
                "market_id": market_id,
                "agent_id": agent_id,
                "side": side,
                "price": price,
                "quantity": quantity,
            },
        )

    def cancel_order(self, market_id: str, order_id: str, agent_id: str) -> dict:
        """Cancel an order."""
        return self._request(
            "DELETE",
            f"/api/markets/{market_id}/orders/{order_id}",
            params={"agent_id": agent_id},
        )

    def get_order(self, market_id: str, order_id: str) -> dict:
        """Get order details."""
        return self._request("GET", f"/api/markets/{market_id}/orders/{order_id}")

    # ============ Positions ============

    def get_position(self, market_id: str, agent_id: str) -> dict:
        """Get agent's position in a market."""
        return self._request(
            "GET", f"/api/markets/{market_id}/positions/{agent_id}"
        )

    def list_positions(self, market_id: str) -> List[dict]:
        """List all positions in a market."""
        return self._request("GET", f"/api/markets/{market_id}/positions")

    # ============ Trades ============

    def list_trades(self, market_id: str, limit: int = 50) -> List[dict]:
        """Get recent trades."""
        return self._request(
            "GET",
            f"/api/markets/{market_id}/trades",
            params={"limit": limit},
        )

    # ============ Agent Queries ============

    def get_agent_orders(self, agent_id: str, active_only: bool = True) -> List[dict]:
        """Get all orders for an agent across markets."""
        return self._request(
            "GET",
            f"/api/markets/agents/{agent_id}/orders",
            params={"active_only": active_only},
        )

    def get_agent_positions(self, agent_id: str) -> List[dict]:
        """Get all positions for an agent across markets."""
        return self._request("GET", f"/api/markets/agents/{agent_id}/positions")

