"""
Market API router - endpoints for trading.

All markets are stored in-memory for now. For production, persist to DB.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List

from .models import Market, Order, OrderSide, MarketStatus
from .orderbook import OrderBook
from .schemas import (
    CreateMarketRequest,
    CreateOrderRequest,
    CancelOrderRequest,
    ResolveMarketRequest,
    MarketResponse,
    MarketSummary,
    OrderResponse,
    TradeResponse,
    PositionResponse,
    OrderBookResponse,
    OrderBookLevel,
    CreateOrderResponse,
)

router = APIRouter(prefix="/api/markets", tags=["markets"])

# In-memory storage
markets: Dict[str, Market] = {}
orderbooks: Dict[str, OrderBook] = {}


def _get_orderbook(market_id: str) -> OrderBook:
    """Get orderbook or raise 404."""
    if market_id not in orderbooks:
        raise HTTPException(status_code=404, detail=f"Market {market_id} not found")
    return orderbooks[market_id]


def _order_to_response(order: Order) -> OrderResponse:
    """Convert Order model to response schema."""
    return OrderResponse(
        id=order.id,
        market_id=order.market_id,
        agent_id=order.agent_id,
        side=order.side,
        price=order.price,
        quantity=order.quantity,
        filled_quantity=order.filled_quantity,
        remaining_quantity=order.remaining_quantity,
        status=order.status,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


def _market_to_response(market: Market, ob: OrderBook) -> MarketResponse:
    """Convert Market model to response schema."""
    return MarketResponse(
        id=market.id,
        question=market.question,
        description=market.description,
        session_id=market.session_id,
        status=market.status,
        resolution=market.resolution,
        last_price=market.last_price,
        volume=market.volume,
        created_at=market.created_at,
        closes_at=market.closes_at,
        resolved_at=market.resolved_at,
    )


# ============ Market Endpoints ============

@router.post("", response_model=MarketResponse)
async def create_market(request: CreateMarketRequest):
    """Create a new prediction market."""
    market = Market(
        question=request.question,
        description=request.description,
        session_id=request.session_id,
        closes_at=request.closes_at,
    )
    ob = OrderBook(market=market)
    
    markets[market.id] = market
    orderbooks[market.id] = ob
    
    return _market_to_response(market, ob)


@router.get("", response_model=List[MarketSummary])
async def list_markets(status: MarketStatus = None):
    """List all markets, optionally filtered by status."""
    result = []
    for market_id, market in markets.items():
        if status and market.status != status:
            continue
        
        ob = orderbooks[market_id]
        snapshot = ob.get_book_snapshot()
        
        result.append(MarketSummary(
            id=market.id,
            question=market.question,
            status=market.status,
            last_price=market.last_price,
            volume=market.volume,
            best_bid=snapshot["bids"][0]["price"] if snapshot["bids"] else None,
            best_ask=snapshot["asks"][0]["price"] if snapshot["asks"] else None,
        ))
    
    return result


@router.get("/{market_id}", response_model=MarketResponse)
async def get_market(market_id: str):
    """Get market details."""
    if market_id not in markets:
        raise HTTPException(status_code=404, detail="Market not found")
    
    market = markets[market_id]
    ob = orderbooks[market_id]
    return _market_to_response(market, ob)


@router.get("/{market_id}/orderbook", response_model=OrderBookResponse)
async def get_orderbook(market_id: str):
    """Get current order book."""
    ob = _get_orderbook(market_id)
    snapshot = ob.get_book_snapshot()
    
    return OrderBookResponse(
        market_id=market_id,
        bids=[OrderBookLevel(**level) for level in snapshot["bids"]],
        asks=[OrderBookLevel(**level) for level in snapshot["asks"]],
        last_price=snapshot["last_price"],
        spread=snapshot["spread"],
    )


@router.post("/{market_id}/resolve", response_model=MarketResponse)
async def resolve_market(market_id: str, request: ResolveMarketRequest):
    """Resolve a market with final outcome."""
    ob = _get_orderbook(market_id)
    
    if ob.market.status == MarketStatus.RESOLVED:
        raise HTTPException(status_code=400, detail="Market already resolved")
    
    # Settle all positions
    ob.settle(request.outcome)
    
    return _market_to_response(ob.market, ob)


# ============ Order Endpoints ============

@router.post("/{market_id}/orders", response_model=CreateOrderResponse)
async def place_order(market_id: str, request: CreateOrderRequest):
    """Place a limit order."""
    if request.market_id != market_id:
        raise HTTPException(status_code=400, detail="Market ID mismatch")
    
    ob = _get_orderbook(market_id)
    
    order = Order(
        market_id=market_id,
        agent_id=request.agent_id,
        side=OrderSide(request.side),
        price=request.price,
        quantity=request.quantity,
    )
    
    try:
        order, trades = ob.place_order(order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    position = ob.get_position(request.agent_id)
    
    return CreateOrderResponse(
        order=_order_to_response(order),
        trades=[
            TradeResponse(
                id=t.id,
                market_id=t.market_id,
                buyer_agent_id=t.buyer_agent_id,
                seller_agent_id=t.seller_agent_id,
                price=t.price,
                quantity=t.quantity,
                created_at=t.created_at,
            )
            for t in trades
        ],
        position=PositionResponse(
            agent_id=position.agent_id,
            market_id=position.market_id,
            yes_quantity=position.yes_quantity,
            no_quantity=position.no_quantity,
            net_position=position.net_position,
            avg_yes_price=position.avg_yes_price,
            avg_no_price=position.avg_no_price,
            realized_pnl=position.realized_pnl,
        ),
    )


@router.delete("/{market_id}/orders/{order_id}", response_model=OrderResponse)
async def cancel_order(market_id: str, order_id: str, agent_id: str):
    """Cancel an order."""
    ob = _get_orderbook(market_id)
    
    try:
        order = ob.cancel_order(order_id, agent_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return _order_to_response(order)


@router.get("/{market_id}/orders/{order_id}", response_model=OrderResponse)
async def get_order(market_id: str, order_id: str):
    """Get order details."""
    ob = _get_orderbook(market_id)
    order = ob.get_order(order_id)
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return _order_to_response(order)


# ============ Position Endpoints ============

@router.get("/{market_id}/positions/{agent_id}", response_model=PositionResponse)
async def get_position(market_id: str, agent_id: str):
    """Get an agent's position in a market."""
    ob = _get_orderbook(market_id)
    position = ob.get_position(agent_id)
    
    return PositionResponse(
        agent_id=position.agent_id,
        market_id=position.market_id,
        yes_quantity=position.yes_quantity,
        no_quantity=position.no_quantity,
        net_position=position.net_position,
        avg_yes_price=position.avg_yes_price,
        avg_no_price=position.avg_no_price,
        realized_pnl=position.realized_pnl,
    )


