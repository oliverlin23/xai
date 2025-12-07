#!/usr/bin/env python3
"""
Test script for FundamentalTrader prediction market agent

Usage:
    cd backend
    
    # Run ALL trader types and compare predictions (default)
    uv run python scripts/test_fundamental_agent.py
    
    # Run single trader type
    uv run python scripts/test_fundamental_agent.py --type conservative
    uv run python scripts/test_fundamental_agent.py --type momentum
    
    # Custom question
    uv run python scripts/test_fundamental_agent.py --question "Will BTC hit 100k by end of 2025?"
    
    # Continuous polling mode with market-making
    uv run python scripts/test_fundamental_agent.py --type balanced --poll
    uv run python scripts/test_fundamental_agent.py --type balanced --poll --poll-interval 30
    
    # Polling with specific session (for trading)
    uv run python scripts/test_fundamental_agent.py --type balanced --poll --session <uuid>

Requires:
    - GROK_API_KEY in .env (for Grok)
    - SUPABASE_URL and SUPABASE_SERVICE_KEY in .env (for market making)
    
Note: Unlike NoiseTrader, FundamentalTrader does NOT use X API.
      It trades purely on market data and prior reasoning.
"""
import argparse
import asyncio
import logging
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

# Load env from project root
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from app.agents.traders.fundamental_agent import (
    FundamentalTrader,
    FUNDAMENTAL_TRADER_TYPES,
    get_fundamental_trader_names,
)
from app.services.market.client import SupabaseMarketMaker

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Suppress noisy logging
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)
logging.getLogger("app.agents.base").setLevel(logging.WARNING)
logging.getLogger("app.services.grok").setLevel(logging.WARNING)
logging.getLogger("app.agents.traders.fundamental_agent").setLevel(logging.WARNING)


# Sample market data for testing
SAMPLE_MARKET_DATA: Dict[str, object] = {
    "market_topic": "Will the Federal Reserve cut interest rates in December 2025?",
    "resolution_criteria": "Resolves YES if the Federal Reserve announces a rate cut at the December 2025 FOMC meeting.",
    "resolution_date": "December 18, 2025",
    "order_book": {
        "bids": [
            {"quantity": 100, "price": 82},
            {"quantity": 75, "price": 81},
            {"quantity": 50, "price": 80},
        ],
        "asks": [
            {"quantity": 80, "price": 86},
            {"quantity": 60, "price": 87},
            {"quantity": 120, "price": 88},
        ]
    },
    "recent_trades": [
        {"side": "buy", "quantity": 25, "price": 84, "time_ago": "2 min ago"},
        {"side": "sell", "quantity": 15, "price": 83, "time_ago": "5 min ago"},
    ]
}


@dataclass
class TraderResult:
    """Result from a single fundamental trader's prediction"""
    trader_type: str
    prediction: int | None
    signal: str
    analysis: str
    confidence: float
    tokens_used: int
    time_seconds: float
    error: str | None = None


async def run_single_trader(
    trader_type: str,
    market_data: dict,
    previous_notes: str = "",
    round_number: int = 1,
) -> TraderResult:
    """Run a single fundamental trader and return result"""
    import time
    
    start = time.perf_counter()
    
    try:
        trader = FundamentalTrader(
            trader_type=trader_type,
            timeout_seconds=120,
        )
        
        # Add round context
        data = market_data.copy()
        data["previous_notes"] = previous_notes
        data["round_number"] = round_number
        
        result = await trader.execute(data)
        elapsed = time.perf_counter() - start
        
        return TraderResult(
            trader_type=trader_type,
            prediction=result.get("prediction"),
            signal=result.get("signal", "uncertain"),
            analysis=result.get("analysis", "")[:200],
            confidence=result.get("confidence", 0),
            tokens_used=trader.tokens_used,
            time_seconds=elapsed,
        )
        
    except Exception as e:
        elapsed = time.perf_counter() - start
        return TraderResult(
            trader_type=trader_type,
            prediction=None,
            signal="error",
            analysis="",
            confidence=0,
            tokens_used=0,
            time_seconds=elapsed,
            error=str(e),
        )


async def run_all_traders(
    market_data: dict,
    max_concurrent: int = 2,
) -> list[TraderResult]:
    """Run all fundamental trader types with limited concurrency"""
    
    all_types = get_fundamental_trader_names()
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def run_with_semaphore(trader_type: str) -> TraderResult:
        async with semaphore:
            info = FUNDAMENTAL_TRADER_TYPES[trader_type]
            print(f"  🔄 Starting {trader_type} ({info['name']})...")
            result = await run_single_trader(trader_type, market_data)
            if result.error:
                print(f"  ❌ {trader_type}: FAILED - {result.error[:50]}")
            else:
                print(f"  ✅ {trader_type}: {result.prediction}% ({result.time_seconds:.1f}s)")
            return result
    
    tasks = [run_with_semaphore(t) for t in all_types]
    results = await asyncio.gather(*tasks)
    return list(results)


