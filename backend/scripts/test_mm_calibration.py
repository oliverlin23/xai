#!/usr/bin/env python3
"""
Calibration test for Market Maker parameters in prediction markets.

Goal: Find reasonable parameters such that:
- High confidence (0.9) → tight spread (2-4 cents)
- Low confidence (0.3) → wide spread (8-12 cents)
- Inventory of ±30 → quotes shift by ~10-15 cents (NOT hit bounds!)
- Time decay is visible over simulation horizon
"""

import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.manager.market_maker import AvellanedaStoikovMM, MMConfig


def print_header(title: str):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def analyze_config(name: str, config: MMConfig, prob: float = 0.50):
    """Analyze how a config behaves across confidence levels."""
    print(f"\n  Config: {name}")
    print(f"  γ={config.risk_aversion}, k={config.liquidity_param}, "
          f"σ_base={config.volatility_base}, min_spread={config.min_spread}")
    print(f"  Mid price: {prob * 100:.0f} cents")
    print()
    
    # Header
    print(f"  {'Conf':>6} | {'σ':>5} | {'Spread':>6} | {'Inv+30':>7} | {'Inv-30':>7} | {'Shift':>6}")
    print(f"  {'-'*6} | {'-'*5} | {'-'*6} | {'-'*7} | {'-'*7} | {'-'*6}")
    
    for conf in [0.90, 0.70, 0.50, 0.30]:
        # Create MM at specified prob
        mm = AvellanedaStoikovMM(
            prediction_probability=prob,
            confidence=conf,
            config=config
        )
        
        # Get spread at t=0
        bid, ask = mm.get_quotes(0.0)
        spread = ask - bid if bid and ask else 0
        mid = (bid + ask) / 2 if bid and ask else prob * 100
        
        # Calculate quotes with +30 inventory
        mm_long = AvellanedaStoikovMM(
            prediction_probability=prob,
            confidence=conf,
            config=config
        )
        mm_long.inventory = 30
        bid_long, ask_long = mm_long.get_quotes(0.0)
        mid_long = (bid_long + ask_long) / 2 if bid_long and ask_long else 0
        
        # Calculate quotes with -30 inventory
        mm_short = AvellanedaStoikovMM(
            prediction_probability=prob,
            confidence=conf,
            config=config
        )
        mm_short.inventory = -30
        bid_short, ask_short = mm_short.get_quotes(0.0)
        mid_short = (bid_short + ask_short) / 2 if bid_short and ask_short else 0
        
        # Shift is difference in midpoints
        shift = mid_short - mid_long if mid_long and mid_short else 0
        
        print(f"  {conf:>6.2f} | {mm.sigma:>5.2f} | {spread:>6} | "
              f"{mid_long:>7.0f} | {mid_short:>7.0f} | {shift:>+6.0f}")


def test_configs():
    print_header("PARAMETER CALIBRATION FOR PREDICTION MARKETS")
    print("""
  Target behavior:
  - Confidence 0.9 → Spread 2-4 cents
  - Confidence 0.5 → Spread 4-8 cents  
  - Confidence 0.3 → Spread 8-15 cents
  - Inventory ±30 → Mid shifts by ~10-20 cents total (not to bounds!)
  """)
    
    # Config 1: Current defaults (inventory effect too strong)
    config_current = MMConfig(
        risk_aversion=0.1,
        liquidity_param=0.5,
        terminal_time=60.0,
        volatility_base=2.0,
        min_spread=2
    )
    analyze_config("CURRENT (inventory too aggressive)", config_current)
    
    # Config 2: Much lower risk aversion
    config_v1 = MMConfig(
        risk_aversion=0.001,     # 100x lower!
        liquidity_param=1.0,
        terminal_time=60.0,
        volatility_base=5.0,
        min_spread=1
    )
    analyze_config("V1: Very low γ=0.001", config_v1)
    
    # Config 3: Balance with higher k
    config_v2 = MMConfig(
        risk_aversion=0.002,
        liquidity_param=1.5,
        terminal_time=60.0,
        volatility_base=4.0,
        min_spread=1
    )
    analyze_config("V2: γ=0.002, k=1.5, σ_base=4", config_v2)
    
    # Config 4: Calibrated for realistic behavior
    config_recommended = MMConfig(
        risk_aversion=0.003,
        liquidity_param=1.2,
        terminal_time=60.0,
        volatility_base=3.5,
        min_spread=2
    )
    analyze_config("RECOMMENDED: γ=0.003, k=1.2, σ_base=3.5", config_recommended)


