#!/usr/bin/env python3
"""
Test script for NoiseTrader prediction market agent

Usage:
    cd backend
    uv run python scripts/test_noise_agent.py

Requires:
    - X_BEARER_TOKEN in .env (for X API)
    - GROK_API_KEY in .env (for Grok)
"""
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# Sample market data for testing
SAMPLE_MARKET_DATA = {
    "market_topic": "Will the Federal Reserve cut interest rates in January 2025?",
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


async def test_noise_trader(community: str, market_data: dict):
    """Test the NoiseTrader with a specific community and market data"""
    
    logger.info("=" * 60)
    logger.info(f"Testing NoiseTrader")
    logger.info(f"Community: {community}")
    logger.info(f"Market: {market_data['market_topic']}")
    logger.info("=" * 60)
    
    # Create trader assigned to this community
    trader = NoiseTrader(community=community, enable_tools=True)
    
    try:
        result = await trader.execute(market_data)
        
        print("\n" + "=" * 60)
        print(f"📊 NOISE TRADER PREDICTION ({community})")
        print("=" * 60)
        print(f"\n🎯 Prediction: {result['prediction']}%")
        print(f"🎭 Sentiment: {result['sentiment']}")
        print(f"📈 Tweets analyzed: {result['tweets_analyzed']}")
        print(f"🔒 Confidence: {result['confidence']:.0%}")
        print(f"\n📝 Reasoning:\n{result['reasoning']}")
        print(f"\n💰 Tokens used: {trader.tokens_used}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Trader failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Main entry point"""
    # Check for required env vars
    if not os.getenv("GROK_API_KEY"):
        logger.error("❌ GROK_API_KEY not set. Add it to ../.env")
        sys.exit(1)
    
    if not os.getenv("X_BEARER_TOKEN"):
        logger.warning("⚠️  X_BEARER_TOKEN not set. Tool calls will fail.")
        logger.warning("   Add X_BEARER_TOKEN to ../.env for full functionality")

    # Test with tech_vc community (most likely to have opinions on Fed rates)
    await test_noise_trader(
        community="tech_vc",
        market_data=SAMPLE_MARKET_DATA
    )
    
    print("\n" + "=" * 60 + "\n")
    
    # Uncomment to test with other communities:
    # await test_noise_trader(
    #     community="news_media",
    #     market_data=SAMPLE_MARKET_DATA
    # )


if __name__ == "__main__":
    asyncio.run(main())