def print_comparison(results: list[TraderResult], question: str):
    """Print comparison of all fundamental trader predictions"""
    
    # Filter successful results
    successful = [r for r in results if r.prediction is not None]
    failed = [r for r in results if r.prediction is None]
    
    if not successful:
        print("\n❌ All traders failed!")
        return
    
    # Sort by prediction
    successful.sort(key=lambda r: r.prediction, reverse=True)
    
    # Calculate stats
    predictions = [r.prediction for r in successful]
    avg_prediction = sum(predictions) / len(predictions)
    min_pred = min(predictions)
    max_pred = max(predictions)
    spread = max_pred - min_pred
    
    print("\n" + "=" * 80)
    print("📊 FUNDAMENTAL TRADER COMPARISON")
    print("=" * 80)
    print(f"Question: {question}")
    print("=" * 80)
    
    # Header
    print(f"\n{'Type':<15} {'Name':<25} {'Pred':>6} {'Signal':<10} {'Conf':>6} {'Time':>6}")
    print("-" * 75)
    
    # Results
    for r in successful:
        name = FUNDAMENTAL_TRADER_TYPES[r.trader_type]["name"]
        print(f"{r.trader_type:<15} {name:<25} {r.prediction:>5}% {r.signal:<10} {r.confidence:>5.0%} {r.time_seconds:>5.1f}s")
    
    # Failed traders
    if failed:
        print("-" * 75)
        for r in failed:
            print(f"{r.trader_type:<15} {'FAILED':<25} {r.error[:40] if r.error else 'Unknown error'}")
    
    # Summary stats
    print("\n" + "=" * 80)
    print("📈 SUMMARY STATISTICS")
    print("=" * 80)
    print(f"  Traders reporting:    {len(successful)}/{len(results)}")
    print(f"  Average prediction:   {avg_prediction:.1f}%")
    print(f"  Range:                {min_pred}% - {max_pred}% (spread: {spread}%)")
    
    # Consensus analysis
    print("\n" + "-" * 40)
    if spread <= 5:
        print(f"  🤝 STRONG CONSENSUS: All traders within {spread}% of each other")
    elif spread <= 15:
        print(f"  📊 MODERATE CONSENSUS: {spread}% spread between extremes")
    else:
        print(f"  ⚔️  DIVERGENT VIEWS: {spread}% spread - traders disagree significantly")
    
    # Token usage
    total_tokens = sum(r.tokens_used for r in results)
    total_time = sum(r.time_seconds for r in results)
    print(f"\n  💰 Total tokens:      {total_tokens:,}")
    print(f"  ⏱️  Total time:        {total_time:.1f}s")
    
    print("=" * 80)


