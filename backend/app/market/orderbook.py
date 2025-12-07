"""
Order book engine with price-time priority matching.

This is an in-memory order book. For production, you'd want to persist
orders and use a proper matching engine, but this works for agent trading.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from datetime import datetime, UTC

from .models import Order, Trade, Position, Market, OrderSide, OrderStatus, MarketStatus


@dataclass
class OrderBook:
    """
    In-memory order book for a single market.
    
    YES orders are "bids" - agents wanting to buy YES contracts.
    NO orders are "asks" - agents wanting to buy NO contracts.
    
    Matching logic:
    - YES at price P matches with NO at price (100-P) or better
    - Example: YES@60 matches NO@40 (both willing to pay 60+40=100 for opposite sides)
    """
    market: Market
    
    # Orders indexed by price level, then by time (FIFO within price)
    yes_orders: Dict[int, List[Order]] = field(default_factory=lambda: defaultdict(list))
    no_orders: Dict[int, List[Order]] = field(default_factory=lambda: defaultdict(list))
    
    # All orders by ID for quick lookup
    orders_by_id: Dict[str, Order] = field(default_factory=dict)
    
    # Agent positions
    positions: Dict[str, Position] = field(default_factory=dict)
    
    # Trade history
    trades: List[Trade] = field(default_factory=list)

    def get_position(self, agent_id: str) -> Position:
        """Get or create position for an agent."""
        if agent_id not in self.positions:
            self.positions[agent_id] = Position(
                agent_id=agent_id,
                market_id=self.market.id,
            )
        return self.positions[agent_id]

    def place_order(self, order: Order) -> Tuple[Order, List[Trade]]:
        """
        Place an order and attempt to match it.
        
        Returns the order (possibly filled) and any trades that occurred.
        """
        if self.market.status != MarketStatus.OPEN:
            raise ValueError(f"Market is {self.market.status}, cannot place orders")
        
        order.market_id = self.market.id
        self.orders_by_id[order.id] = order
        
        # Try to match the order
        trades = self._match_order(order)
        
        # If order still has remaining quantity, add to book
        if order.is_active and order.remaining_quantity > 0:
            if order.side == OrderSide.YES:
                self.yes_orders[order.price].append(order)
            else:
                self.no_orders[order.price].append(order)
        
        return order, trades

    def _match_order(self, incoming: Order) -> List[Trade]:
        """
        Match incoming order against resting orders.
        
        YES@P matches NO@(100-P) or better.
        """
        trades = []
        
        if incoming.side == OrderSide.YES:
            # YES order matches against NO orders
            # YES@60 needs NO@40 or lower (100-60=40)
            match_price = 100 - incoming.price
            opposite_book = self.no_orders
            
            # Get all NO prices <= match_price (sorted ascending for best price first)
            matchable_prices = sorted([p for p in opposite_book.keys() if p <= match_price])
        else:
            # NO order matches against YES orders
            # NO@40 needs YES@60 or higher (100-40=60)
            match_price = 100 - incoming.price
            opposite_book = self.yes_orders
            
            # Get all YES prices >= match_price (sorted descending for best price first)
            matchable_prices = sorted([p for p in opposite_book.keys() if p >= match_price], reverse=True)
        
        for price in matchable_prices:
            if incoming.remaining_quantity <= 0:
                break
                
            orders_at_price = opposite_book[price]
            i = 0
            while i < len(orders_at_price) and incoming.remaining_quantity > 0:
                resting = orders_at_price[i]
                
                if not resting.is_active:
                    i += 1
                    continue
                
                # Calculate fill quantity
                fill_qty = min(incoming.remaining_quantity, resting.remaining_quantity)
                
                # Execution price is the resting order's price
                exec_price = resting.price
                
                # Create trade
                if incoming.side == OrderSide.YES:
                    trade = Trade(
                        market_id=self.market.id,
                        buy_order_id=incoming.id,
                        sell_order_id=resting.id,
                        buyer_agent_id=incoming.agent_id,
                        seller_agent_id=resting.agent_id,
                        price=exec_price,
                        quantity=fill_qty,
                    )
                else:
                    trade = Trade(
                        market_id=self.market.id,
                        buy_order_id=resting.id,
                        sell_order_id=incoming.id,
                        buyer_agent_id=resting.agent_id,
                        seller_agent_id=incoming.agent_id,
                        price=100 - exec_price,  # Convert NO price to YES equivalent
                        quantity=fill_qty,
                    )
                
                # Update orders
                incoming.fill(fill_qty)
                resting.fill(fill_qty)
                
                # Update positions
                self._update_positions(trade, incoming, resting)
                
                # Record trade
                self.trades.append(trade)
                trades.append(trade)
                
                # Update market stats
                self.market.last_price = trade.price
                self.market.volume += fill_qty
                
                # Remove filled resting order from book
                if not resting.is_active:
                    orders_at_price.pop(i)
                else:
                    i += 1
            
            # Clean up empty price levels
            if not orders_at_price:
                del opposite_book[price]
        
        return trades

    def _update_positions(self, trade: Trade, incoming: Order, resting: Order) -> None:
        """Update positions after a trade."""
        buyer_pos = self.get_position(trade.buyer_agent_id)
        seller_pos = self.get_position(trade.seller_agent_id)
        
        # Buyer gets YES contracts
        old_yes_qty = buyer_pos.yes_quantity
        buyer_pos.yes_quantity += trade.quantity
        if buyer_pos.yes_quantity > 0:
            # Update average price
            old_cost = old_yes_qty * buyer_pos.avg_yes_price
            new_cost = trade.quantity * trade.price
            buyer_pos.avg_yes_price = (old_cost + Decimal(new_cost)) / buyer_pos.yes_quantity
        
        # Seller gets NO contracts (or closes YES position)
        old_no_qty = seller_pos.no_quantity
        seller_pos.no_quantity += trade.quantity
        if seller_pos.no_quantity > 0:
            old_cost = old_no_qty * seller_pos.avg_no_price
            new_cost = trade.quantity * (100 - trade.price)
            seller_pos.avg_no_price = (old_cost + Decimal(new_cost)) / seller_pos.no_quantity

    def cancel_order(self, order_id: str, agent_id: str) -> Order:
        """Cancel an order. Only the owner can cancel."""
        order = self.orders_by_id.get(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        if order.agent_id != agent_id:
            raise ValueError("Cannot cancel another agent's order")
        if not order.is_active:
            raise ValueError(f"Order is already {order.status}")
        
        order.cancel()
        
        # Remove from price level
        book = self.yes_orders if order.side == OrderSide.YES else self.no_orders
        if order.price in book:
            book[order.price] = [o for o in book[order.price] if o.id != order_id]
            if not book[order.price]:
                del book[order.price]
        
        return order

    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return self.orders_by_id.get(order_id)

    def get_agent_orders(self, agent_id: str, active_only: bool = True) -> List[Order]:
        """Get all orders for an agent."""
        orders = [o for o in self.orders_by_id.values() if o.agent_id == agent_id]
        if active_only:
            orders = [o for o in orders if o.is_active]
        return sorted(orders, key=lambda o: o.created_at, reverse=True)

    def get_book_snapshot(self) -> dict:
        """Get current order book state."""
        def aggregate_levels(book: Dict[int, List[Order]], descending: bool = False) -> List[dict]:
            levels = []
            for price in sorted(book.keys(), reverse=descending):
                active_orders = [o for o in book[price] if o.is_active]
                if active_orders:
                    total_qty = sum(o.remaining_quantity for o in active_orders)
                    levels.append({
                        "price": price,
                        "quantity": total_qty,
                        "order_count": len(active_orders),
                    })
            return levels
        
        bids = aggregate_levels(self.yes_orders, descending=True)  # Best bid first
        asks = aggregate_levels(self.no_orders, descending=False)  # Best ask first
        
        best_bid = bids[0]["price"] if bids else None
        best_ask = asks[0]["price"] if asks else None
        spread = (best_ask - best_bid) if (best_bid and best_ask) else None
        
        return {
            "market_id": self.market.id,
            "bids": bids,
            "asks": asks,
            "last_price": self.market.last_price,
            "spread": spread,
        }

    def settle(self, outcome: bool) -> Dict[str, Decimal]:
        """
        Settle all positions after market resolution.
        
        Returns dict of agent_id -> payout.
        """
        self.market.resolve(outcome)
        payouts: Dict[str, Decimal] = {}
        
        for agent_id, pos in self.positions.items():
            payout = Decimal("0")
            if outcome:
                # YES wins - YES holders get $1 per contract
                payout = Decimal(pos.yes_quantity)
            else:
                # NO wins - NO holders get $1 per contract
                payout = Decimal(pos.no_quantity)
            
            # Subtract what they paid
            cost = (pos.yes_quantity * pos.avg_yes_price + 
                    pos.no_quantity * pos.avg_no_price) / 100
            
            pos.realized_pnl = payout - cost
            payouts[agent_id] = payout
        
        return payouts

