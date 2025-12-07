#!/usr/bin/env python3
"""
Test script for NoiseAgent with grok_tool integration

This script demonstrates the NoiseAgent calling Grok with the 
grok_x_related_tweets tool to fetch real X/Twitter data.

Usage:
    cd backend
    uv run python scripts/test_noise_agent.py

Requires:
    - X_BEARER_TOKEN in .env (for X API)
    - GROK_API_KEY in .env (for Grok)
"""
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timedelta, UTC
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from dotenv import load_dotenv

# Load env from project root
load_dotenv(Path(__file__).parent.parent.parent / ".env")

from app.services.grok import GrokService
from grok_tool.tool import run_tool, GrokXToolConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# Tool definition for Grok (matches grok_tool MCP server)
GROK_X_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "grok_x_related_tweets",
        "description": (
            "Fetch tweets about a topic from a seed user and graph-adjacent accounts "
            "using the X API with popularity-based fan-out. Use this to get real-time "
            "social media sentiment and discussions about any topic."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic or boolean query to search within tweets"
                },
                "username": {
                    "type": "string",
                    "description": "Seed X username (without @) whose audience will be expanded"
                },
                "start_time": {
                    "type": "string",
                    "description": "ISO-8601 timestamp (UTC) to bound the search window"
                },
                "max_tweets": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 200,
                    "default": 10,
                    "description": "Maximum number of tweets to return"
                },
                "community": {
                    "type": "string",
                    "enum": ["tech_vc", "maga_populist", "progressive_left", "crypto_web3", 
                             "rationalist_ai", "manosphere_selfhelp", "media_journalism"],
                    "description": "Optional: Community sphere to also search for broader context"
                }
            },
            "required": ["topic", "username", "start_time"]
        }
    }
}


async def execute_grok_tool(tool_call: dict) -> dict:
    """Execute the grok_x_related_tweets tool and return results"""
    args = json.loads(tool_call["function"]["arguments"])
    
    logger.info(f"Executing grok_tool with args: {json.dumps(args, indent=2)}")
    
    try:
        # Call the actual grok_tool
        result = await run_tool(args)
        return {
            "success": True,
            "tweet_count": len(result.get("tweets", [])),
            "tweets": [
                {
                    "author": t["author_username"],
                    "text": t["text"][:200] + "..." if len(t["text"]) > 200 else t["text"],
                    "likes": t.get("like_count", 0),
                    "url": str(t["url"])
                }
                for t in result.get("tweets", [])[:5]  # Limit for readability
            ],
            "related_users": [u["username"] for u in result.get("related_users", [])[:5]]
        }
    except Exception as e:
        logger.error(f"Tool execution failed: {e}")
        return {"success": False, "error": str(e)}


async def run_noise_agent_with_tools(question: str, seed_username: str = "elonmusk"):
    """
    Run a conversation with Grok that can use the grok_x_related_tweets tool
    """
    grok = GrokService()
    
    # System prompt for the agent
    system_prompt = """You are an AI analyst with access to real-time X/Twitter data.

When asked about topics, trends, or public sentiment, use the grok_x_related_tweets tool 
to fetch actual tweets and analyze them.

Your analysis should:
1. Use the tool to gather real data when relevant
2. Summarize key themes and sentiments from the tweets
3. Identify notable voices or influencers discussing the topic
4. Provide a balanced, evidence-based assessment

Always cite specific tweets or users when making claims about public discourse."""

    # Build initial user message
    start_time = (datetime.now(UTC) - timedelta(days=7)).isoformat()
    user_message = f"""Analyze the following topic using real X/Twitter data:

Topic: {question}

Use the grok_x_related_tweets tool to search for relevant tweets. 
Suggested seed user: {seed_username}
Search from: {start_time}

Provide a comprehensive analysis of what people are saying about this topic."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]

    logger.info("=" * 60)
    logger.info(f"Question: {question}")
    logger.info("=" * 60)

    # Call Grok with tools
    logger.info("\n📤 Calling Grok with grok_x_related_tweets tool...")
    
    response = await grok.chat_completion_with_messages(
        messages=messages,
        tools=[GROK_X_TOOL_DEFINITION],
        tool_choice="auto"
    )

    logger.info(f"Tokens used: {response.get('total_tokens', 'N/A')}")

    # Check for tool calls
    if response.get("tool_calls"):
        logger.info(f"\n🔧 Grok requested {len(response['tool_calls'])} tool call(s)")
        
        # Add assistant message with tool calls
        messages.append({
            "role": "assistant",
            "content": response.get("content"),
            "tool_calls": response["tool_calls"]
        })

        # Execute each tool call
        for tc in response["tool_calls"]:
            func_name = tc["function"]["name"]
            logger.info(f"\n⚡ Executing: {func_name}")
            
            if func_name == "grok_x_related_tweets":
                result = await execute_grok_tool(tc)
                
                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result, indent=2)
                })
                
                if result.get("success"):
                    logger.info(f"✅ Found {result.get('tweet_count', 0)} tweets")
                else:
                    logger.error(f"❌ Tool failed: {result.get('error')}")

        # Get final response from Grok with tool results
        logger.info("\n📤 Getting final analysis from Grok...")
        
        final_response = await grok.chat_completion_with_messages(
            messages=messages,
            tools=None  # No more tool calls needed
        )
        
        logger.info(f"Additional tokens: {final_response.get('total_tokens', 'N/A')}")
        
        print("\n" + "=" * 60)
        print("📊 FINAL ANALYSIS")
        print("=" * 60)
        print(final_response.get("content", "No content returned"))
        
    else:
        # No tool calls, just return the response
        print("\n" + "=" * 60)
        print("📊 RESPONSE (no tools used)")
        print("=" * 60)
        print(response.get("content", "No content returned"))

    return response


async def main():
    """Main entry point"""
    # Check for required env vars
    if not os.getenv("GROK_API_KEY"):
        logger.error("❌ GROK_API_KEY not set. Add it to ../.env")
        sys.exit(1)
    
    if not os.getenv("X_BEARER_TOKEN"):
        logger.warning("⚠️  X_BEARER_TOKEN not set. Tool calls will fail.")
        logger.warning("   Add X_BEARER_TOKEN to ../.env for full functionality")

    # Example questions to test
    questions = [
        "What is the current sentiment about AI regulation?",
        # "How are people reacting to the latest crypto market moves?",
        # "What are tech VCs saying about the startup ecosystem?",
    ]

    for question in questions:
        try:
            await run_noise_agent_with_tools(
                question=question,
                seed_username="sama"  # Sam Altman as seed user
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())


