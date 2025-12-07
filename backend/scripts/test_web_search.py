"""
Test script for Grok web search functionality
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try parent directory
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.grok import GrokService
from app.core.logging_config import get_logger

logger = get_logger(__name__)


async def test_web_search():
    """Test Grok web search with and without search_parameters"""
    
    grok = GrokService()
    test_query = "What are the latest developments in AI regulation in 2024?"
    
    print("=" * 60)
    print("Testing Grok Web Search")
    print("=" * 60)
    
    # Test 1: Without web search
    print("\n1. Testing WITHOUT web search:")
    print("-" * 60)
    try:
        response_no_search = await grok.chat_completion(
            system_prompt="You are a helpful assistant.",
            user_message=test_query,
            enable_web_search=False
        )
        print(f"✅ Response received")
        print(f"   Tokens: {response_no_search.get('total_tokens', 'N/A')}")
        print(f"   Content preview: {response_no_search.get('content', '')[:200]}...")
        print(f"   Sources used: {response_no_search.get('num_sources_used', 'N/A')}")
        print(f"   Web search indicators: {response_no_search.get('web_search_indicators', 'None')}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    await asyncio.sleep(2)
    
    # Test 2: With web search
    print("\n2. Testing WITH web search (search_parameters enabled):")
    print("-" * 60)
    try:
        response_with_search = await grok.chat_completion(
            system_prompt="You are a helpful assistant with access to web search.",
            user_message=test_query,
            enable_web_search=True
        )
        print(f"✅ Response received")
        print(f"   Tokens: {response_with_search.get('total_tokens', 'N/A')}")
        print(f"   Content preview: {response_with_search.get('content', '')[:200]}...")
        print(f"   Sources used: {response_with_search.get('num_sources_used', 'N/A')}")
        print(f"   Web search indicators: {response_with_search.get('web_search_indicators', 'None')}")
        
        # Check if response mentions sources or URLs
        content = response_with_search.get('content', '')
        has_urls = 'http' in content.lower()
        has_sources = 'source' in content.lower() or 'according to' in content.lower()
        print(f"   Contains URLs: {has_urls}")
        print(f"   Mentions sources: {has_sources}")
        
        # Show full response structure for debugging
        print(f"\n   Full response keys: {list(response_with_search.keys())}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    # Check for API key
    if not os.getenv("GROK_API_KEY"):
        print("❌ Error: GROK_API_KEY not found in environment")
        print("   Set it in backend/.env or export GROK_API_KEY=your-key")
        sys.exit(1)
    
    asyncio.run(test_web_search())

