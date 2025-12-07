#!/usr/bin/env python3
"""
Test script for NoiseTrader prediction market agent

Usage:
    cd backend
    
    # Default: semantic filter mode (recommended)
    uv run python scripts/test_noise_agent.py
    
    # Use tool-based mode instead
    uv run python scripts/test_noise_agent.py --no-semantic-filter
    
    # Custom sphere and question
    uv run python scripts/test_noise_agent.py --sphere fintwit_market --question "Will BTC hit 100k?"

Requires:
    - X_BEARER_TOKEN in .env (for X API)
    - GROK_API_KEY in .env (for Grok)
"""
import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

# Load env from project root
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from app.noise_traders.noise_agent import NoiseTrader
from app.noise_traders.semantic_filter import SemanticFilterConfig

logging.basicConfig(
    level=logging.WARNING,  # Only show warnings and errors by default
    format="%(asctime)s | %(levelname)-8s | %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # But allow our logger to show info

# Suppress noisy logging - only show errors
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)
logging.getLogger("app.agents.base").setLevel(logging.WARNING)
logging.getLogger("app.services.grok").setLevel(logging.WARNING)
logging.getLogger("app.noise_traders.noise_agent").setLevel(logging.WARNING)
logging.getLogger("app.noise_traders.semantic_filter").setLevel(logging.WARNING)
logging.getLogger("x_search").setLevel(logging.WARNING)


# Sample market data for testing
SAMPLE_MARKET_DATA = {
    "market_topic": "Will the Federal Reserve cut interest rates in December 2025?",
    "order_book": {
        "bids": [
            {"quantity": 100, "price": 0.42},
            {"quantity": 75, "price": 0.40},
            {"quantity": 50, "price": 0.38},
        ],
        "asks": [
            {"quantity": 80, "price": 0.45},
            {"quantity": 60, "price": 0.48},
            {"quantity": 120, "price": 0.50},
        ]
    },
    "recent_trades": [
        {"side": "buy", "quantity": 25, "price": 0.43, "time_ago": "2 min ago"},
        {"side": "sell", "quantity": 15, "price": 0.44, "time_ago": "5 min ago"},
        {"side": "buy", "quantity": 50, "price": 0.42, "time_ago": "8 min ago"},
        {"side": "buy", "quantity": 30, "price": 0.41, "time_ago": "15 min ago"},
        {"side": "sell", "quantity": 20, "price": 0.45, "time_ago": "22 min ago"},
    ]
}


