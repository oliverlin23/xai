#!/usr/bin/env python3
"""
Test script for NoiseTrader prediction market agent

Usage:
    cd backend
    
    # Run ALL spheres and compare predictions (default)
    uv run python scripts/test_noise_agent.py
    
    # Run single sphere
    uv run python scripts/test_noise_agent.py --sphere fintwit_market
    
    # Custom question
    uv run python scripts/test_noise_agent.py --question "Will BTC hit 100k by end of 2025?"
    
    # Save results to file
    uv run python scripts/test_noise_agent.py --save
    
    # Continuous polling mode with market-making
    uv run python scripts/test_noise_agent.py --sphere fintwit_market --poll
    uv run python scripts/test_noise_agent.py --sphere fintwit_market --poll --poll-interval 30
    
    # Polling with specific session (for trading)
    uv run python scripts/test_noise_agent.py --sphere fintwit_market --poll --session my-session-id

Requires:
    - X_BEARER_TOKEN in .env (for X API)
    - GROK_API_KEY in .env (for Grok)
"""
import argparse
import asyncio
import logging
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

# Load env from project root
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from app.traders.noise_agent import NoiseTrader
from app.traders.semantic_filter import SemanticFilterConfig
from app.market import SupabaseMarketMaker

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s | %(levelname)-8s | %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Suppress noisy logging
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)
logging.getLogger("app.agents.base").setLevel(logging.WARNING)
logging.getLogger("app.services.grok").setLevel(logging.WARNING)
logging.getLogger("app.traders.noise_agent").setLevel(logging.WARNING)
logging.getLogger("app.traders.semantic_filter").setLevel(logging.WARNING)
logging.getLogger("x_search").setLevel(logging.WARNING)


# All available spheres
ALL_SPHERES = [
    "eacc_sovereign",
    "america_first",
    "blue_establishment",
    "progressive_left",
    "optimizer_idw",
    "fintwit_market",
    "builder_engineering",
    "academic_research",
    "osint_intel",
]

# Sphere display names
SPHERE_NAMES = {
    "eacc_sovereign": "e/acc & Sovereign",
    "america_first": "America First",
    "blue_establishment": "Blue Establishment",
    "progressive_left": "Progressive Left",
    "optimizer_idw": "Optimizer/IDW",
    "fintwit_market": "FinTwit/Market",
    "builder_engineering": "Builder/Engineering",
    "academic_research": "Academic/Research",
    "osint_intel": "OSINT/Intel",
}


# Sample market data for testing
SAMPLE_MARKET_DATA = {
    "market_topic": "Will the Federal Reserve cut interest rates in December 2025?",
    "order_book": {
        "bids": [
            {"quantity": 100, "price": 0.82},
            {"quantity": 75, "price": 0.81},
            {"quantity": 50, "price": 0.80},
        ],
        "asks": [
            {"quantity": 80, "price": 0.78},
            {"quantity": 60, "price": 0.77},
            {"quantity": 120, "price": 0.76},
        ]
    },
    "recent_trades": [
        {"side": "buy", "quantity": 25, "price": 0.80, "time_ago": "2 min ago"},
        {"side": "sell", "quantity": 15, "price": 0.79, "time_ago": "5 min ago"},
    ]
}


@dataclass
class SphereResult:
    """Result from a single sphere's prediction"""
    sphere: str
    prediction: int | None
    signal: str
    confidence: float
    tweets_analyzed: int
    reasoning: str
    tokens_used: int
    time_seconds: float
    error: str | None = None


async def run_single_sphere(
    sphere: str,
    market_data: dict,
    filter_config: SemanticFilterConfig,
) -> SphereResult:
    """Run a single sphere's noise trader and return result"""
    import time
    
    start = time.perf_counter()
    
    try:
        trader = NoiseTrader(
            sphere=sphere,
            use_semantic_filter=True,
            semantic_filter_config=filter_config,
        )
        
        result = await trader.execute(market_data)
        elapsed = time.perf_counter() - start
        
        return SphereResult(
            sphere=sphere,
            prediction=result.get("prediction"),
            signal=result.get("signal", "uncertain"),
            confidence=result.get("confidence", 0),
            tweets_analyzed=result.get("tweets_analyzed", 0),
            reasoning=result.get("analysis", "")[:200],
            tokens_used=trader.tokens_used,
            time_seconds=elapsed,
        )
        
    except Exception as e:
        elapsed = time.perf_counter() - start
        return SphereResult(
            sphere=sphere,
            prediction=None,
            signal="error",
            confidence=0,
            tweets_analyzed=0,
            reasoning="",
            tokens_used=0,
            time_seconds=elapsed,
            error=str(e),
        )