def test_inventory_visual():
    print_header("INVENTORY DYNAMICS VISUALIZATION")
    print("  Using recommended config at prob=0.60, conf=0.50")
    print()
    
    config = MMConfig(
        risk_aversion=0.003,
        liquidity_param=1.2,
        terminal_time=60.0,
        volatility_base=3.5,
        min_spread=2
    )
    
    prob = 0.60
    mid_base = prob * 100  # 60
    
    print(f"  Fair value (mid): {mid_base:.0f} cents")
    print()
    print(f"  {'Inv':>5} | {'Bid':>4} | {'Ask':>4} | {'Mid':>5} | {'Shift':>6} | Visual (40-80 range)")
    print(f"  {'-'*5} | {'-'*4} | {'-'*4} | {'-'*5} | {'-'*6} | {'-'*40}")
    
    for inv in [-50, -40, -30, -20, -10, 0, 10, 20, 30, 40, 50]:
        mm = AvellanedaStoikovMM(
            prediction_probability=prob,
            confidence=0.50,
            config=config
        )
        mm.inventory = inv
        
        bid, ask = mm.get_quotes(0.0)
        if bid and ask:
            mid = (bid + ask) / 2
            shift = mid - mid_base
            
            # Visual: 40 chars representing price range 40-80
            bar = [' '] * 40
            scale = lambda p: int((p - 40))  # 40->0, 60->20, 80->40
            
            mid_pos = scale(mid_base)
            bid_pos = scale(bid)
            ask_pos = scale(ask)
            
            # Clamp to valid range
            mid_pos = max(0, min(39, mid_pos))
            bid_pos = max(0, min(39, bid_pos))
            ask_pos = max(0, min(39, ask_pos))
            
            # Draw
            bar[mid_pos] = '│'  # Fair value marker
            for i in range(bid_pos, ask_pos + 1):
                if 0 <= i < 40 and bar[i] == ' ':
                    bar[i] = '░'
            if 0 <= bid_pos < 40:
                bar[bid_pos] = '['
            if 0 <= ask_pos < 40:
                bar[ask_pos] = ']'
            
            bar_str = ''.join(bar)
            print(f"  {inv:>+5} | {bid:>4} | {ask:>4} | {mid:>5.0f} | {shift:>+6.0f} | {bar_str}")
        else:
            print(f"  {inv:>+5} | Market closed")


def test_confidence_spread():
    print_header("CONFIDENCE vs SPREAD (Recommended Config)")
    print("  How spread varies with forecast confidence")
    print()
    
    config = MMConfig(
        risk_aversion=0.003,
        liquidity_param=1.2,
        terminal_time=60.0,
        volatility_base=3.5,
        min_spread=2
    )
    
    print(f"  {'Conf':>6} | {'σ':>5} | {'Spread':>6} | Visual")
    print(f"  {'-'*6} | {'-'*5} | {'-'*6} | {'-'*20}")
    
    for conf in [0.95, 0.85, 0.75, 0.65, 0.55, 0.45, 0.35, 0.25, 0.15]:
        mm = AvellanedaStoikovMM(
            prediction_probability=0.50,
            confidence=conf,
            config=config
        )
        
        bid, ask = mm.get_quotes(0.0)
        spread = ask - bid if bid and ask else 0
        
        bar = "█" * min(spread, 20)
        print(f"  {conf:>6.2f} | {mm.sigma:>5.2f} | {spread:>6} | {bar}")


def test_time_decay():
    print_header("TIME DECAY (Recommended Config)")
    print("  How spread narrows as t approaches T")
    print()
    
    config = MMConfig(
        risk_aversion=0.003,
        liquidity_param=1.2,
        terminal_time=60.0,
        volatility_base=3.5,
        min_spread=2
    )
    
    mm = AvellanedaStoikovMM(
        prediction_probability=0.50,
        confidence=0.50,
        config=config
    )
    
    print(f"  Setup: prob=0.50, conf=0.50, σ={mm.sigma:.2f}")
    print()
    
    print(f"  {'Time':>6} | {'T-t':>5} | {'Bid':>4} | {'Ask':>4} | {'Spread':>6}")
    print(f"  {'-'*6} | {'-'*5} | {'-'*4} | {'-'*4} | {'-'*6}")
    
    for t in [0, 10, 20, 30, 40, 50, 55, 58, 59, 60]:
        bid, ask = mm.get_quotes(float(t))
        if bid and ask:
            spread = ask - bid
            remaining = config.terminal_time - t
            print(f"  {t:>6} | {remaining:>5.0f} | {bid:>4} | {ask:>4} | {spread:>6}")
        else:
            print(f"  {t:>6} | {'0':>5} | {'--':>4} | {'--':>4} | CLOSED")


def show_final_recommendation():
    print_header("FINAL RECOMMENDED CONFIGURATION")
    print("""
  After calibration, the recommended parameters for prediction markets:
  
  ```python
  MMConfig(
      risk_aversion = 0.003,      # γ: Controls inventory skew strength
      liquidity_param = 1.2,      # k: Controls base spread width
      terminal_time = 60.0,       # T: Simulation horizon (seconds)
      volatility_base = 3.5,      # σ_base: Spread sensitivity to confidence
      min_spread = 2,             # Minimum spread (cents)
      max_inventory = 100         # Position limit
  )
  ```
  
  Resulting behavior:
  ┌────────────┬─────────┬────────────────────────────────┐
  │ Confidence │ Spread  │ Description                    │
  ├────────────┼─────────┼────────────────────────────────┤
  │   0.90     │  2-3¢   │ Very certain - tight quotes    │
  │   0.70     │  3-4¢   │ Confident - moderate spread    │
  │   0.50     │  5-6¢   │ Uncertain - wider spread       │
  │   0.30     │  8-10¢  │ Low confidence - wide spread   │
  └────────────┴─────────┴────────────────────────────────┘
  
  Inventory dynamics (at conf=0.50):
  ┌───────────┬────────────────────────────────────────────┐
  │ Inventory │ Quote Shift                                │
  ├───────────┼────────────────────────────────────────────┤
  │   ±10     │ ~3-5 cents from mid                        │
  │   ±30     │ ~10-15 cents from mid                      │
  │   ±50     │ ~15-25 cents from mid (approaches bounds)  │
  └───────────┴────────────────────────────────────────────┘
  
  These parameters produce realistic prediction market dynamics.
  """)


def main():
    print("\n🎯 " * 15)
    print("  MARKET MAKER PARAMETER CALIBRATION v2")
    print("🎯 " * 15)
    
    test_configs()
    test_inventory_visual()
    test_confidence_spread()
    test_time_decay()
    show_final_recommendation()
    
    print("\n" + "=" * 70)
    print("  CALIBRATION COMPLETE")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
