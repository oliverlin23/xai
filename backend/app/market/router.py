"""
Market API router - endpoints for trading.

Simplified: session-based orderbook for probability trading.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List

from .models import Order, OrderSide as ModelOrderSide
from .orderbook import OrderBook
from .schemas import (
    CreateOrderRequest,
    CancelOrderRequest,
    OrderResponse,
    TradeResponse,
    TraderStateResponse,
    OrderBookResponse,
    OrderBookLevel,
    CreateOrderResponse,
    OrderSide,
)

router = APIRouter(prefix="/api/markets", tags=["markets"])

# In-memory storage: session_id -> OrderBook
orderbooks: Dict[str, OrderBook] = {}


def get_or_create_orderbook(session_id: str) -> OrderBook:
    """Get orderbook for session, creating if needed."""
    if session_id not in orderbooks:
        orderbooks[session_id] = OrderBook(session_id=session_id)
    return orderbooks[session_id]


def _order_to_response(order: Order) -> OrderResponse:
    """Convert Order model to response schema."""
    return OrderResponse(
        id=order.id,
        session_id=order.session_id,
        trader_name=order.trader_name,
        side=OrderSide(order.side.value),
        price=order.price,
        quantity=order.quantity,
        filled_quantity=order.filled_quantity,
        remaining_quantity=order.remaining_quantity,
        status=order.status,
        created_at=order.created_at,
    )


# ============ Order Book Endpoints ============

@router.get("/{session_id}/orderbook", response_model=OrderBookResponse)
async def get_orderbook(session_id: str):
    """Get current order book for a session."""
    ob = get_or_create_orderbook(session_id)
    snapshot = ob.get_book_snapshot()
    
    return OrderBookResponse(
        session_id=session_id,
        bids=[OrderBookLevel(**level) for level in snapshot["bids"]],
        asks=[OrderBookLevel(**level) for level in snapshot["asks"]],
        last_price=snapshot["last_price"],
        spread=snapshot["spread"],
        volume=snapshot["volume"],
    )


# ============ Order Endpoints ============

@router.post("/{session_id}/orders", response_model=CreateOrderResponse)
async def place_order(session_id: str, request: CreateOrderRequest):
    """Place a limit order."""
    ob = get_or_create_orderbook(session_id)
    
    order = Order(
        session_id=session_id,
        trader_name=request.trader_name,
        side=ModelOrderSide(request.side.value),
        price=request.price,
        quantity=request.quantity,
    )
    
    try:
        order, trades = ob.place_order(order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    state = ob.get_trader_state(request.trader_name)
    
    return CreateOrderResponse(
        order=_order_to_response(order),
        trades=[
            TradeResponse(
                id=t.id,
                session_id=t.session_id,
                buyer_name=t.buyer_name,
                seller_name=t.seller_name,
                price=t.price,
                quantity=t.quantity,
                created_at=t.created_at,
            )
            for t in trades
        ],
        trader_state=TraderStateResponse(
            session_id=state.session_id,
            trader_type=state.trader_type,
            name=state.name,
            position=state.position,
            cash=state.cash,
            pnl=state.pnl,
        ),
    )


@router.delete("/{session_id}/orders/{order_id}", response_model=OrderResponse)
async def cancel_order(session_id: str, order_id: str, trader_name: str):
    """Cancel an order."""
    ob = get_or_create_orderbook(session_id)
    
    try:
        order = ob.cancel_order(order_id, trader_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return _order_to_response(order)


@router.delete("/{session_id}/orders", response_model=dict)
async def cancel_all_orders(session_id: str, trader_name: str):
    """Cancel all orders for a trader."""
    ob = get_or_create_orderbook(session_id)
    count = ob.cancel_all_orders(trader_name)
    return {"cancelled": count}


@router.get("/{session_id}/orders/{order_id}", response_model=OrderResponse)
async def get_order(session_id: str, order_id: str):
    """Get order details."""
    ob = get_or_create_orderbook(session_id)
    order = ob.get_order(order_id)
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return _order_to_response(order)


# ============ Trader Endpoints ============

@router.get("/{session_id}/traders/{trader_name}", response_model=TraderStateResponse)
async def get_trader_state(session_id: str, trader_name: str):
    """Get a trader's state (position, cash, P&L)."""
    ob = get_or_create_orderbook(session_id)
    state = ob.get_trader_state(trader_name)
    
    return TraderStateResponse(
        session_id=state.session_id,
        trader_type=state.trader_type,
        name=state.name,
        position=state.position,
        cash=state.cash,
        pnl=state.pnl,
    )


@router.get("/{session_id}/traders/{trader_name}/orders", response_model=List[OrderResponse])
async def get_trader_orders(session_id: str, trader_name: str, active_only: bool = True):
    """Get all orders for a trader."""
    ob = get_or_create_orderbook(session_id)
    orders = ob.get_trader_orders(trader_name, active_only=active_only)
    return [_order_to_response(o) for o in orders]


@router.get("/{session_id}/traders", response_model=List[TraderStateResponse])
async def list_trader_states(session_id: str):
    """List all trader states in a session."""
    ob = get_or_create_orderbook(session_id)
    
    return [
        TraderStateResponse(
            session_id=state.session_id,
            trader_type=state.trader_type,
            name=state.name,
            position=state.position,
            cash=state.cash,
            pnl=state.pnl,
        )
        for state in ob.trader_states.values()
    ]


# ============ Trade Endpoints ============

@router.get("/{session_id}/trades", response_model=List[TradeResponse])
async def list_trades(session_id: str, limit: int = 50):
    """Get recent trades."""
    ob = get_or_create_orderbook(session_id)
    
    trades = ob.trades[-limit:][::-1]  # Most recent first
    
    return [
        TradeResponse(
            id=t.id,
            session_id=t.session_id,
            buyer_name=t.buyer_name,
            seller_name=t.seller_name,
            price=t.price,
            quantity=t.quantity,
            created_at=t.created_at,
        )
        for t in trades
    ]


# ============ Settlement ============

@router.post("/{session_id}/settle")
async def settle_market(session_id: str, outcome: bool):
    """
    Settle the market with final outcome.
    
    outcome=True: event happened (longs win)
    outcome=False: event didn't happen (shorts win)
    """
    ob = get_or_create_orderbook(session_id)
    payouts = ob.settle(outcome)
    
    return {
        "session_id": session_id,
        "outcome": outcome,
        "payouts": {k: float(v) for k, v in payouts.items()},
    }
