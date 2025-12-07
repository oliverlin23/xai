#!/usr/bin/env python3
"""
Test script for UserAgent prediction market agent

Usage:
    cd backend
    
    # Run single user agent (uses mapped username)
    uv run python scripts/test_user_agent.py --user oliver
    
    # Run with explicit X username
    uv run python scripts/test_user_agent.py --user custom --username elonmusk
    
    # Run ALL configured users and compare predictions
    uv run python scripts/test_user_agent.py --all
    
    # Custom question
    uv run python scripts/test_user_agent.py --user oliver --question "Will BTC hit 100k by end of 2025?"
    
    # Save results to file
    uv run python scripts/test_user_agent.py --all --save
    
    # Continuous polling mode (prediction only)
    uv run python scripts/test_user_agent.py --user oliver --poll
    
    # Continuous polling with market-making (requires valid session)
    uv run python scripts/test_user_agent.py --user oliver --poll --session <uuid>
    uv run python scripts/test_user_agent.py --user oliver --poll --session <uuid> --spread 6 --quantity 50

Requires:
    - X_BEARER_TOKEN in .env (for X API)
    - GROK_API_KEY in .env (for Grok)
    - SUPABASE_URL and SUPABASE_SERVICE_KEY in .env (for market making)
"""
import argparse
import asyncio
import logging
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable, Dict, Optional

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv

# Load env from project root
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from app.traders.user_agent import UserAgent, USER_ACCOUNT_MAPPINGS, get_user_agent_names
from app.market.client import SupabaseMarketMaker

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
logging.getLogger("app.traders.user_agent").setLevel(logging.WARNING)
logging.getLogger("x_search").setLevel(logging.WARNING)