async def run_poll_mode(
    trader_type: str,
    market_data: Dict[str, Any],
    interval_seconds: int = 10,
    session_id: Optional[str] = None,
    spread: int = 4,
    quantity: int = 100,
):
    """
    Continuously poll and trade using fundamental analysis
    
    Args:
        trader_type: Type of fundamental trader (conservative, momentum, etc.)
        market_data: Initial market data dict
        interval_seconds: Seconds between rounds
        session_id: Supabase session ID for trading (optional)
        spread: Market making spread in cents
        quantity: Order quantity
    """
    trader_name = trader_type  # fundamental traders use their type as trader_name
    
    # Initialize market maker if session provided
    market_maker: Optional[SupabaseMarketMaker] = None
    if session_id:
        market_maker = SupabaseMarketMaker()
    
    trader_info = FUNDAMENTAL_TRADER_TYPES[trader_type]
    
    print("\n" + "=" * 70)
    print("🔄 CONTINUOUS POLLING MODE (Fundamental)" + (" (with trading)" if market_maker else ""))
    print("=" * 70)
    print(f"Trader Type: {trader_type}")
    print(f"Trader Name: {trader_info['name']}")
    print(f"Style: {trader_info['style']}")
    print(f"Question: {market_data['market_topic']}")
    if market_maker:
        print(f"Session ID: {session_id}")
        print(f"Market making spread: {spread} (bid @ pred-{spread//2}, ask @ pred+{spread//2})")
        print(f"Order quantity: {quantity}")
    print(f"Poll interval: {interval_seconds}s")
    print("Press Ctrl+C to stop.")
    print("=" * 70)
    
    # Create trader
    trader = FundamentalTrader(
        trader_type=trader_type,
        timeout_seconds=120,
    )
    
    round_number = 1
    previous_notes = ""
    
    try:
        while True:
            start_ts = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{start_ts}] 🔄 Round {round_number}...")
            
            try:
                # Build round data
                round_data = market_data.copy()
                round_data["previous_notes"] = previous_notes
                round_data["round_number"] = round_number
                
                # If we have market maker, fetch live orderbook data
                if market_maker and session_id:
                    orderbook = market_maker.get_orderbook(session_id)
                    recent_trades = market_maker.get_recent_trades(session_id, limit=10)
                    round_data["order_book"] = orderbook
                    round_data["recent_trades"] = recent_trades
                
                # Run prediction
                result = await trader.execute(round_data)
                
                prediction = result.get("prediction", 50)
                signal = result.get("signal", "uncertain")
                confidence = result.get("confidence", 0)
                notes = result.get("notes_for_next_round", "")
                
                print(f"[{start_ts}] 🎯 prediction={prediction}% signal={signal} conf={confidence:.0%}")
                
                # Market making - atomically cancel, place, and match
                if market_maker and session_id:
                    mm_result = market_maker.place_market_making_orders(
                        session_id=session_id,
                        trader_name=trader_name,
                        prediction=prediction,
                        spread=spread,
                        quantity=quantity,
                    )
                    
                    if "error" not in mm_result:
                        bid_price = mm_result.get("bid_price", prediction - spread // 2)
                        ask_price = mm_result.get("ask_price", prediction + spread // 2)
                        print(f"[{start_ts}] 📈 Market making: bid={bid_price}¢ ask={ask_price}¢ qty={quantity}")
                        
                        # Matching happens atomically in the SQL function
                        if mm_result.get("trades_count", 0) > 0:
                            print(f"[{start_ts}] 🔄 Matched {mm_result['trades_count']} trades, volume={mm_result['volume']}")
                    else:
                        print(f"[{start_ts}] ⚠️  Market making failed: {mm_result.get('error')}")
                
                # Print detailed result
                print(json.dumps({
                    "round": round_number,
                    "prediction": prediction,
                    "signal": signal,
                    "confidence": confidence,
                    "analysis": result.get("analysis", "")[:200] + "...",
                    "notes_for_next_round": notes[:200] + "..." if len(notes) > 200 else notes,
                }, indent=2, ensure_ascii=False))
                
                # Save notes for next round
                previous_notes = notes
                round_number += 1
                
            except Exception as e:
                print(f"[{start_ts}] ❌ Round failed: {e}")
                logger.exception("Round failed")
            
            # Wait before next round
            await asyncio.sleep(interval_seconds)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Polling stopped by user.")
    finally:
        # Clean up - cancel any remaining orders
        if market_maker and session_id:
            print(f"🧹 Cleaning up: cancelling orders for {trader_name}...")
            cancelled = market_maker.cancel_all_orders(session_id, trader_name)
            print(f"   Cancelled {cancelled} orders.")


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Test FundamentalTrader prediction agent")
    parser.add_argument(
        "--type", "-t",
        type=str,
        default=None,
        help=f"Trader type to test. Available: {', '.join(get_fundamental_trader_names())}"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Run all trader types and compare predictions"
    )
    parser.add_argument(
        "--question", "-q",
        type=str,
        default=None,
        help="Custom market question (overrides default)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show verbose logging from internal components"
    )
    parser.add_argument(
        "--concurrent", "-c",
        type=int,
        default=2,
        help="Max concurrent trader executions (default: 2)"
    )
    parser.add_argument(
        "--poll",
        action="store_true",
        help="Continuously poll and update predictions",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=10,
        help="Seconds between polls when --poll is used (default: 10)",
    )
    parser.add_argument(
        "--session",
        type=str,
        default=None,
        help="Supabase session ID for market making (enables trading)"
    )
    parser.add_argument(
        "--spread",
        type=int,
        default=4,
        help="Market making spread width in cents (default: 4)"
    )
    parser.add_argument(
        "--quantity",
        type=int,
        default=100,
        help="Order quantity (default: 100)"
    )
    parser.add_argument(
        "--list-types",
        action="store_true",
        help="List all available trader types"
    )
    return parser.parse_args()


async def test_single_type(trader_type: str, market_data: dict):
    """Test a single trader type with verbose output"""
    import time
    
    info = FUNDAMENTAL_TRADER_TYPES[trader_type]
    question = market_data['market_topic']
    
    print("\n" + "=" * 60)
    print(f"FUNDAMENTAL TRADER TEST")
    print("=" * 60)
    print(f"Type: {trader_type}")
    print(f"Name: {info['name']}")
    print(f"Style: {info['style']}")
    print(f"Known Bias: {info['bias']}")
    print(f"Question: {question}")
    print("=" * 60)
    
    # Create trader
    trader = FundamentalTrader(
        trader_type=trader_type,
        timeout_seconds=120,
    )
    
    # Run prediction
    print("\n🧠 GENERATING FORECAST...")
    start = time.perf_counter()
    result = await trader.execute(market_data)
    elapsed = time.perf_counter() - start
    
    print("\n" + "=" * 60)
    print(f"📊 PREDICTION (Type: {trader_type})")
    print("=" * 60)
    
    print(f"\n🎯 PREDICTION: {result['prediction']}%")
    print(f"📡 Signal: {result['signal']}")
    print(f"🔒 Confidence: {result['confidence']:.0%}")
    
    print(f"\n📝 KEY FACTS:")
    for i, fact in enumerate(result.get('key_facts', [])[:5], 1):
        print(f"   {i}. {fact[:100]}...")
    
    print(f"\n📉 REASONS NO:")
    for reason in result.get('reasons_no', [])[:3]:
        strength = reason.get('strength', 0)
        text = reason.get('reason', '')
        print(f"   [{strength}/10] {text[:80]}...")
    
    print(f"\n📈 REASONS YES:")
    for reason in result.get('reasons_yes', [])[:3]:
        strength = reason.get('strength', 0)
        text = reason.get('reason', '')
        print(f"   [{strength}/10] {text[:80]}...")
    
    print(f"\n💭 ANALYSIS:")
    print(f"   {result.get('analysis', '')[:300]}...")
    
    print(f"\n🔮 REFLECTION:")
    print(f"   {result.get('reflection', '')[:300]}...")
    
    print(f"\n📓 NOTES FOR NEXT ROUND:")
    print(f"   {result.get('notes_for_next_round', '')[:300]}...")
    
    print(f"\n⏱️  Time: {elapsed:.1f}s")
    print(f"💰 Tokens used: {trader.tokens_used}")
    print("=" * 60)
    
    return result


async def main():
    """Main entry point"""
    args = parse_args()
    
    # List types mode
    if args.list_types:
        print("\n📋 AVAILABLE FUNDAMENTAL TRADER TYPES:")
        print("-" * 60)
        for t, info in FUNDAMENTAL_TRADER_TYPES.items():
            print(f"\n  {t}")
            print(f"    Name:  {info['name']}")
            print(f"    Style: {info['style']}")
            print(f"    Bias:  {info['bias']}")
        print("\nUse --type <name> to run a specific trader")
        return
    
    # Enable verbose logging if requested
    if args.verbose:
        logging.getLogger("httpx").setLevel(logging.INFO)
        logging.getLogger("app.agents.base").setLevel(logging.INFO)
        logging.getLogger("app.services.grok").setLevel(logging.INFO)
        logging.getLogger("app.agents.traders.fundamental_agent").setLevel(logging.INFO)
    
    # Check for required env vars
    if not os.getenv("GROK_API_KEY"):
        logger.error("❌ GROK_API_KEY not set. Add it to ../.env")
        sys.exit(1)
    
    # Build market data
    market_data = SAMPLE_MARKET_DATA.copy()
    if args.question:
        market_data["market_topic"] = args.question
    
    question = market_data["market_topic"]
    
    # If no mode specified, default to --all
    if not args.type and not args.all:
        args.all = True
    
    # Single trader mode
    if args.type:
        # Validate type
        if args.type not in FUNDAMENTAL_TRADER_TYPES:
            print(f"❌ Unknown trader type '{args.type}'.")
            print(f"   Available: {', '.join(get_fundamental_trader_names())}")
            sys.exit(1)
        
        # Polling mode
        if args.poll:
            await run_poll_mode(
                trader_type=args.type,
                market_data=market_data,
                interval_seconds=args.poll_interval,
                session_id=args.session,
                spread=args.spread,
                quantity=args.quantity,
            )
            return
        
        # One-shot mode
        await test_single_type(args.type, market_data)
        return
    
    # All traders mode
    if args.all:
        print("\n" + "=" * 80)
        print("🌐 RUNNING ALL FUNDAMENTAL TRADERS")
        print("=" * 80)
        print(f"Question: {question}")
        print(f"Traders: {len(FUNDAMENTAL_TRADER_TYPES)}")
        print(f"Max concurrent: {args.concurrent}")
        print("=" * 80 + "\n")
        
        results = await run_all_traders(
            market_data=market_data,
            max_concurrent=args.concurrent,
        )
        
        # Print comparison
        print_comparison(results, question)


if __name__ == "__main__":
    asyncio.run(main())