async def test_noise_trader(
    sphere: str, 
    market_data: dict,
    use_semantic_filter: bool = True,
):
    """Test the NoiseTrader with a specific sphere and market data"""
    import time
    from app.noise_traders.semantic_filter import SemanticFilter
    
    mode = "semantic filter" if use_semantic_filter else "tool-based"
    question = market_data['market_topic']
    
    print("\n" + "=" * 60)
    print(f"🤖 NOISE TRADER TEST")
    print("=" * 60)
    print(f"Sphere: {sphere}")
    print(f"Mode: {mode}")
    print(f"Question: {question}")
    print("=" * 60)
    
    filter_config = SemanticFilterConfig(
        max_tweets_to_fetch=100,
        max_tweets_to_return=15,
        min_relevance_score=0.3,
        lookback_days=7,
        verified_only=False,  # Don't restrict - sphere filter handles quality
    )
    
    # Timing metrics
    search_time = 0.0
    forecast_time = 0.0
    
    # If using semantic filter, run it first to show tweets
    filtered_result = None
    if use_semantic_filter:
        print("\n📡 FETCHING & FILTERING TWEETS...")
        search_start = time.perf_counter()
        
        semantic_filter = SemanticFilter(config=filter_config)
        filtered_result = await semantic_filter.filter(
            question=question,
            sphere=sphere,
        )
        
        search_time = time.perf_counter() - search_start
        
        # Show raw tweets fetched
        print(f"\n📥 TWEETS FETCHED: {filtered_result.total_tweets_analyzed} (⏱️ {search_time:.1f}s)")
        
        if filtered_result.total_tweets_analyzed > 0:
            # Show relevant tweets
            if filtered_result.relevant_tweets:
                print(f"\n✅ RELEVANT TWEETS ({len(filtered_result.relevant_tweets)}):")
                print("-" * 50)
                for i, tweet in enumerate(filtered_result.relevant_tweets, 1):
                    # Format timestamp nicely
                    timestamp = tweet.created_at[:16].replace("T", " ") if tweet.created_at else "unknown"
                    print(f"\n[{i}] @{tweet.author}")
                    print(f"    📅 {timestamp} | Relevance: {tweet.relevance_score:.0%} | ❤️ {tweet.likes} | 🔄 {tweet.retweets}")
                    print(f"    \"{tweet.text[:200]}{'...' if len(tweet.text) > 200 else ''}\"")
                    print(f"    → {tweet.relevance_reason}")
            else:
                print("\n⚠️  No tweets passed the relevance filter")
            
            print(f"\n📊 FILTER SUMMARY:")
            print(f"   {filtered_result.summary}")
        else:
            print("   No tweets found from this sphere on this topic")
    
    # Create trader
    trader = NoiseTrader(
        sphere=sphere, 
        use_semantic_filter=use_semantic_filter,
        semantic_filter_config=filter_config if use_semantic_filter else None,
    )
    
    try:
        print("\n" + "=" * 60)
        print("🧠 GENERATING FORECAST...")
        print("=" * 60)
        
        forecast_start = time.perf_counter()
        result = await trader.execute(market_data)
        forecast_time = time.perf_counter() - forecast_start
        
        print("\n" + "=" * 60)
        print(f"📊 SUPERFORECASTER PREDICTION ({sphere})")
        print("=" * 60)
        
        # Core prediction
        print(f"\n🎯 FINAL PREDICTION: {result['prediction']}%")
        print(f"📍 Baseline (Market): {result.get('baseline_probability', 50)}%")
        print(f"🔄 Initial Estimate: {result.get('initial_probability', result['prediction'])}%")
        print(f"📡 Sphere Signal: {result['signal']}")
        print(f"📈 Tweets Analyzed: {result['tweets_analyzed']}")
        print(f"🔒 Confidence: {result['confidence']:.0%}")
        
        # Key facts
        if result.get('key_facts'):
            print(f"\n📋 KEY FACTS:")
            for i, fact in enumerate(result['key_facts'][:5], 1):
                print(f"  {i}. {fact}")
        
        # Reasons NO
        if result.get('reasons_no'):
            print(f"\n🔴 REASONS FOR NO:")
            for item in result['reasons_no'][:3]:
                if isinstance(item, dict):
                    print(f"  • [{item.get('strength', '?')}/10] {item.get('reason', item)}")
                else:
                    print(f"  • {item}")
        
        # Reasons YES
        if result.get('reasons_yes'):
            print(f"\n🟢 REASONS FOR YES:")
            for item in result['reasons_yes'][:3]:
                if isinstance(item, dict):
                    print(f"  • [{item.get('strength', '?')}/10] {item.get('reason', item)}")
                else:
                    print(f"  • {item}")
        
        # Analysis
        if result.get('analysis'):
            print(f"\n🧠 ANALYSIS:")
            print(f"  {result['analysis'][:500]}{'...' if len(result.get('analysis', '')) > 500 else ''}")
        
        # Reflection
        if result.get('reflection'):
            print(f"\n🔍 REFLECTION:")
            print(f"  {result['reflection'][:300]}{'...' if len(result.get('reflection', '')) > 300 else ''}")
        
        # Timing & resource summary
        print(f"\n⏱️  TIMING:")
        if search_time > 0:
            print(f"   Tweet search & filter: {search_time:.1f}s")
        print(f"   Forecast generation:   {forecast_time:.1f}s")
        print(f"   Total:                 {search_time + forecast_time:.1f}s")
        print(f"\n💰 Tokens used: {trader.tokens_used}")
        print("=" * 60)
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Trader failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Test NoiseTrader prediction agent")
    parser.add_argument(
        "--sphere",
        type=str,
        default="academic_research",
        choices=[
            "eacc_sovereign", "america_first", "blue_establishment", "progressive_left",
            "optimizer_idw", "fintwit_market", "builder_engineering", "academic_research",
            "osint_intel",
        ],
        help="Sphere of influence to search (default: academic_research)"
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
        "--no-semantic-filter",
        action="store_true",
        help="Use tool-based mode instead of semantic filter"
    )
    return parser.parse_args()


async def main():
    """Main entry point"""
    args = parse_args()
    
    # Enable verbose logging if requested
    if args.verbose:
        logging.getLogger("httpx").setLevel(logging.INFO)
        logging.getLogger("app.agents.base").setLevel(logging.INFO)
        logging.getLogger("app.services.grok").setLevel(logging.INFO)
        logging.getLogger("app.noise_traders.noise_agent").setLevel(logging.INFO)
        logging.getLogger("app.noise_traders.semantic_filter").setLevel(logging.INFO)
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

    # Run test
    await test_noise_trader(
        sphere=args.sphere,
        market_data=market_data,
        use_semantic_filter=not args.no_semantic_filter,
    )


if __name__ == "__main__":
    asyncio.run(main())