# Sample market data for testing
SAMPLE_MARKET_DATA: Dict[str, object] = {
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
class UserResult:
    """Result from a single user agent's prediction"""
    user: str
    tracked_account: str
    prediction: int | None
    signal: str
    posts_analyzed: int
    reasoning: str
    tokens_used: int
    time_seconds: float
    error: str | None = None


async def run_single_user(
    user: str,
    market_data: dict,
    target_username: str | None = None,
) -> UserResult:
    """Run a single user agent and return result"""
    import time
    
    start = time.perf_counter()
    tracked = target_username or USER_ACCOUNT_MAPPINGS.get(user, user)
    
    try:
        agent = UserAgent(
            name=user,
            target_username=target_username,
            max_posts_to_fetch=50,
            max_posts_to_return=15,
            lookback_days=7,
        )
        
        result = await agent.execute(market_data)
        elapsed = time.perf_counter() - start
        
        return UserResult(
            user=user,
            tracked_account=f"@{tracked}",
            prediction=result.get("prediction"),
            signal=result.get("signal", "uncertain"),
            posts_analyzed=result.get("posts_analyzed", 0),
            reasoning=result.get("analysis", "")[:200],
            tokens_used=agent.tokens_used,
            time_seconds=elapsed,
        )
        
    except Exception as e:
        elapsed = time.perf_counter() - start
        return UserResult(
            user=user,
            tracked_account=f"@{tracked}",
            prediction=None,
            signal="error",
            posts_analyzed=0,
            reasoning="",
            tokens_used=0,
            time_seconds=elapsed,
            error=str(e),
        )


async def run_all_users(
    market_data: dict,
    max_concurrent: int = 2,
) -> list[UserResult]:
    """Run all configured user agents with limited concurrency"""
    
    all_users = get_user_agent_names()
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def run_with_semaphore(user: str) -> UserResult:
        async with semaphore:
            tracked = USER_ACCOUNT_MAPPINGS.get(user, user)
            print(f"  🔄 Starting {user} (tracking @{tracked})...")
            result = await run_single_user(user, market_data)
            if result.error:
                print(f"  ❌ {user}: FAILED - {result.error[:50]}")
            else:
                print(f"  ✅ {user}: {result.prediction}% ({result.time_seconds:.1f}s)")
            return result
    
    tasks = [run_with_semaphore(user) for user in all_users]
    results = await asyncio.gather(*tasks)
    return list(results)


def print_comparison(results: list[UserResult], question: str):
    """Print comparison of all user agent predictions"""
    
    # Filter successful results
    successful = [r for r in results if r.prediction is not None]
    failed = [r for r in results if r.prediction is None]
    
    if not successful:
        print("\n❌ All user agents failed!")
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
    print("📊 USER AGENT COMPARISON")
    print("=" * 80)
    print(f"Question: {question}")
    print("=" * 80)
    
    # Header
    print(f"\n{'User':<15} {'Account':<20} {'Pred':>6} {'Signal':<10} {'Posts':>6} {'Time':>6}")
    print("-" * 70)
    
    # Results
    for r in successful:
        print(f"{r.user:<15} {r.tracked_account:<20} {r.prediction:>5}% {r.signal:<10} {r.posts_analyzed:>6} {r.time_seconds:>5.1f}s")
    
    # Failed users
    if failed:
        print("-" * 70)
        for r in failed:
            print(f"{r.user:<15} {r.tracked_account:<20} {'FAILED':>6} {r.error[:30] if r.error else 'Unknown error'}")
    
    # Summary stats
    print("\n" + "=" * 80)
    print("📈 SUMMARY STATISTICS")
    print("=" * 80)
    print(f"  Users reporting:      {len(successful)}/{len(results)}")
    print(f"  Average prediction:   {avg_prediction:.1f}%")
    print(f"  Range:                {min_pred}% - {max_pred}% (spread: {spread}%)")
    
    # Consensus analysis
    print("\n" + "-" * 40)
    if spread <= 10:
        print(f"  🤝 STRONG CONSENSUS: All users within {spread}% of each other")
    elif spread <= 20:
        print(f"  📊 MODERATE CONSENSUS: {spread}% spread between extremes")
    else:
        print(f"  ⚔️  DIVERGENT VIEWS: {spread}% spread - users disagree significantly")
    
    # Token usage
    total_tokens = sum(r.tokens_used for r in results)
    total_time = sum(r.time_seconds for r in results)
    print(f"\n  💰 Total tokens:      {total_tokens:,}")
    print(f"  ⏱️  Total time:        {total_time:.1f}s")
    
    print("=" * 80)


def save_results(results: list[UserResult], question: str):
    """Save results to file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_question = "".join(c if c.isalnum() or c in " -_" else "" for c in question[:30])
    safe_question = safe_question.replace(" ", "_")
    
    output_dir = Path(__file__).parent / "test_outputs"
    output_dir.mkdir(exist_ok=True)
    
    filename = output_dir / f"user_agent_comparison_{timestamp}_{safe_question}.txt"
    
    successful = [r for r in results if r.prediction is not None]
    successful.sort(key=lambda r: r.prediction, reverse=True)
    
    predictions = [r.prediction for r in successful]
    avg_prediction = sum(predictions) / len(predictions) if predictions else 0
    
    lines = []
    lines.append("=" * 80)
    lines.append("USER AGENT COMPARISON RESULTS")
    lines.append("=" * 80)
    lines.append(f"Timestamp: {datetime.now().isoformat()}")
    lines.append(f"Question: {question}")
    lines.append("")
    
    lines.append("-" * 80)
    lines.append("PREDICTIONS BY USER")
    lines.append("-" * 80)
    
    for r in successful:
        lines.append(f"{r.user} (tracking {r.tracked_account}): {r.prediction}% (signal: {r.signal})")
        lines.append(f"  Posts: {r.posts_analyzed}, Time: {r.time_seconds:.1f}s, Tokens: {r.tokens_used}")
        if r.reasoning:
            lines.append(f"  Reasoning: {r.reasoning[:150]}...")
        lines.append("")
    
    lines.append("-" * 80)
    lines.append("SUMMARY")
    lines.append("-" * 80)
    lines.append(f"Average prediction: {avg_prediction:.1f}%")
    if predictions:
        lines.append(f"Range: {min(predictions):.0f}% - {max(predictions):.0f}%")
    lines.append(f"Users reporting: {len(successful)}/{len(results)}")
    
    with open(filename, "w") as f:
        f.write("\n".join(lines))
    
    return filename


async def test_single_user(
    user: str,
    market_data: dict,
    target_username: str | None = None,
):
    """Test a single user agent with verbose output"""
    import time
    
    question = market_data['market_topic']
    tracked = target_username or USER_ACCOUNT_MAPPINGS.get(user, user)
    
    print("\n" + "=" * 60)
    print(f"USER AGENT TEST")
    print("=" * 60)
    print(f"User: {user}")
    print(f"Tracking: @{tracked}")
    print(f"Question: {question}")
    print("=" * 60)
    
    # Create agent
    agent = UserAgent(
        name=user,
        target_username=target_username,
        max_posts_to_fetch=50,
        max_posts_to_return=15,
        lookback_days=7,
    )
    
    # Fetch posts first to show them
    print("\n📡 FETCHING POSTS...")
    fetch_start = time.perf_counter()
    
    fetched_posts = await agent._account_filter.fetch_posts(question)
    
    fetch_time = time.perf_counter() - fetch_start
    posts = fetched_posts.get("posts", [])
    
    print(f"\n📥 POSTS: {len(posts)} retrieved (⏱️ {fetch_time:.1f}s)")
    
    if posts:
        print(f"\n✅ POSTS FROM @{tracked}:")
        print("-" * 50)
        for i, post in enumerate(posts, 1):
            author = post.get("author", f"@{tracked}")
            text = post.get("text", "")
            likes = post.get("likes", 0)
            rts = post.get("retweets", 0)
            print(f"[{i}] {author} ({likes}L/{rts}RT): {text[:150]}...")
    else:
        print(f"\n⚠️  No posts found from @{tracked}")
    
    # Run forecast
    print("\n" + "=" * 60)
    print("🧠 GENERATING FORECAST...")
    print("=" * 60)
    
    forecast_start = time.perf_counter()
    result = await agent.execute(market_data)
    forecast_time = time.perf_counter() - forecast_start
    
    print("\n" + "=" * 60)
    print(f"📊 PREDICTION (User: {user}, tracking @{tracked})")
    print("=" * 60)
    
    print(f"\n🎯 PREDICTION: {result['prediction']}%")
    print(f"📡 Signal: {result['signal']}")
    print(f"📈 Posts analyzed: {result['posts_analyzed']}")
    print(f"🔒 Tracked account: {result['tracked_account']}")
    
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
    
    print(f"\n⏱️  TIMING:")
    print(f"   Post fetch:           {fetch_time:.1f}s")
    print(f"   Forecast generation:  {forecast_time:.1f}s")
    print(f"   Total:                {fetch_time + forecast_time:.1f}s")
    print(f"\n💰 Tokens used: {agent.tokens_used}")
    print("=" * 60)
    
    return result


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Test UserAgent prediction agent")
    parser.add_argument(
        "--user",
        type=str,
        default=None,
        help=f"User agent to test. Available: {', '.join(get_user_agent_names())}"
    )
    parser.add_argument(
        "--username",
        type=str,
        default=None,
        help="Explicit X username to track (overrides user mapping)"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Run all configured users and compare predictions"
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
        default=2,
        help="Max concurrent user agent requests (default: 2)"
    )
    parser.add_argument(
        "--poll",
        action="store_true",
        help="Continuously poll the target user every 10s",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        dest="poll",
        help="Alias for --poll (periodic polling every 10s)",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=10,
        help="Seconds between polls when --poll is used (default: 10)",
    )
    parser.add_argument(
        "--list-users",
        action="store_true",
        help="List all configured users and their X accounts"
    )
    parser.add_argument(
        "--session",
        type=str,
        default=None,
        help="Supabase session ID for market making (required for --poll with trading)"
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
        "--no-trade",
        action="store_true",
        help="Skip market making even if --session is provided"
    )
    return parser.parse_args()


async def run_poll_mode(
    user: str,
    target_username: Optional[str],
    market_data_provider: Callable[[], Awaitable[Dict[str, object]] | Dict[str, object]],
    interval_seconds: int = 10,
    session_id: Optional[str] = None,
    spread: int = 4,
    quantity: int = 100,
) -> None:
    """
    Poll the target user's posts periodically (default every 10s) using x_search username filter.
    
    If session_id is provided, also performs market making after each prediction:
    - Cancels existing orders for this trader
    - Places new bid/ask orders around the prediction
    - Triggers order matching atomically
    """
    tracked = target_username or USER_ACCOUNT_MAPPINGS.get(user, user)
    
    # Determine trader_name - must match trader_name enum in DB
    # User agents use their user key as trader_name
    trader_name = user if user in ['oliver', 'owen', 'skylar', 'tyler'] else None
    
    # Initialize market maker if session provided
    market_maker: Optional[SupabaseMarketMaker] = None
    if session_id and trader_name:
        market_maker = SupabaseMarketMaker()
    
    print("\n" + "=" * 70)
    print("📡 CONTINUOUS POLLING MODE" + (" (with trading)" if market_maker else ""))
    print("=" * 70)
    print(f"User agent: {user}")
    print(f"Tracking: @{tracked}")
    if market_maker:
        print(f"Session ID: {session_id}")
        print(f"Trader name: {trader_name}")
        print(f"Market making spread: {spread} (bid @ pred-{spread//2}, ask @ pred+{spread//2})")
        print(f"Order quantity: {quantity}")
    print(f"Polling interval: {interval_seconds}s")
    print("Press Ctrl+C to stop.")
    print("=" * 70 + "\n")

    agent = UserAgent(
        name=user,
        target_username=target_username,
        max_posts_to_fetch=50,
        max_posts_to_return=15,
        lookback_days=7,
    )

    round_number = 1
    try:
        while True:
            start_ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{start_ts}] 🔄 Round {round_number}...")
            
            try:
                # Get market data (may include live orderbook if market_maker exists)
                data_or_coro = market_data_provider()
                market_data = await data_or_coro if asyncio.iscoroutine(data_or_coro) else data_or_coro
                
                # If we have market maker, fetch live orderbook data
                if market_maker and session_id:
                    orderbook = market_maker.get_orderbook(session_id)
                    recent_trades = market_maker.get_recent_trades(session_id, limit=5)
                    market_data["order_book"] = orderbook
                    market_data["recent_trades"] = recent_trades
                
                # Run prediction
                result = await agent.execute(market_data)
                
                if result.get("skipped"):
                    print(f"[{start_ts}] ⏭️  no new posts for @{tracked}")
                else:
                    prediction = result.get("prediction", 50)
                    signal = result.get("signal", "uncertain")
                    posts = result.get("posts_analyzed", 0)
                    
                    print(f"[{start_ts}] 🎯 prediction={prediction}% signal={signal} posts={posts}")
                    
                    # Market making - atomically cancel, place, and match
                    if market_maker and session_id and trader_name:
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
                    
                    # Print summary
                    print(json.dumps({
                        "round": round_number,
                        "prediction": prediction,
                        "signal": signal,
                        "posts_analyzed": posts,
                        "analysis": result.get("analysis", "")[:200] + "...",
                    }, indent=2, ensure_ascii=False))
                
                round_number += 1
                
            except Exception as e:
                print(f"[{start_ts}] ❌ Round failed: {e}")
                logger.exception("Round failed")
            
            await asyncio.sleep(interval_seconds)
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Polling stopped by user.")
    finally:
        # Clean up - cancel any remaining orders
        if market_maker and session_id and trader_name:
            print(f"🧹 Cleaning up: cancelling orders for {trader_name}...")
            cancelled = market_maker.cancel_all_orders(session_id, trader_name)
            print(f"   Cancelled {cancelled} orders.")


async def main():
    """Main entry point"""
    args = parse_args()
    
    # List users mode
    if args.list_users:
        print("\n📋 CONFIGURED USER AGENTS:")
        print("-" * 40)
        for user, account in USER_ACCOUNT_MAPPINGS.items():
            print(f"  {user:<15} → @{account}")
        print("\nUse --user <name> to run a specific user agent")
        print("Use --username <handle> to track a custom account")
        return
    
    # Enable verbose logging if requested
    if args.verbose:
        logging.getLogger("httpx").setLevel(logging.INFO)
        logging.getLogger("app.agents.base").setLevel(logging.INFO)
        logging.getLogger("app.services.grok").setLevel(logging.INFO)
        logging.getLogger("app.traders.user_agent").setLevel(logging.INFO)
        logging.getLogger("x_search").setLevel(logging.INFO)
    
    # Check for required env vars
    if not os.getenv("GROK_API_KEY"):
        logger.error("❌ GROK_API_KEY not set. Add it to ../.env")
        sys.exit(1)
    
    if not os.getenv("X_BEARER_TOKEN"):
        logger.warning("⚠️  X_BEARER_TOKEN not set. API calls will fail.")
        logger.warning("   Add X_BEARER_TOKEN to ../.env for full functionality")
    
    # Build market data
    market_data = SAMPLE_MARKET_DATA.copy()
    if args.question:
        market_data["market_topic"] = args.question
    
    question = market_data["market_topic"]
    
    # Require either --user, --all, or --username
    if not args.user and not args.all and not args.username:
        print("❌ Please specify --user <name>, --all, or --username <handle>")
        print(f"   Available users: {', '.join(get_user_agent_names())}")
        print("   Use --list-users to see all configured accounts")
        sys.exit(1)
    
    # Single user mode (polling or one-shot)
    if args.user or args.username:
        user = args.user or "custom"

        # Validate user if no explicit username
        if user != "custom" and user not in USER_ACCOUNT_MAPPINGS and not args.username:
            print(f"❌ Unknown user '{user}'. Available: {', '.join(get_user_agent_names())}")
            print("   Or use --username to track a custom account")
            sys.exit(1)

        tracked = args.username or USER_ACCOUNT_MAPPINGS.get(user, user)

        # Polling mode (periodic)
        if args.poll:
            # Warn if session not provided for trading
            if args.session and not args.no_trade:
                if user not in ['oliver', 'owen', 'skylar', 'tyler']:
                    print(f"⚠️  User '{user}' is not a valid trader_name enum value.")
                    print("   Trading will be disabled. Use one of: oliver, owen, skylar, tyler")
                    args.session = None
            
            await run_poll_mode(
                user=user,
                target_username=tracked,
                market_data_provider=lambda: market_data,
                interval_seconds=args.poll_interval,
                session_id=args.session if not args.no_trade else None,
                spread=args.spread,
                quantity=args.quantity,
            )
            return

        # One-shot mode
        await test_single_user(
            user=user,
            market_data=market_data,
            target_username=args.username,
        )
        return
    
    # All users mode
    if args.all:
        print("\n" + "=" * 80)
        print("🌐 RUNNING ALL USER AGENTS")
        print("=" * 80)
        print(f"Question: {question}")
        print(f"Users: {len(get_user_agent_names())}")
        print(f"Max concurrent: {args.concurrent}")
        print("=" * 80 + "\n")
        
        results = await run_all_users(
            market_data=market_data,
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
