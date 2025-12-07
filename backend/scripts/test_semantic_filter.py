#!/usr/bin/env python3
"""
Test script for the semantic filter.

Usage:
    cd backend
    uv run python scripts/test_semantic_filter.py
    
    # Or with custom question:
    uv run python scripts/test_semantic_filter.py --question "Will Trump win 2024?" --community "maga_right"
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
    semantic_search,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_semantic_filter(
    question: str,
    community: str,
    topic: str | None = None,
    max_tweets: int = 30,
):
    """Run semantic filter test"""
    print(f"\n{'='*60}")
    print(f"SEMANTIC FILTER TEST")
    print(f"{'='*60}")
    print(f"Question: {question}")
    print(f"Community: {community}")
    print(f"Topic override: {topic or '(auto-extracted)'}")
    print(f"Max tweets to fetch: {max_tweets}")
    print(f"{'='*60}\n")

    config = SemanticFilterConfig(
        max_tweets_to_fetch=max_tweets,
        max_tweets_to_return=10,
        min_relevance_score=0.3,
        lookback_days=7,  # X API recent search max is 7 days
        include_replies=True,  # Replies often have good signal
    )

    try:
        result = await semantic_search(
            question=question,
            community=community,
            topic=topic,
            config=config,
        )

        print(f"\n📊 RESULTS")
        print(f"{'─'*60}")
        print(f"Total tweets analyzed: {result.total_tweets_analyzed}")
        print(f"Relevant tweets found: {result.relevant_tweet_count}")
        print(f"Overall sentiment: {result.overall_sentiment}")
        print(f"Confidence: {result.confidence:.2%}")
        
        print(f"\n📝 SUMMARY")
        print(f"{'─'*60}")
        print(result.summary)

        if result.relevant_tweets:
            print(f"\n🐦 RELEVANT TWEETS (top {len(result.relevant_tweets)})")
            print(f"{'─'*60}")
            for i, tweet in enumerate(result.relevant_tweets, 1):
                sentiment_emoji = {
                    "bullish": "🟢",
                    "bearish": "🔴", 
                    "neutral": "⚪",
                }.get(tweet.sentiment, "⚪")
                
                print(f"\n[{i}] {tweet.author} {sentiment_emoji} (relevance: {tweet.relevance_score:.2f})")
                print(f"    ❤️ {tweet.likes} | 🔄 {tweet.retweets}")
                print(f"    {tweet.text[:200]}{'...' if len(tweet.text) > 200 else ''}")
                print(f"    → {tweet.relevance_reason}")
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
        default="Will Bitcoin reach $100,000 by the end of 2025?",
        help="Prediction market question to analyze",
    )
    parser.add_argument(
        "--community",
        type=str,
        default="crypto_web3",
        choices=[
            "tech_vc", "maga_right", "progressive_left", "crypto_web3",
            "ai_ml", "podcast_media", "news_media", "world_leaders",
        ],
        help="Community to search",
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
        help="Maximum tweets to fetch from x_search (X API allows up to 100 per query)",
    )
    
    args = parser.parse_args()

    asyncio.run(
        test_semantic_filter(
            question=args.question,
            community=args.community,
            topic=args.topic,
            max_tweets=args.max_tweets,
        )
    )


if __name__ == "__main__":
    main()
