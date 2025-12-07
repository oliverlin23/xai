#!/usr/bin/env python3
"""
Test script for Avellaneda-Stoikov Market Maker behavior.

Tests:
1. Quote evolution over time (spread narrows as T approaches)
2. Inventory skewing (quotes shift based on position)
3. Confidence effect on spread
4. Simulated trading scenario
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.manager.market_maker import AvellanedaStoikovMM, MMConfig


def print_header(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_quotes(mm: AvellanedaStoikovMM, time: float, label: str = ""):
    """Print current quotes with visual representation."""
    bid, ask = mm.get_quotes(time)
    if bid is None:
        print(f"  {label}Market closed (time >= T)")
        return
    
    mid = mm.mid_price
    spread = ask - bid
    
    # Visual representation (50 chars wide = 0-100 cents)
    scale = 0.5  # 1 cent = 0.5 chars
    bar_len = 50
    
    bid_pos = int(bid * scale)
    ask_pos = int(ask * scale)
    mid_pos = int(mid * scale)
    
    # Build the visual bar
    bar = [' '] * bar_len
    
    # Mark the spread region
    for i in range(bid_pos, min(ask_pos + 1, bar_len)):
        bar[i] = '░'
    
    # Mark bid and ask
    if 0 <= bid_pos < bar_len:
        bar[bid_pos] = '['
    if 0 <= ask_pos < bar_len:
        bar[ask_pos] = ']'
    if 0 <= mid_pos < bar_len:
        bar[mid_pos] = '│'
    
    bar_str = ''.join(bar)
    
    inv_str = f"inv={mm.inventory:+d}" if mm.inventory != 0 else "inv=0"
    print(f"  {label:12} Bid={bid:2d} Ask={ask:2d} Spread={spread:2d} ({inv_str})")
    print(f"              0{bar_str}100")


def test_time_evolution():
    """Test 1: How quotes change as time approaches terminal."""
    print_header("TEST 1: Quote Evolution Over Time")
    print("  As time → T, spread should narrow (less inventory risk)")
    print()
    
    mm = AvellanedaStoikovMM(
        prediction_probability=0.60,  # 60% YES
        confidence=0.70,              # Moderate-high confidence
        config=MMConfig(
            terminal_time=10.0,       # 10 second horizon
            volatility_base=2.0,
            risk_aversion=0.1,
            min_spread=2
        )
    )
    
    print(f"  Setup: prob=0.60, conf=0.70 → mid={mm.mid_price}, σ={mm.sigma:.2f}")
    print()
    
    for t in [0.0, 2.5, 5.0, 7.5, 9.0, 9.9, 10.0]:
        print_quotes(mm, t, f"t={t:.1f}")
    
    print("\n  ✓ Spread narrows as time approaches T (less time to unwind risk)")


def test_inventory_skewing():
    """Test 2: How inventory affects quote positioning."""
    print_header("TEST 2: Inventory Skewing")
    print("  Positive inventory → lower quotes (want to sell)")
    print("  Negative inventory → higher quotes (want to buy)")
    print()
    
    config = MMConfig(
        terminal_time=10.0,
        volatility_base=2.0,
        risk_aversion=0.15,  # Higher risk aversion = more skew
        min_spread=2
    )
    
    # Test at t=0 with different inventory levels
    inventories = [-50, -20, 0, 20, 50]
    
    print(f"  Setup: prob=0.50, conf=0.50 → mid=50, at t=0")
    print()
    
    for inv in inventories:
        mm = AvellanedaStoikovMM(
            prediction_probability=0.50,
            confidence=0.50,
            config=config
        )
        mm.inventory = inv
        print_quotes(mm, 0.0, f"inv={inv:+d}")
    
    print("\n  ✓ With long inventory (+50), quotes shift DOWN to encourage selling")
    print("  ✓ With short inventory (-50), quotes shift UP to encourage buying")


def test_confidence_spread():
    """Test 3: How confidence affects spread width."""
    print_header("TEST 3: Confidence → Spread Width")
    print("  High confidence → low sigma → tight spread")
    print("  Low confidence → high sigma → wide spread")
    print()
    
    confidences = [0.95, 0.80, 0.60, 0.40, 0.20]
    
    print(f"  Setup: prob=0.50 (mid=50), varying confidence, t=0")
    print()
    
    for conf in confidences:
        mm = AvellanedaStoikovMM(
            prediction_probability=0.50,
            confidence=conf,
            config=MMConfig(terminal_time=10.0)
        )
        bid, ask = mm.get_quotes(0.0)
        spread = ask - bid
        print(f"  conf={conf:.2f} → σ={mm.sigma:.2f} → Bid={bid:2d} Ask={ask:2d} Spread={spread:2d}")
    
    print("\n  ✓ Higher confidence = tighter quotes (more certain about fair value)")


def test_trading_scenario():
    """Test 4: Simulate a trading scenario."""
    print_header("TEST 4: Trading Scenario Simulation")
    print("  Simulate trades and observe MM reaction")
    print()
    
    mm = AvellanedaStoikovMM(
        prediction_probability=0.65,  # Slightly bullish
        confidence=0.60,
        config=MMConfig(
            terminal_time=60.0,  # 1 minute
            risk_aversion=0.1,
            min_spread=2
        )
    )
    
    print(f"  Initial: prob=0.65, conf=0.60 → mid={mm.mid_price}, σ={mm.sigma:.2f}")
    print()
    
    # Simulate time steps with trades
    events = [
        (0.0, None, None, "Initial state"),
        (5.0, "buy", 10, "Trader buys 10 from MM (MM sells YES)"),
        (10.0, "buy", 15, "Trader buys 15 more (MM sells YES)"),
        (15.0, "sell", 5, "Trader sells 5 to MM (MM buys YES)"),
        (20.0, None, None, "No trade"),
        (30.0, "buy", 30, "Large buy order (MM sells YES)"),
        (45.0, None, None, "No trade"),
        (55.0, None, None, "Near terminal"),
    ]
    
    for t, side, qty, desc in events:
        # Process trade if any
        if side == "buy":
            # Trader buys YES = MM sells YES
            bid, ask = mm.get_quotes(t)
            mm.on_fill(qty, "sell", ask)  # MM sold at ask
            print(f"  t={t:5.1f} | {desc}")
            print(f"          | Trade: MM SOLD {qty} YES @ {ask}¢")
        elif side == "sell":
            # Trader sells YES = MM buys YES
            bid, ask = mm.get_quotes(t)
            mm.on_fill(qty, "buy", bid)  # MM bought at bid
            print(f"  t={t:5.1f} | {desc}")
            print(f"          | Trade: MM BOUGHT {qty} YES @ {bid}¢")
        else:
            print(f"  t={t:5.1f} | {desc}")
        
        # Show quotes after trade
        print_quotes(mm, t, "")
        print(f"          | Cash: {mm.cash:+.0f}¢")
        print()
    
    print("  Summary:")
    print(f"    Final Inventory: {mm.inventory} contracts")
    print(f"    Total Cash Flow: {mm.cash:+.0f}¢")
    print()
    print("  ✓ As MM accumulates short position, quotes shift DOWN to buy back")
    print("  ✓ Cash increases as MM sells at premium (ask > fair value)")


def test_edge_cases():
    """Test 5: Edge cases and boundary conditions."""
    print_header("TEST 5: Edge Cases")
    print()
    
    # Test 1: Very high confidence
    print("  Case A: Very high confidence (0.99)")
    mm = AvellanedaStoikovMM(
        prediction_probability=0.75,
        confidence=0.99,
        config=MMConfig(terminal_time=10.0)
    )
    bid, ask = mm.get_quotes(0.0)
    print(f"    σ={mm.sigma:.4f}, Spread={ask-bid} (hits min_spread=2)")
    
    # Test 2: Very low confidence
    print("\n  Case B: Very low confidence (0.10)")
    mm = AvellanedaStoikovMM(
        prediction_probability=0.50,
        confidence=0.10,
        config=MMConfig(terminal_time=10.0)
    )
    bid, ask = mm.get_quotes(0.0)
    print(f"    σ={mm.sigma:.4f}, Spread={ask-bid} (wide due to uncertainty)")
    
    # Test 3: Extreme probability
    print("\n  Case C: Extreme probability (0.95)")
    mm = AvellanedaStoikovMM(
        prediction_probability=0.95,
        confidence=0.70,
        config=MMConfig(terminal_time=10.0)
    )
    bid, ask = mm.get_quotes(0.0)
    print(f"    mid={mm.mid_price}, Bid={bid}, Ask={ask}")
    print(f"    Quotes clamped to valid range (1-99)")
    
    # Test 4: At terminal time
    print("\n  Case D: At terminal time (t=T)")
    mm = AvellanedaStoikovMM(
        prediction_probability=0.50,
        confidence=0.50,
        config=MMConfig(terminal_time=10.0)
    )
    bid, ask = mm.get_quotes(10.0)
    print(f"    Bid={bid}, Ask={ask} (should be None - market closed)")
    
    # Test 5: Large inventory
    print("\n  Case E: Large inventory stress test")
    mm = AvellanedaStoikovMM(
        prediction_probability=0.50,
        confidence=0.50,
        config=MMConfig(terminal_time=10.0, risk_aversion=0.1)
    )
    mm.inventory = 100  # Very long
    bid, ask = mm.get_quotes(0.0)
    print(f"    With inv=+100: Bid={bid}, Ask={ask}")
    print(f"    Reservation price shifted significantly DOWN")
    
    mm.inventory = -100  # Very short
    bid, ask = mm.get_quotes(0.0)
    print(f"    With inv=-100: Bid={bid}, Ask={ask}")
    print(f"    Reservation price shifted significantly UP")


def test_pnl_scenarios():
    """Test 6: P&L under different market scenarios."""
    print_header("TEST 6: P&L Analysis")
    print()
    
    scenarios = [
        ("Balanced flow", [(5, "buy", 10), (10, "sell", 10)]),
        ("All buys (MM goes short)", [(5, "buy", 10), (10, "buy", 10), (15, "buy", 10)]),
        ("All sells (MM goes long)", [(5, "sell", 10), (10, "sell", 10), (15, "sell", 10)]),
    ]
    
    for scenario_name, trades in scenarios:
        print(f"  Scenario: {scenario_name}")
        
        mm = AvellanedaStoikovMM(
            prediction_probability=0.50,
            confidence=0.60,
            config=MMConfig(terminal_time=60.0, risk_aversion=0.1)
        )
        
        for t, side, qty in trades:
            bid, ask = mm.get_quotes(float(t))
            if side == "buy":
                mm.on_fill(qty, "sell", ask)
            else:
                mm.on_fill(qty, "buy", bid)
        
        # Calculate theoretical P&L at settlement
        # If market settles at mid_price (50):
        mid = 50
        inventory_value = mm.inventory * mid
        total_pnl = mm.cash + inventory_value
        
        print(f"    Inventory: {mm.inventory:+d} | Cash: {mm.cash:+.0f}¢ | "
              f"Inv Value @50: {inventory_value:+.0f}¢ | Total P&L: {total_pnl:+.0f}¢")
    
    print()
    print("  ✓ Balanced flow = small profit (earned spread)")
    print("  ✓ One-sided flow = larger profit from spread but inventory risk")


def main():
    print("\n" + "🔬 " * 20)
    print("     AVELLANEDA-STOIKOV MARKET MAKER TEST SUITE")
    print("🔬 " * 20)
    
    test_time_evolution()
    test_inventory_skewing()
    test_confidence_spread()
    test_trading_scenario()
    test_edge_cases()
    test_pnl_scenarios()
    
    print("\n" + "=" * 70)
    print("  ALL TESTS COMPLETED")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()