async def run_all_spheres(
    market_data: dict,
    filter_config: SemanticFilterConfig,
    max_concurrent: int = 3,
) -> list[SphereResult]:
    """Run all spheres with limited concurrency"""
    
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def run_with_semaphore(sphere: str) -> SphereResult:
        async with semaphore:
            print(f"  🔄 Starting {SPHERE_NAMES.get(sphere, sphere)}...")
            result = await run_single_sphere(sphere, market_data, filter_config)
            if result.error:
                print(f"  ❌ {SPHERE_NAMES.get(sphere, sphere)}: FAILED - {result.error[:50]}")
            else:
                print(f"  ✅ {SPHERE_NAMES.get(sphere, sphere)}: {result.prediction}% ({result.time_seconds:.1f}s)")
            return result
    
    tasks = [run_with_semaphore(sphere) for sphere in ALL_SPHERES]
    results = await asyncio.gather(*tasks)
    return list(results)


def print_comparison(results: list[SphereResult], question: str):
    """Print comparison of all sphere predictions"""
    
    # Filter successful results
    successful = [r for r in results if r.prediction is not None]
    failed = [r for r in results if r.prediction is None]
    
    if not successful:
        print("\n❌ All spheres failed!")
        return
    
    # Sort by prediction
    successful.sort(key=lambda r: r.prediction, reverse=True)
    
    # Calculate stats
    predictions = [r.prediction for r in successful]
    avg_prediction = sum(predictions) / len(predictions)
    min_pred = min(predictions)
    max_pred = max(predictions)
    spread = max_pred - min_pred
    
    # Weighted average by confidence
    weighted_sum = sum(r.prediction * r.confidence for r in successful)
    weight_total = sum(r.confidence for r in successful)
    weighted_avg = weighted_sum / weight_total if weight_total > 0 else avg_prediction
    
    print("\n" + "=" * 80)
    print("📊 SPHERE COMPARISON")
    print("=" * 80)
    print(f"Question: {question}")
    print("=" * 80)
    
    # Header
    print(f"\n{'Sphere':<22} {'Pred':>6} {'Signal':<10} {'Conf':>6} {'Tweets':>7} {'Time':>6}")
    print("-" * 65)
    
    # Results
    for r in successful:
        name = SPHERE_NAMES.get(r.sphere, r.sphere)[:20]
        pred_bar = "█" * (r.prediction // 10) + "░" * (10 - r.prediction // 10)
        print(f"{name:<22} {r.prediction:>5}% {r.signal:<10} {r.confidence:>5.0%} {r.tweets_analyzed:>7} {r.time_seconds:>5.1f}s")
    
    # Failed spheres
    if failed:
        print("-" * 65)
        for r in failed:
            name = SPHERE_NAMES.get(r.sphere, r.sphere)[:20]
            print(f"{name:<22} {'FAILED':>6} {r.error[:30] if r.error else 'Unknown error'}")
    
    # Summary stats
    print("\n" + "=" * 80)
    print("📈 SUMMARY STATISTICS")
    print("=" * 80)
    print(f"  Spheres reporting:    {len(successful)}/{len(results)}")
    print(f"  Average prediction:   {avg_prediction:.1f}%")
    print(f"  Weighted average:     {weighted_avg:.1f}% (by confidence)")
    print(f"  Range:                {min_pred}% - {max_pred}% (spread: {spread}%)")
    
    # Consensus analysis
    print("\n" + "-" * 40)
    if spread <= 10:
        print(f"  🤝 STRONG CONSENSUS: All spheres within {spread}% of each other")
    elif spread <= 20:
        print(f"  📊 MODERATE CONSENSUS: {spread}% spread between extremes")
    else:
        print(f"  ⚔️  DIVERGENT VIEWS: {spread}% spread - spheres disagree significantly")
    
    # Bullish vs Bearish
    bullish = [r for r in successful if r.prediction >= 60]
    bearish = [r for r in successful if r.prediction <= 40]
    neutral = [r for r in successful if 40 < r.prediction < 60]
    
    print(f"\n  Bullish (≥60%):  {len(bullish)} spheres")
    print(f"  Neutral (40-60%): {len(neutral)} spheres")
    print(f"  Bearish (≤40%):  {len(bearish)} spheres")
    
    # Most extreme views
    print("\n" + "-" * 40)
    most_bullish = successful[0]
    most_bearish = successful[-1]
    print(f"  📈 Most bullish: {SPHERE_NAMES.get(most_bullish.sphere, most_bullish.sphere)} @ {most_bullish.prediction}%")
    print(f"  📉 Most bearish: {SPHERE_NAMES.get(most_bearish.sphere, most_bearish.sphere)} @ {most_bearish.prediction}%")
    
    # Token usage
    total_tokens = sum(r.tokens_used for r in results)
    total_time = sum(r.time_seconds for r in results)
    print(f"\n  💰 Total tokens:      {total_tokens:,}")
    print(f"  ⏱️  Total time:        {total_time:.1f}s")
    
    print("=" * 80)


def save_results(results: list[SphereResult], question: str):
    """Save results to file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_question = "".join(c if c.isalnum() or c in " -_" else "" for c in question[:30])
    safe_question = safe_question.replace(" ", "_")
    
    output_dir = Path(__file__).parent / "test_outputs"
    output_dir.mkdir(exist_ok=True)
    
    filename = output_dir / f"sphere_comparison_{timestamp}_{safe_question}.txt"
    
    successful = [r for r in results if r.prediction is not None]
    successful.sort(key=lambda r: r.prediction, reverse=True)
    
    predictions = [r.prediction for r in successful]
    avg_prediction = sum(predictions) / len(predictions) if predictions else 0
    
    lines = []
    lines.append("=" * 80)
    lines.append("SPHERE COMPARISON RESULTS")
    lines.append("=" * 80)
    lines.append(f"Timestamp: {datetime.now().isoformat()}")
    lines.append(f"Question: {question}")
    lines.append("")
    
    lines.append("-" * 80)
    lines.append("PREDICTIONS BY SPHERE")
    lines.append("-" * 80)
    
    for r in successful:
        name = SPHERE_NAMES.get(r.sphere, r.sphere)
        lines.append(f"{name}: {r.prediction}% (confidence: {r.confidence:.0%}, signal: {r.signal})")
        lines.append(f"  Tweets: {r.tweets_analyzed}, Time: {r.time_seconds:.1f}s, Tokens: {r.tokens_used}")
        if r.reasoning:
            lines.append(f"  Reasoning: {r.reasoning[:150]}...")
        lines.append("")
    
    lines.append("-" * 80)
    lines.append("SUMMARY")
    lines.append("-" * 80)
    lines.append(f"Average prediction: {avg_prediction:.1f}%")
    lines.append(f"Range: {min(predictions):.0f}% - {max(predictions):.0f}%")
    lines.append(f"Spheres reporting: {len(successful)}/{len(results)}")
    
    with open(filename, "w") as f:
        f.write("\n".join(lines))
    
    return filename


async def test_single_sphere(
    sphere: str,
    market_data: dict,
    save_to_file: bool = False,
):
    """Test a single sphere (original behavior)"""
    import time
    from app.traders.semantic_filter import SemanticFilter
    
    question = market_data['market_topic']
    
    print("\n" + "=" * 60)
    print(f"NOISE TRADER TEST")
    print("=" * 60)
    print(f"Sphere: {SPHERE_NAMES.get(sphere, sphere)}")
    print(f"Question: {question}")
    print("=" * 60)
    
    filter_config = SemanticFilterConfig(
        max_tweets_to_fetch=100,
        max_tweets_to_return=15,
        lookback_days=7,
    )
    
    # Run semantic filter first to show tweets
    print("\n📡 FETCHING & FILTERING TWEETS...")
    search_start = time.perf_counter()
    
    semantic_filter = SemanticFilter(config=filter_config)
    filtered_result = await semantic_filter.filter(
        question=question,
        sphere=sphere,
    )
    
    search_time = time.perf_counter() - search_start
    
    print(f"\n📥 TWEETS: {filtered_result.relevant_tweet_count}/{filtered_result.total_tweets_analyzed} relevant (⏱️ {search_time:.1f}s)")
    
    if filtered_result.tweets:
        print(f"\n✅ RELEVANT TWEETS:")
        print("-" * 50)
        for i, tweet in enumerate(filtered_result.tweets, 1):
            author = tweet.get("author", "unknown")
            text = tweet.get("text", "")
            likes = tweet.get("likes", 0)
            rts = tweet.get("retweets", 0)
            print(f"[{i}] {author} ({likes}L/{rts}RT): {text[:150]}...")
    
    # Create trader and run
    trader = NoiseTrader(
        sphere=sphere,
        use_semantic_filter=True,
        semantic_filter_config=filter_config,
    )
    
    print("\n" + "=" * 60)
    print("🧠 GENERATING FORECAST...")
    print("=" * 60)
    
    forecast_start = time.perf_counter()
    result = await trader.execute(market_data)
    forecast_time = time.perf_counter() - forecast_start
    
    print("\n" + "=" * 60)
    print(f"📊 PREDICTION ({SPHERE_NAMES.get(sphere, sphere)})")
    print("=" * 60)
    
    print(f"\n🎯 PREDICTION: {result['prediction']}%")
    print(f"📡 Signal: {result['signal']}")
    print(f"📈 Tweets analyzed: {result['tweets_analyzed']}")
    print(f"🔒 Confidence: {result['confidence']:.0%}")
    
    print(f"\n⏱️  TIMING:")
    print(f"   Tweet search & filter: {search_time:.1f}s")
    print(f"   Forecast generation:   {forecast_time:.1f}s")
    print(f"   Total:                 {search_time + forecast_time:.1f}s")
    print(f"\n💰 Tokens used: {trader.tokens_used}")
    print("=" * 60)
    
    return result


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Test NoiseTrader prediction agent")
    parser.add_argument(
        "--sphere",
        type=str,
        default=None,
        choices=ALL_SPHERES,
        help="Single sphere to test (default: run all spheres)"
    )
    parser.add_argument(
        "--question",
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
        "--save", "-s",
        action="store_true",
        help="Save results to a text file in scripts/test_outputs/"
    )
    parser.add_argument(
        "--concurrent", "-c",
        type=int,
        default=3,
        help="Max concurrent sphere requests (default: 3)"
    )
    parser.add_argument(
        "--poll",
        action="store_true",
        help="Run continuously, polling every 10 seconds with market-making"
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=10,
        help="Seconds between polls (default: 10)"
    )
    parser.add_argument(
        "--session",
        type=str,
        default="test-session",
        help="Session ID for trading (default: test-session)"
    )
    parser.add_argument(
        "--spread",
        type=int,
        default=4,
        help="Total spread width for market making (default: 4 = 2 on each side)"
    )
    parser.add_argument(
        "--quantity",
        type=int,
        default=100,
        help="Quantity for each market-making order (default: 100)"
    )
    return parser.parse_args()


def format_trades_for_agent(trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format API trade responses for the agent's input format."""
    formatted = []
    now = datetime.utcnow()
    
    for t in trades[:10]:  # Limit to 10 most recent
        created_at = t.get("created_at")
        if created_at:
            # Parse ISO timestamp
            try:
                trade_time = datetime.fromisoformat(created_at.replace("Z", "+00:00").replace("+00:00", ""))
                delta = now - trade_time
                if delta.total_seconds() < 60:
                    time_ago = f"{int(delta.total_seconds())} sec ago"
                elif delta.total_seconds() < 3600:
                    time_ago = f"{int(delta.total_seconds() / 60)} min ago"
                else:
                    time_ago = f"{int(delta.total_seconds() / 3600)} hr ago"
            except:
                time_ago = "recently"
        else:
            time_ago = "recently"
        
        # Determine if it's a buy or sell from the perspective of the trade
        formatted.append({
            "side": "buy",  # The trade happened (buyer got matched)
            "quantity": t.get("quantity", 0),
            "price": t.get("price", 50) / 100,  # Convert cents to decimal
            "time_ago": time_ago,
        })
    
    return formatted


async def run_poll_mode(
    sphere: str,
    market_data: Dict[str, Any],
    session_id: str,
    interval_seconds: int = 10,
    spread: int = 4,
    quantity: int = 100,
) -> None:
    """
    Run noise trader continuously with market-making.
    
    Each round:
    1. Fetch recent trades from Supabase
    2. Run prediction with notes from last round
    3. Cancel previous orders
    4. Place new market-making orders (4-wide around prediction)
    5. Order matching happens automatically via database trigger -> Edge Function
    6. Wait and repeat
    """
    trader_name = sphere  # Use sphere name as trader name
    question = market_data.get("market_topic", "")
    
    print("\n" + "=" * 70)
    print("🔄 CONTINUOUS POLLING MODE (Supabase)")
    print("=" * 70)
    print(f"Sphere: {SPHERE_NAMES.get(sphere, sphere)}")
    print(f"Question: {question}")
    print(f"Session ID: {session_id}")
    print(f"Poll interval: {interval_seconds}s")
    print(f"Market making spread: {spread} (bid @ pred-{spread//2}, ask @ pred+{spread//2})")
    print(f"Order quantity: {quantity}")
    print("Press Ctrl+C to stop.")
    print("=" * 70 + "\n")
    
    # Initialize components
    filter_config = SemanticFilterConfig(
        max_tweets_to_fetch=50,
        max_tweets_to_return=15,
        lookback_days=7,
    )
    
    trader = NoiseTrader(
        sphere=sphere,
        use_semantic_filter=True,
        semantic_filter_config=filter_config,
    )
    
    # Use Supabase market maker (reads/writes directly to Supabase tables)
    market_maker = SupabaseMarketMaker()
    
    round_number = 1
    previous_notes = ""
    
    try:
        while True:
            start_ts = datetime.now().strftime("%H:%M:%S")
            print(f"\n[{start_ts}] 🔄 Round {round_number}...")
            
            try:
                # Step 1: Fetch market data from Supabase
                orderbook = market_maker.get_orderbook(session_id)
                recent_trades_raw = market_maker.get_recent_trades(session_id, limit=10)
                recent_trades = format_trades_for_agent(recent_trades_raw)
                
                # Build input data with current market state
                round_data = market_data.copy()
                round_data["order_book"] = {
                    "bids": [{"quantity": b["quantity"], "price": b["price"] / 100} for b in orderbook.get("bids", [])],
                    "asks": [{"quantity": a["quantity"], "price": a["price"] / 100} for a in orderbook.get("asks", [])],
                }
                round_data["recent_trades"] = recent_trades
                round_data["previous_notes"] = previous_notes
                round_data["round_number"] = round_number
                
                # Step 2: Run prediction
                result = await trader.execute(round_data)
                
                prediction = result.get("prediction", 50)
                signal = result.get("signal", "uncertain")
                tweets = result.get("tweets_analyzed", 0)
                confidence = result.get("confidence", 0)
                notes = result.get("notes_for_next_round", "")
                
                print(f"[{start_ts}] 🎯 prediction={prediction}% signal={signal} tweets={tweets} conf={confidence:.0%}")
                
                # Step 3: Market making - cancel old orders and place new ones
                bid_result, ask_result = market_maker.place_market_making_orders(
                    session_id=session_id,
                    trader_name=trader_name,
                    prediction=prediction,
                    spread=spread,
                    quantity=quantity,
                )
                
                bid_price = prediction - spread // 2
                ask_price = prediction + spread // 2
                
                if bid_result and ask_result:
                    print(f"[{start_ts}] 📈 Market making: bid={bid_price}¢ ask={ask_price}¢ qty={quantity}")
                    
                    # Step 4: Trigger order matching (uses SQL function, no Edge Function needed)
                    match_result = market_maker.trigger_matching(session_id)
                    if match_result.get("trades_count", 0) > 0:
                        print(f"[{start_ts}] 🔄 Matched {match_result['trades_count']} trades, volume={match_result['volume']}")
                else:
                    print(f"[{start_ts}] ⚠️  Market making failed (check Supabase connection)")
                
                # Print detailed result
                print(json.dumps({
                    "round": round_number,
                    "prediction": prediction,
                    "signal": signal,
                    "tweets_analyzed": tweets,
                    "confidence": confidence,
                    "analysis": result.get("analysis", "")[:200] + "...",
                    "notes_for_next_round": notes[:200] + "..." if len(notes) > 200 else notes,
                    "market_making": {
                        "bid_price": bid_price,
                        "ask_price": ask_price,
                        "quantity": quantity,
                    }
                }, indent=2, ensure_ascii=False))
                
                # Step 4: Save notes for next round
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
        print(f"🧹 Cleaning up: cancelling orders for {trader_name}...")
        cancelled = market_maker.cancel_all_orders(session_id, trader_name)
        print(f"   Cancelled {cancelled} orders.")


async def main():
    """Main entry point"""
    args = parse_args()
    
    # Enable verbose logging if requested
    if args.verbose:
        logging.getLogger("httpx").setLevel(logging.INFO)
        logging.getLogger("app.agents.base").setLevel(logging.INFO)
        logging.getLogger("app.services.grok").setLevel(logging.INFO)
        logging.getLogger("app.traders.noise_agent").setLevel(logging.INFO)
        logging.getLogger("app.traders.semantic_filter").setLevel(logging.INFO)
        logging.getLogger("x_search").setLevel(logging.INFO)
    
    # Check for required env vars
    if not os.getenv("GROK_API_KEY"):
        logger.error("❌ GROK_API_KEY not set. Add it to ../.env")
        sys.exit(1)
    
    if not os.getenv("X_BEARER_TOKEN"):
        logger.warning("⚠️  X_BEARER_TOKEN not set. Tool calls will fail.")
        logger.warning("   Add X_BEARER_TOKEN to ../.env for full functionality")

    # Build market data
    market_data = SAMPLE_MARKET_DATA.copy()
    if args.question:
        market_data["market_topic"] = args.question
    
    question = market_data["market_topic"]
    
    # Polling mode (continuous)
    if args.poll:
        if not args.sphere:
            print("❌ --poll requires --sphere to be specified")
            print(f"   Available spheres: {', '.join(ALL_SPHERES)}")
            sys.exit(1)
        
        await run_poll_mode(
            sphere=args.sphere,
            market_data=market_data,
            session_id=args.session,
            interval_seconds=args.poll_interval,
            spread=args.spread,
            quantity=args.quantity,
        )
        return
    
    # Single sphere mode (one-shot)
    if args.sphere:
        await test_single_sphere(
            sphere=args.sphere,
            market_data=market_data,
            save_to_file=args.save,
        )
        return
    
    # All spheres mode (default)
    print("\n" + "=" * 80)
    print("🌐 RUNNING ALL SPHERES")
    print("=" * 80)
    print(f"Question: {question}")
    print(f"Spheres: {len(ALL_SPHERES)}")
    print(f"Max concurrent: {args.concurrent}")
    print("=" * 80 + "\n")
    
    filter_config = SemanticFilterConfig(
        max_tweets_to_fetch=50,
        max_tweets_to_return=10,
        lookback_days=7,
    )
    
    results = await run_all_spheres(
        market_data=market_data,
        filter_config=filter_config,
        max_concurrent=args.concurrent,
    )
    
    # Print comparison
    print_comparison(results, question)
    
    # Save if requested
    if args.save:
        filename = save_results(results, question)
        print(f"\n💾 Results saved to: {filename}")


if __name__ == "__main__":
    asyncio.run(main())
