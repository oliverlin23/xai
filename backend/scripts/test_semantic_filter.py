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

from app.agents.traders.semantic_filter import (
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
    max_tweets: int = 100,
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
        lookback_days=7,
    )

    try:
        # Create filter instance
        semantic_filter = SemanticFilter(config=config)
        
        # Run full filter pipeline
        print("📡 Running semantic filter...")
        result = await semantic_filter.filter(question, sphere, topic)

        print(f"\n📊 RESULTS: {result.relevant_tweet_count}/{result.total_tweets_analyzed} relevant")

        if result.tweets:
            print(f"\n✅ RELEVANT TWEETS ({len(result.tweets)})")
            print(f"{'─'*60}")
            for i, tweet in enumerate(result.tweets, 1):
                author = tweet.get("author", "unknown")
                text = tweet.get("text", "")
                likes = tweet.get("likes", 0)
                rts = tweet.get("retweets", 0)
                print(f"\n[{i}] {author} ({likes}L/{rts}RT)")
                print(f"    \"{text}\"")
        else:
            print("\n⚠️ No relevant tweets found.")

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
        help="Maximum tweets to fetch from x_search",
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