@router.get("/{market_id}/positions", response_model=List[PositionResponse])
async def list_positions(market_id: str):
    """List all positions in a market."""
    ob = _get_orderbook(market_id)
    
    return [
        PositionResponse(
            agent_id=pos.agent_id,
            market_id=pos.market_id,
            yes_quantity=pos.yes_quantity,
            no_quantity=pos.no_quantity,
            net_position=pos.net_position,
            avg_yes_price=pos.avg_yes_price,
            avg_no_price=pos.avg_no_price,
            realized_pnl=pos.realized_pnl,
        )
        for pos in ob.positions.values()
    ]


@router.get("/{market_id}/trades", response_model=List[TradeResponse])
async def list_trades(market_id: str, limit: int = 50):
    """Get recent trades in a market."""
    ob = _get_orderbook(market_id)
    
    trades = ob.trades[-limit:][::-1]  # Most recent first
    
    return [
        TradeResponse(
            id=t.id,
            market_id=t.market_id,
            buyer_agent_id=t.buyer_agent_id,
            seller_agent_id=t.seller_agent_id,
            price=t.price,
            quantity=t.quantity,
            created_at=t.created_at,
        )
        for t in trades
    ]


# ============ Agent Endpoints ============

@router.get("/agents/{agent_id}/orders", response_model=List[OrderResponse])
async def get_agent_orders(agent_id: str, active_only: bool = True):
    """Get all orders for an agent across all markets."""
    all_orders = []
    
    for ob in orderbooks.values():
        orders = ob.get_agent_orders(agent_id, active_only=active_only)
        all_orders.extend(orders)
    
    return [_order_to_response(o) for o in all_orders]


@router.get("/agents/{agent_id}/positions", response_model=List[PositionResponse])
async def get_agent_positions(agent_id: str):
    """Get all positions for an agent across all markets."""
    positions = []
    
    for ob in orderbooks.values():
        if agent_id in ob.positions:
            pos = ob.positions[agent_id]
            positions.append(PositionResponse(
                agent_id=pos.agent_id,
                market_id=pos.market_id,
                yes_quantity=pos.yes_quantity,
                no_quantity=pos.no_quantity,
                net_position=pos.net_position,
                avg_yes_price=pos.avg_yes_price,
                avg_no_price=pos.avg_no_price,
                realized_pnl=pos.realized_pnl,
            ))
    
    return positions

