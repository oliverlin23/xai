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
    
    # Save results to file
    uv run python scripts/test_noise_agent.py --save

Requires:
    - X_BEARER_TOKEN in .env (for X API)
    - GROK_API_KEY in .env (for Grok)
"""
import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime
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
    ]
}


def save_results_to_file(
    sphere: str,
    question: str,
    filtered_result,
    result: dict | None,
    search_time: float,
    forecast_time: float,
    tokens_used: int,
    search_query: str | None = None,
):
    """Save test results to a timestamped text file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sanitize question for filename
    safe_question = "".join(c if c.isalnum() or c in " -_" else "" for c in question[:30])
    safe_question = safe_question.replace(" ", "_")
    
    output_dir = Path(__file__).parent / "test_outputs"
    output_dir.mkdir(exist_ok=True)
    
    filename = output_dir / f"noise_trader_{timestamp}_{safe_question}.txt"
    
    lines = []
    lines.append("=" * 80)
    lines.append("NOISE TRADER TEST RESULTS")
    lines.append("=" * 80)
    lines.append(f"Timestamp: {datetime.now().isoformat()}")
    lines.append(f"Sphere: {sphere}")
    lines.append(f"Question: {question}")
    lines.append("")
    
    # Search query / keywords
    if search_query:
        lines.append("-" * 80)
        lines.append("SEARCH QUERY (Keywords)")
        lines.append("-" * 80)
        lines.append(search_query)
        lines.append("")
    
    # Tweets
    lines.append("-" * 80)
    lines.append("TWEETS")
    lines.append("-" * 80)
    if filtered_result and filtered_result.tweets:
        lines.append(f"Total fetched: {filtered_result.total_tweets_analyzed}")
        lines.append(f"Relevant: {filtered_result.relevant_tweet_count}")
        lines.append("")
        for i, tweet in enumerate(filtered_result.tweets, 1):
            author = tweet.get("author", "unknown")
            text = tweet.get("text", "")
            likes = tweet.get("likes", 0)
            rts = tweet.get("retweets", 0)
            lines.append(f"[{i}] {author} ({likes} likes, {rts} RTs)")
            lines.append(f"    {text}")
            lines.append("")
    else:
        lines.append("No tweets found")
    lines.append("")
    
    # Prediction results
    lines.append("-" * 80)
    lines.append("PREDICTION")
    lines.append("-" * 80)
    if result:
        lines.append(f"Prediction: {result.get('prediction')}%")
        lines.append(f"Signal: {result.get('signal')}")
        lines.append(f"Confidence: {result.get('confidence', 0):.0%}")
        lines.append(f"Tweets analyzed: {result.get('tweets_analyzed')}")
        
        # Reasoning if available
        if result.get('reasoning'):
            lines.append("")
            lines.append("Reasoning:")
            lines.append(result['reasoning'])
        
        # Factors if available
        if result.get('factors'):
            lines.append("")
            lines.append("Factors:")
            for factor in result['factors']:
                lines.append(f"  - {factor}")
    else:
        lines.append("Prediction failed")
    lines.append("")
    
    # Timing & tokens
    lines.append("-" * 80)
    lines.append("METRICS")
    lines.append("-" * 80)
    lines.append(f"Tweet search & filter: {search_time:.1f}s")
    lines.append(f"Forecast generation: {forecast_time:.1f}s")
    lines.append(f"Total time: {search_time + forecast_time:.1f}s")
    lines.append(f"Tokens used: {tokens_used}")
    lines.append("")
    lines.append("=" * 80)
    
    # Write to file
    with open(filename, "w") as f:
        f.write("\n".join(lines))
    
    return filename


async def test_noise_trader(
    sphere: str, 
    market_data: dict,
    use_semantic_filter: bool = True,
    save_to_file: bool = False,
):
    """Test the NoiseTrader with a specific sphere and market data"""
    import time
    from app.noise_traders.semantic_filter import SemanticFilter
    
    mode = "semantic filter" if use_semantic_filter else "tool-based"
    question = market_data['market_topic']
    
    print("\n" + "=" * 60)
    print(f"NOISE TRADER TEST")
    print("=" * 60)
    print(f"Sphere: {sphere}")
    print(f"Mode: {mode}")
    print(f"Question: {question}")
    print("=" * 60)
    
    filter_config = SemanticFilterConfig(
        max_tweets_to_fetch=100,
        max_tweets_to_return=15,
        lookback_days=7,
    )
    
    # Timing metrics
    search_time = 0.0
    forecast_time = 0.0
    filtered_result = None
    search_query = None
    
    # If using semantic filter, run it first to show tweets
    if use_semantic_filter:
        print("\n📡 FETCHING & FILTERING TWEETS...")
        search_start = time.perf_counter()
        
        semantic_filter = SemanticFilter(config=filter_config)
        filtered_result = await semantic_filter.filter(
            question=question,
            sphere=sphere,
        )
        
        # Try to get the search query that was used
        if hasattr(semantic_filter, '_last_search_query'):
            search_query = semantic_filter._last_search_query
        
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
        else:
            print("   No relevant tweets found")
    
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
        print(f"📊 PREDICTION ({sphere})")
        print("=" * 60)
        
        # Core prediction (simplified output)
        print(f"\n🎯 PREDICTION: {result['prediction']}%")
        print(f"📡 Signal: {result['signal']}")
        print(f"📈 Tweets analyzed: {result['tweets_analyzed']}")
        print(f"🔒 Confidence: {result['confidence']:.0%}")
        
        # Timing summary
        print(f"\n⏱️  TIMING:")
        if search_time > 0:
            print(f"   Tweet search & filter: {search_time:.1f}s")
        print(f"   Forecast generation:   {forecast_time:.1f}s")
        print(f"   Total:                 {search_time + forecast_time:.1f}s")
        print(f"\n💰 Tokens used: {trader.tokens_used}")
        print("=" * 60)
        
        # Save to file if requested
        if save_to_file:
            filename = save_results_to_file(
                sphere=sphere,
                question=question,
                filtered_result=filtered_result,
                result=result,
                search_time=search_time,
                forecast_time=forecast_time,
                tokens_used=trader.tokens_used,
                search_query=search_query,
            )
            print(f"\n💾 Results saved to: {filename}")
        
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
    parser.add_argument(
        "--save", "-s",
        action="store_true",
        help="Save results (tweets, keywords, prediction) to a text file in scripts/test_outputs/"
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
        save_to_file=args.save,
    )


if __name__ == "__main__":
    asyncio.run(main())
