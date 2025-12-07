#!/usr/bin/env python3
"""
Test script for the semantic filter.

Usage:
    cd backend
    uv run python scripts/test_semantic_filter.py
    
    # Or with custom question:
    uv run python scripts/test_semantic_filter.py --question "Will Trump win 2024?" --sphere "america_first"
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.noise_traders.semantic_filter import (
    SemanticFilter,
    SemanticFilterConfig,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_semantic_filter(
    question: str,
    sphere: str,
    topic: str | None = None,
    max_tweets: int = 150,
):
    """Run semantic filter test"""
    print(f"\n{'='*60}")
    print(f"SEMANTIC FILTER TEST")
    print(f"{'='*60}")
    print(f"Question: {question}")
    print(f"Sphere: {sphere}")
    print(f"Topic override: {topic or '(auto-extracted)'}")
    print(f"Max tweets to fetch: {max_tweets}")
    print(f"{'='*60}\n")

    config = SemanticFilterConfig(
        max_tweets_to_fetch=max_tweets,
        max_tweets_to_return=15,
        min_relevance_score=0.3,
        lookback_days=7,
        verified_only=False,  # Don't restrict - sphere filter handles quality
    )

    try:
        # Create filter instance
        semantic_filter = SemanticFilter(config=config)
        
        # Step 1: Fetch raw tweets
        print("📡 Fetching tweets...")
        raw_tweets = await semantic_filter._fetch_tweets(question, sphere, topic)
        print(f"   Fetched {len(raw_tweets)} raw tweets")
        
        if not raw_tweets:
            print("\n⚠️ No tweets found for this query.")
            return None
        
        # Step 2: Run semantic filter
        print("🧠 Running semantic filter...")
        result = await semantic_filter._semantic_filter(question, raw_tweets)
        
        # Build set of relevant tweet authors+text for comparison
        # Normalize text by removing extra whitespace for comparison
        def normalize(text: str) -> str:
            return " ".join(text.split())[:80]
        
        relevant_keys = {
            (t.author.lstrip("@").lower(), normalize(t.text))
            for t in result.relevant_tweets
        }
        
        # Find filtered out tweets
        filtered_out = [
            t for t in raw_tweets 
            if (t.get("author_username", "").lower(), normalize(t.get("text", ""))) not in relevant_keys
        ]

        print(f"\n📊 RESULTS")
        print(f"{'─'*60}")
        print(f"Total tweets analyzed: {result.total_tweets_analyzed}")
        print(f"Relevant tweets found: {result.relevant_tweet_count}")
        print(f"Filtered out: {len(filtered_out)}")
        
        print(f"\n📝 SUMMARY")
        print(f"{'─'*60}")
        print(result.summary)

        if result.relevant_tweets:
            print(f"\n✅ RELEVANT TWEETS ({len(result.relevant_tweets)})")
            print(f"{'─'*60}")
            for i, tweet in enumerate(result.relevant_tweets, 1):
                timestamp = tweet.created_at[:16].replace("T", " ") if tweet.created_at else "unknown"
                print(f"\n[{i}] @{tweet.author}")
                print(f"    📅 {timestamp} | Relevance: {tweet.relevance_score:.0%} | ❤️ {tweet.likes} | 🔄 {tweet.retweets}")
                print(f"    \"{tweet.text[:200]}{'...' if len(tweet.text) > 200 else ''}\"")
                print(f"    → {tweet.relevance_reason}")
        else:
            print("\n⚠️ No relevant tweets found.")

        # Show filtered out tweets
        if filtered_out:
            print(f"\n❌ FILTERED OUT ({len(filtered_out)})")
            print(f"{'─'*60}")
            for i, tweet in enumerate(filtered_out, 1):
                author = tweet.get("author_username", "unknown")
                text = tweet.get("text", "")[:150]
                likes = tweet.get("like_count", 0)
                retweets = tweet.get("retweet_count", 0)
                created_at = str(tweet.get("created_at", ""))[:16].replace("T", " ")
                print(f"\n[{i}] @{author}")
                print(f"    📅 {created_at} | ❤️ {likes} | 🔄 {retweets}")
                print(f"    \"{text}{'...' if len(tweet.get('text', '')) > 150 else ''}\"")

        print(f"\n{'='*60}")
        return result

    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        raise


def main():
    parser = argparse.ArgumentParser(description="Test the semantic filter")
    parser.add_argument(
        "--question",
        type=str,
        default="Will the Federal Reserve cut interest rates in December 2025?",
        help="Prediction market question to analyze",
    )
    parser.add_argument(
        "--sphere",
        type=str,
        default="academic_research",
        choices=[
            "eacc_sovereign", "america_first", "blue_establishment", "progressive_left",
            "optimizer_idw", "fintwit_market", "builder_engineering", "academic_research",
            "osint_intel",
        ],
        help="Sphere of influence to search",
    )
    parser.add_argument(
        "--topic",
        type=str,
        default=None,
        help="Optional topic override (otherwise auto-extracted from question)",
    )
    parser.add_argument(
        "--max-tweets",
        type=int,
        default=100,
        help="Maximum tweets to fetch from x_search (keyword search, filtered by sphere)",
    )
    
    args = parser.parse_args()

    asyncio.run(
        test_semantic_filter(
            question=args.question,
            sphere=args.sphere,
            topic=args.topic,
            max_tweets=args.max_tweets,
        )
    )


if __name__ == "__main__":
    main()
