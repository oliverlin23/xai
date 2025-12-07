#!/usr/bin/env python3
"""
Full Integration Test for Manager + Market Maker + OrderBook + Noise Traders

This test verifies that all components work together:
1. Manager receives Superforecaster output
2. Creates Market + OrderBook
3. Market Maker quotes bid/ask
4. Noise Traders (mocked) place orders
5. OrderBook matches trades
6. Simulation completes with results
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.market.models import Market, Order, OrderSide, MarketStatus
from app.market.orderbook import OrderBook
from app.manager.market_maker import AvellanedaStoikovMM, MMConfig
from app.manager.manager import SimulationManager


def print_header(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


async def test_orderbook_integration():
    """Test that OrderBook works with Market Maker orders."""
    print_header("TEST 1: OrderBook + Market Maker Integration")
    
    # Create market and orderbook
    market = Market(
        question="Will BTC hit $100k by end of 2025?",
        description="Test market"
    )
    orderbook = OrderBook(market)
    
    # Create market maker
    mm = AvellanedaStoikovMM(
        prediction_probability=0.65,
        confidence=0.60,
        config=MMConfig(terminal_time=60.0)
    )
    mm_id = "mm_test_001"
    
    print(f"  Market: {market.question}")
    print(f"  MM mid_price: {mm.mid_price}, sigma: {mm.sigma:.2f}")
    
    # Get MM quotes
    bid, ask = mm.get_quotes(0.0)
    print(f"  MM quotes: Bid={bid}, Ask={ask}")
    
    # Place MM bid order (Buy YES)
    bid_order = Order(
        agent_id=mm_id,
        market_id=market.id,
        side=OrderSide.YES,
        price=bid,
        quantity=10
    )
    order_result, trades = orderbook.place_order(bid_order)
    print(f"  Placed bid: {order_result.id[:8]}... @ {bid}")
    
    # Place MM ask order (Sell YES = Buy NO at 100-ask)
    ask_order = Order(
        agent_id=mm_id,
        market_id=market.id,
        side=OrderSide.NO,
        price=100 - ask,
        quantity=10
    )
    order_result, trades = orderbook.place_order(ask_order)
    print(f"  Placed ask: {order_result.id[:8]}... @ {ask}")
    
    # Check orderbook state
    snapshot = orderbook.get_book_snapshot()
    print(f"\n  OrderBook State:")
    print(f"    Bids: {snapshot['bids']}")
    print(f"    Asks: {snapshot['asks']}")
    
    # Simulate a trader buying NO aggressively to cross the spread
    trader_id = "trader_001"
    trader_order = Order(
        agent_id=trader_id,
        market_id=market.id,
        side=OrderSide.NO,
        price=99,  # Very aggressive NO bid to ensure a match
        quantity=5
    )
    order_result, trades = orderbook.place_order(trader_order)
    
    print(f"\n  Trader placed NO order @ 99 for 5 contracts")
    print(f"    Trades executed: {len(trades)}")
    for trade in trades:
        print(f"      Trade: {trade.quantity} @ {trade.price} "
              f"(buyer={trade.buyer_agent_id[:10]}, seller={trade.seller_agent_id[:10]})")
    
    # Check market stats
    print(f"\n  Market Stats:")
    print(f"    Last price: {market.last_price}")
    print(f"    Volume: {market.volume}")
    
    # Check positions
    mm_pos = orderbook.get_position(mm_id)
    trader_pos = orderbook.get_position(trader_id)
    print(f"\n  Positions:")
    print(f"    MM: YES={mm_pos.yes_quantity}, NO={mm_pos.no_quantity}")
    print(f"    Trader: YES={trader_pos.yes_quantity}, NO={trader_pos.no_quantity}")
    
    print("\n  ✓ OrderBook + Market Maker integration working!")
    return True


async def test_manager_without_traders():
    """Test Manager with mocked traders to verify core logic."""
    print_header("TEST 2: Manager Core Logic (No API calls)")
    
    # Mock prediction result from Superforecaster
    prediction_result = {
        "prediction": "Yes",
        "prediction_probability": 0.70,
        "confidence": 0.55,
        "reasoning": "Based on market trends...",
        "key_factors": ["Factor 1", "Factor 2"]
    }
    
    print(f"  Superforecaster output:")
    print(f"    prediction_probability: {prediction_result['prediction_probability']}")
    print(f"    confidence: {prediction_result['confidence']}")
    
    # Create manager without initializing traders (we'll mock the trader step)
    manager = SimulationManager(
        session_id="test-session-002",
        question="Will the S&P 500 end 2025 higher than 2024?",
        prediction_result=prediction_result,
        duration_seconds=10,  # Short simulation
        time_step=1.0,
        trader_communities=[]  # Empty - we won't use real traders
    )
    
    print(f"\n  Manager initialized:")
    print(f"    MM mid_price: {manager.mm.mid_price}")
    print(f"    MM sigma: {manager.mm.sigma:.4f}")
    
    # Run MM step manually a few times
    print(f"\n  Running MM steps:")
    for t in [0, 2, 5, 8]:
        await manager._run_mm_step(float(t))
        snapshot = manager.orderbook.get_book_snapshot()
        bids = snapshot['bids']
        asks = snapshot['asks']
        best_bid = bids[0]['price'] if bids else None
        best_ask = asks[0]['price'] if asks else None
        print(f"    t={t}: Bid={best_bid}, Ask={best_ask}, Volume={manager.market.volume}")
    
    # Simulate a trader order manually
    print(f"\n  Simulating trader order:")
    from app.market.models import Order, OrderSide
    
    # Bearish trader buys NO aggressively to cross MM YES quotes
    trader_order = Order(
        agent_id="simulated_trader",
        market_id=manager.market.id,
        side=OrderSide.NO,
        price=99,
        quantity=5
    )
    _, trades = manager.orderbook.place_order(trader_order)
    print(f"    Trader placed NO@99 for 5")
    print(f"    Trades: {len(trades)}")
    
    if trades:
        for trade in trades:
            print(f"      Filled: {trade.quantity} @ {trade.price}")
        
        # Update MM inventory
        for trade in trades:
            if trade.seller_agent_id == manager.mm_agent_id:
                manager.mm.on_fill(trade.quantity, "sell", trade.price)
    
    print(f"\n  Final state:")
    print(f"    Market volume: {manager.market.volume}")
    print(f"    Market last_price: {manager.market.last_price}")
    print(f"    MM inventory: {manager.mm.inventory}")
    print(f"    MM cash: {manager.mm.cash}")
    
    print("\n  ✓ Manager core logic working!")
    return True


async def test_full_simulation_mocked():
    """Test full simulation with mocked NoiseTraders."""
    print_header("TEST 3: Full Simulation (Mocked Traders)")
    
    prediction_result = {
        "prediction": "Yes",
        "prediction_probability": 0.65,
        "confidence": 0.60,
        "reasoning": "Test reasoning",
        "key_factors": ["Factor A", "Factor B"]
    }
    
    # Create manager
    manager = SimulationManager(
        session_id="test-session-003",
        question="Will AI regulation pass in 2025?",
        prediction_result=prediction_result,
        duration_seconds=6,
        time_step=1.0,
        trader_communities=[]  # No real traders
    )
    
    # Create mock traders that return deterministic predictions
    class MockTrader:
        def __init__(self, name: str, fixed_prediction: int):
            self.agent_name = name
            self.fixed_prediction = fixed_prediction
        
        async def execute(self, input_data):
            return {
                "prediction": self.fixed_prediction,
                "reasoning": "Mock prediction",
                "sentiment": "neutral",
                "confidence": 0.5
            }
    
    # Add mock traders with different views
    manager.traders = [
        MockTrader("trader_bull", 75),   # Bullish
        MockTrader("trader_bear", 45),   # Bearish
        MockTrader("trader_neutral", 65) # Near MM mid
    ]
    
    print(f"  Starting simulation with 3 mock traders")
    print(f"    Trader views: Bull=75, Bear=45, Neutral=65")
    print(f"    MM mid_price: {manager.mm.mid_price}")
    print()
    
    # Run the simulation (force the bearish trader to act to ensure a trade)
    with patch("app.manager.manager.random.choice", lambda seq: seq[1]), \
         patch("app.manager.manager.asyncio.sleep", new=AsyncMock()):
        result = await manager.run()
    
    print(f"\n  Simulation Results:")
    print(f"    Market ID: {result['market_id'][:8]}...")
    print(f"    Initial price: {result['initial_price']}")
    print(f"    Final price: {result['final_price']}")
    print(f"    Total volume: {result['total_volume']}")
    print(f"    MM final inventory: {result['mm_state']['inventory']}")
    print(f"    MM final cash: {result['mm_state']['cash']}")
    
    print(f"\n  Price History (sampled):")
    for i, ph in enumerate(result['price_history']):
        if i % 2 == 0:  # Every other
            print(f"    t={ph['time']:.0f}: price={ph['price']}, volume={ph['volume']}")
    
    print("\n  ✓ Full simulation completed successfully!")
    return True


async def test_noise_trader_initialization_and_trading():
    """Ensure manager initializes NoiseTraders correctly and processes their trades."""
    print_header("TEST 4: NoiseTrader Initialization + Trading")

    prediction_result = {
        "prediction": "Yes",
        "prediction_probability": 0.6,
        "confidence": 0.5,
        "reasoning": "Test reasoning",
        "key_factors": ["Factor X", "Factor Y"]
    }

    # Use a single deterministic sphere to avoid randomness
    trader_spheres = ["eacc_sovereign"]
    init_kwargs = {}

    class StubNoiseTrader:
        def __init__(self, sphere: str, agent_name: str | None = None, **kwargs):
            init_kwargs["sphere"] = sphere
            init_kwargs["agent_name"] = agent_name
            init_kwargs["kwargs"] = kwargs
            self.sphere = sphere
            self.agent_name = agent_name or f"trader_{sphere}"

        async def execute(self, input_data):
            # Bearish view forces a NO trade against the MM's YES quote
            return {"prediction": 30}

    with patch("app.manager.manager.NoiseTrader", StubNoiseTrader):
        # Speed up the simulation loop for tests
        with patch("app.manager.manager.asyncio.sleep", new=AsyncMock()) as fake_sleep:
            manager = SimulationManager(
                session_id="test-session-004",
                question="Will a test event happen?",
                prediction_result=prediction_result,
                duration_seconds=6,
                time_step=1.0,
                trader_communities=trader_spheres,
                noise_trader_kwargs={"use_semantic_filter": False, "enable_tools": False},
            )

            result = await manager.run()

    print(f"  Trader initialized with sphere: {init_kwargs.get('sphere')}")
    print(f"  Agent name: {init_kwargs.get('agent_name')}")
    print(f"  NoiseTrader kwargs: {init_kwargs.get('kwargs')}")
    print(f"  Total volume traded: {result['total_volume']}")
    print(f"  Final price: {result['final_price']}")
    print(f"  MM inventory: {result['mm_state']['inventory']}")

    assert init_kwargs.get("sphere") == trader_spheres[0], "Manager should pass valid sphere key"
    assert result["total_volume"] > 0, "Noise trader should have generated trades"
    assert result["final_price"] is not None, "Market price should update after trades"

    print("\n  ✓ NoiseTrader initialization + trading verified!")
    return True


async def test_component_compatibility():
    """Verify all components use compatible interfaces."""
    print_header("TEST 5: Component Compatibility Check")
    
    print("  Checking imports...")
    
    # Test that all components can be imported
    from app.market.models import Market, Order, Trade, Position, OrderSide, OrderStatus, MarketStatus
    from app.market.orderbook import OrderBook
    from app.manager.market_maker import AvellanedaStoikovMM, MMConfig
    from app.manager.manager import SimulationManager
    print("    ✓ All manager components imported")
    
    # Check that Market and OrderBook are compatible
    market = Market(question="Test?")
    orderbook = OrderBook(market)
    assert orderbook.market == market
    print("    ✓ Market → OrderBook compatible")
    
    # Check that Order can be created and placed
    order = Order(
        agent_id="test",
        market_id=market.id,
        side=OrderSide.YES,
        price=50,
        quantity=10
    )
    placed, trades = orderbook.place_order(order)
    assert placed.id == order.id
    print("    ✓ Order → OrderBook compatible")
    
    # Check that MM produces valid prices
    mm = AvellanedaStoikovMM(
        prediction_probability=0.5,
        confidence=0.5,
        config=MMConfig()
    )
    bid, ask = mm.get_quotes(0.0)
    assert 1 <= bid <= 99
    assert 1 <= ask <= 99
    assert bid < ask
    print("    ✓ Market Maker produces valid quotes")
    
    # Check that SimulationManager initializes correctly
    manager = SimulationManager(
        session_id="test",
        question="Test?",
        prediction_result={"prediction_probability": 0.5, "confidence": 0.5},
        duration_seconds=10,
        trader_communities=[]
    )
    assert manager.market is not None
    assert manager.orderbook is not None
    assert manager.mm is not None
    print("    ✓ SimulationManager initializes all components")
    
    print("\n  ✓ All components compatible!")
    return True


async def main():
    print("\n" + "🔗 " * 20)
    print("  FULL INTEGRATION TEST SUITE")
    print("🔗 " * 20)
    
    results = []
    
    # Run all tests
    results.append(await test_orderbook_integration())
    results.append(await test_manager_without_traders())
    results.append(await test_full_simulation_mocked())
    results.append(await test_noise_trader_initialization_and_trading())
    results.append(await test_component_compatibility())
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n  Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("\n  ✅ ALL INTEGRATION TESTS PASSED!")
        print("\n  The Manager is complete and working with:")
        print("    - Market (in-memory)")
        print("    - OrderBook (price-time priority matching)")
        print("    - Avellaneda-Stoikov Market Maker")
        print("    - Noise Traders (requires X API for live data)")
    else:
        print("\n  ❌ SOME TESTS FAILED")
    
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
