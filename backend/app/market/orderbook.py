"""
Order book engine with price-time priority matching.

Simplified for probability trading:
- Buy orders want to buy at price P or lower
- Sell orders want to sell at price P or higher
- Match when buy_price >= sell_price
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from .models import Order, Trade, TraderState, OrderSide, OrderStatus


@dataclass
class OrderBook:
    """
    Order book for a single session/market.
    
    Buy orders (bids): sorted by price descending (highest first)
    Sell orders (asks): sorted by price ascending (lowest first)
    
    Match when best_bid >= best_ask
    """
    session_id: str
    
    # Orders indexed by price level, then by time (FIFO within price)
    buy_orders: Dict[int, List[Order]] = field(default_factory=lambda: defaultdict(list))
    sell_orders: Dict[int, List[Order]] = field(default_factory=lambda: defaultdict(list))
    
    # All orders by ID for quick lookup
    orders_by_id: Dict[str, Order] = field(default_factory=dict)
    
    # Trader states (positions, cash, P&L)
    trader_states: Dict[str, TraderState] = field(default_factory=dict)
    
    # Trade history
    trades: List[Trade] = field(default_factory=list)
    
    # Market stats
    last_price: Optional[int] = None
    volume: int = 0

    def get_trader_state(self, trader_name: str) -> TraderState:
        """Get or create state for a trader."""
        if trader_name not in self.trader_states:
            self.trader_states[trader_name] = TraderState(
                session_id=self.session_id,
                name=trader_name,
            )
        return self.trader_states[trader_name]

    def place_order(self, order: Order) -> Tuple[Order, List[Trade]]:
        """
        Place an order and attempt to match it.
        
        Returns the order (possibly filled) and any trades that occurred.
        """
        order.session_id = self.session_id
        self.orders_by_id[order.id] = order
        
        # Try to match the order
        trades = self._match_order(order)
        
        # If order still has remaining quantity, add to book
        if order.is_active and order.remaining_quantity > 0:
            if order.side == OrderSide.BUY:
                self.buy_orders[order.price].append(order)
            else:
                self.sell_orders[order.price].append(order)
        
        return order, trades

    def _match_order(self, incoming: Order) -> List[Trade]:
        """
        Match incoming order against resting orders.
        
        Buy order matches sell orders at incoming.price or lower.
        Sell order matches buy orders at incoming.price or higher.
        """
        trades = []
        
        if incoming.side == OrderSide.BUY:
            # Buy order matches against sell orders
            opposite_book = self.sell_orders
            # Get all sell prices <= incoming buy price (best/lowest first)
            matchable_prices = sorted([p for p in opposite_book.keys() if p <= incoming.price])
        else:
            # Sell order matches against buy orders
            opposite_book = self.buy_orders
            # Get all buy prices >= incoming sell price (best/highest first)
            matchable_prices = sorted([p for p in opposite_book.keys() if p >= incoming.price], reverse=True)
        
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
                
                # Execution price is the resting order's price (price-time priority)
                exec_price = resting.price
                
                # Determine buyer and seller
                if incoming.side == OrderSide.BUY:
                    buyer_name = incoming.trader_name
                    seller_name = resting.trader_name
                else:
                    buyer_name = resting.trader_name
                    seller_name = incoming.trader_name
                
                # Create trade
                trade = Trade(
                    session_id=self.session_id,
                    buyer_name=buyer_name,
                    seller_name=seller_name,
                    price=exec_price,
                    quantity=fill_qty,
                )
                
                # Update orders
                incoming.fill(fill_qty)
                resting.fill(fill_qty)
                
                # Update trader states
                self._update_trader_states(trade)
                
                # Record trade
                self.trades.append(trade)
                trades.append(trade)
                
                # Update market stats
                self.last_price = trade.price
                self.volume += fill_qty
                
                # Remove filled resting order from book
                if not resting.is_active:
                    orders_at_price.pop(i)
                else:
                    i += 1
            
            # Clean up empty price levels
            if not orders_at_price:
                del opposite_book[price]
        
        return trades

    def _update_trader_states(self, trade: Trade) -> None:
        """Update trader positions and cash after a trade."""
        buyer = self.get_trader_state(trade.buyer_name)
        seller = self.get_trader_state(trade.seller_name)
        
        cost = Decimal(trade.price * trade.quantity) / 100  # Convert cents to dollars
        
        # Buyer: pays cash, gains position
        buyer.cash -= cost
        buyer.position += trade.quantity
        
        # Seller: receives cash, loses position
        seller.cash += cost
        seller.position -= trade.quantity

    def cancel_order(self, order_id: str, trader_name: str) -> Order:
        """Cancel an order. Only the owner can cancel."""
        order = self.orders_by_id.get(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")
        if order.trader_name != trader_name:
            raise ValueError("Cannot cancel another trader's order")
        if not order.is_active:
            raise ValueError(f"Order is already {order.status}")
        
        order.cancel()
        
        # Remove from price level
        book = self.buy_orders if order.side == OrderSide.BUY else self.sell_orders
        if order.price in book:
            book[order.price] = [o for o in book[order.price] if o.id != order_id]
            if not book[order.price]:
                del book[order.price]
        
        return order

    def cancel_all_orders(self, trader_name: str) -> int:
        """Cancel all active orders for a trader. Returns count cancelled."""
        cancelled = 0
        for order in list(self.orders_by_id.values()):
            if order.trader_name == trader_name and order.is_active:
                try:
                    self.cancel_order(order.id, trader_name)
                    cancelled += 1
                except ValueError:
                    pass
        return cancelled

    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        return self.orders_by_id.get(order_id)

    def get_trader_orders(self, trader_name: str, active_only: bool = True) -> List[Order]:
        """Get all orders for a trader."""
        orders = [o for o in self.orders_by_id.values() if o.trader_name == trader_name]
        if active_only:
            orders = [o for o in orders if o.is_active]
        return sorted(orders, key=lambda o: o.created_at, reverse=True)

    def get_best_bid(self) -> Optional[int]:
        """Get highest buy price."""
        if not self.buy_orders:
            return None
        return max(self.buy_orders.keys())

    def get_best_ask(self) -> Optional[int]:
        """Get lowest sell price."""
        if not self.sell_orders:
            return None
        return min(self.sell_orders.keys())

    def get_mid_price(self) -> Optional[float]:
        """Get mid price between best bid and ask."""
        bid = self.get_best_bid()
        ask = self.get_best_ask()
        if bid and ask:
            return (bid + ask) / 2
        return bid or ask

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
        
        bids = aggregate_levels(self.buy_orders, descending=True)  # Best bid first
        asks = aggregate_levels(self.sell_orders, descending=False)  # Best ask first
        
        best_bid = bids[0]["price"] if bids else None
        best_ask = asks[0]["price"] if asks else None
        spread = (best_ask - best_bid) if (best_bid is not None and best_ask is not None) else None
        
        return {
            "session_id": self.session_id,
            "bids": bids,
            "asks": asks,
            "last_price": self.last_price,
            "spread": spread,
            "volume": self.volume,
        }

    def settle(self, outcome: bool) -> Dict[str, Decimal]:
        """
        Settle all positions after market resolution.
        
        outcome=True: probability was 100% (longs win $1 per contract)
        outcome=False: probability was 0% (shorts win $1 per contract)
        
        Returns dict of trader_name -> payout.
        """
        payouts: Dict[str, Decimal] = {}
        
        for trader_name, state in self.trader_states.items():
            if outcome:
                # Event happened: long positions pay out $1 per contract
                payout = Decimal(max(0, state.position))
            else:
                # Event didn't happen: short positions pay out $1 per contract
                payout = Decimal(max(0, -state.position))
            
            state.cash += payout
            state.pnl = state.cash - Decimal("1000.00")  # P&L vs starting cash
            payouts[trader_name] = payout
        
        return payouts
