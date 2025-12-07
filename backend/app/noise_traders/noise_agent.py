"""
Noise Trader - Prediction market agent with X Search tool integration
Analyzes X/Twitter sentiment to generate probability predictions for prediction markets
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent
from app.core.config import get_settings
from datetime import datetime, timedelta, UTC
import json
import logging
import asyncio
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


# Add x_search to path for imports
_x_search_path = Path(__file__).parent.parent.parent.parent
if str(_x_search_path) not in sys.path:
    sys.path.insert(0, str(_x_search_path))

from x_search.communities import COMMUNITIES, get_community_users
from x_search.tool import XSearchConfig


class NoiseTraderOutput(BaseModel):
    """Output schema for Noise Trader predictions"""
    prediction: int = Field(
        ge=0, le=100,
        description="Probability 0-100 that the market resolves YES"
    )
    reasoning: str = Field(
        description="Brief explanation of the prediction based on X sentiment"
    )
    sentiment: str = Field(
        default="neutral",
        description="Overall X sentiment: bullish, bearish, neutral, mixed"
    )
    tweets_analyzed: int = Field(
        default=0,
        description="Number of tweets analyzed"
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence in this prediction (based on tweet volume and consistency)"
    )


def get_x_search_tool():
    """Get x_search tool runner"""
    from x_search.tool import run_tool
    return run_tool


def _build_tool_definition(community: str) -> Dict[str, Any]:
    """Build tool definition for a specific community"""
    community_users = get_community_users(community)
    first_user = community_users[0] if community_users else "elonmusk"
    
    return {
        "type": "function",
        "function": {
            "name": "x_search",
            "description": (
                f"Search tweets about the market topic from the {community} community on X/Twitter. "
                f"This searches accounts like: {', '.join(community_users[:5])}... "
                "Use this to gauge real-time sentiment and inform your probability prediction."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Topic or keywords to search for (derived from market question)"
                    },
                    "max_tweets": {
                        "type": "integer",
                        "minimum": 10,
                        "maximum": 50,
                        "default": 25,
                        "description": "Maximum tweets to return"
                    }
                },
                "required": ["topic"]
            }
        }
    }


def _get_noise_trader_prompt(community: str) -> str:
    """Generate system prompt for a noise trader assigned to a community"""
    community_users = get_community_users(community)
    
    return f"""You are a Noise Trader - an AI agent that trades on prediction markets by analyzing X/Twitter sentiment.

You are assigned to monitor the **{community}** community on X, which includes voices like:
{', '.join(f'@{u}' for u in community_users[:8])}

YOUR TASK:
1. You will receive a prediction market question, the current order book, and recent trades
2. Use the x_search tool to find relevant tweets from your assigned community
3. Analyze the sentiment and what influential voices are saying
4. Output a probability prediction (0-100) for whether the market resolves YES

UNDERSTANDING THE ORDER BOOK:
- Prices represent implied probabilities (e.g., $0.65 = 65% chance of YES)
- Buy orders (bids) = people wanting to bet YES at that price
- Sell orders (asks) = people wanting to bet NO at that price  
- The spread between best bid and ask shows market uncertainty
- Recent trades show which direction momentum is moving

YOUR OUTPUT:
- prediction: Your probability estimate (0-100) that the market resolves YES
- reasoning: Brief explanation citing specific tweets or voices
- sentiment: Overall community sentiment (bullish/bearish/neutral/mixed)
- confidence: How confident you are (based on tweet volume and consistency)

Be contrarian if the data suggests it - don't just follow the current market price.
Base your prediction on actual tweet content, not assumptions."""


class NoiseTrader(BaseAgent):
    """
    Noise Trader - Prediction market agent assigned to a specific X community
    
    Each NoiseTrader instance monitors one community and provides probability
    predictions based on sentiment analysis of that community's tweets.
    """

    def __init__(
        self,
        community: str,
        agent_name: str = None,
        phase: str = "prediction",
        max_retries: int = 3,
        timeout_seconds: int = 300,
        enable_tools: bool = True
    ):
        # Validate community
        if community not in COMMUNITIES:
            valid = ", ".join(COMMUNITIES.keys())
            raise ValueError(f"Invalid community '{community}'. Valid options: {valid}")
        
        self.community = community
        
        # Auto-generate agent name if not provided
        if agent_name is None:
            agent_name = f"noise_trader_{community}"
        
        super().__init__(
            agent_name=agent_name,
            phase=phase,
            system_prompt=_get_noise_trader_prompt(community),
            output_schema=NoiseTraderOutput,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds
        )
        
        self._tools_enabled = enable_tools
        self._tool_definition = _build_tool_definition(community)
        self._community_users = get_community_users(community)

    async def build_user_message(self, input_data: Dict[str, Any]) -> str:
        """
        Build user message from market data
        
        Expected input_data keys:
            - market_topic: str - The prediction market question
            - order_book: dict - Current bids and asks
            - recent_trades: list - Last 5 trades
        """
        market_topic = input_data.get("market_topic", "")
        order_book = input_data.get("order_book", {})
        recent_trades = input_data.get("recent_trades", [])
        
        # Format order book in LLM-friendly prose
        bids = order_book.get("bids", [])
        asks = order_book.get("asks", [])
        
        order_book_text = "CURRENT ORDER BOOK:\n"
        
        if bids:
            order_book_text += "Buy orders (people betting YES):\n"
            for bid in bids[:5]:
                qty = bid.get("quantity", bid.get("qty", 0))
                price = bid.get("price", 0)
                implied_prob = int(price * 100) if price <= 1 else int(price)
                order_book_text += f"  - {qty} shares at ${price:.2f} (implies {implied_prob}% probability)\n"
        else:
            order_book_text += "Buy orders: None\n"
        
        if asks:
            order_book_text += "Sell orders (people betting NO):\n"
            for ask in asks[:5]:
                qty = ask.get("quantity", ask.get("qty", 0))
                price = ask.get("price", 0)
                implied_prob = int(price * 100) if price <= 1 else int(price)
                order_book_text += f"  - {qty} shares at ${price:.2f} (implies {implied_prob}% probability)\n"
        else:
            order_book_text += "Sell orders: None\n"
        
        # Calculate current market price from order book
        if bids and asks:
            best_bid = max(b.get("price", 0) for b in bids)
            best_ask = min(a.get("price", 1) for a in asks)
            mid_price = (best_bid + best_ask) / 2
            order_book_text += f"\nCurrent market price: ~${mid_price:.2f} (market thinks {int(mid_price * 100)}% likely)\n"
        
        # Format recent trades
        trades_text = "RECENT TRADES (last 5):\n"
        if recent_trades:
            for i, trade in enumerate(recent_trades[:5], 1):
                side = trade.get("side", "unknown").upper()
                qty = trade.get("quantity", trade.get("qty", 0))
                price = trade.get("price", 0)
                time_ago = trade.get("time_ago", "recently")
                signal = "bullish signal" if side == "BUY" else "bearish signal"
                trades_text += f"  {i}. {side} {qty} shares at ${price:.2f} ({time_ago}) - {signal}\n"
        else:
            trades_text += "  No recent trades\n"
        
        # Build the complete message
        message = f"""MARKET QUESTION: {market_topic}

{order_book_text}
{trades_text}

Search the {self.community} community on X for tweets related to this topic.
Based on what influential voices are saying, provide your probability prediction (0-100).
"""
        
        return message

    async def _execute_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an x_search tool call for this trader's community"""
        args = json.loads(tool_call["function"]["arguments"])
        topic = args.get("topic", "")
        max_tweets = args.get("max_tweets", 25)
        
        # Build the actual x_search payload using this trader's community
        first_user = self._community_users[0] if self._community_users else "elonmusk"
        start_time = (datetime.now(UTC) - timedelta(days=7)).isoformat()
        
        payload = {
            "topic": topic,
            "username": first_user,
            "start_time": start_time,
            "max_tweets": max_tweets,
            "community": self.community,
            "lang": "en"
        }
        
        logger.info(f"Executing x_search for {self.community} community with topic: {topic}")
        
        try:
            # Pass bearer token from app config to x_search
            settings = get_settings()
            x_config = XSearchConfig(bearer_token=settings.x_bearer_token)
            
            run_tool = get_x_search_tool()
            result = await run_tool(payload, config=x_config)
            
            tweets = result.get("tweets", [])
            return {
                "success": True,
                "community": self.community,
                "topic": result.get("topic"),
                "tweet_count": len(tweets),
                "tweets": [
                    {
                        "author": f"@{t['author_username']}",
                        "text": t["text"][:300],
                        "likes": t.get("like_count", 0),
                        "retweets": t.get("retweet_count", 0),
                    }
                    for t in tweets[:15]
                ]
            }
        except Exception as e:
            logger.error(f"x_search tool failed: {e}")
            return {"success": False, "error": str(e), "community": self.community}

    async def execute(
        self,
        input_data: Dict[str, Any],
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Execute the noise trader to generate a prediction"""
        
        if not self._tools_enabled:
            logger.info(f"NoiseTrader ({self.community}) running without tools")
            return await super().execute(input_data, progress_callback)
        
        self.status = "running"
        if progress_callback:
            await progress_callback(self.agent_name, "started")

        for attempt in range(self.max_retries):
            try:
                user_message = await self.build_user_message(input_data)
                
                # Step 1: Call Grok with x_search tool
                logger.info(f"NoiseTrader ({self.community}) calling Grok...")
                response = await asyncio.wait_for(
                    self.grok_service.chat_completion(
                        system_prompt=self.system_prompt,
                        user_message=user_message,
                        tools=[self._tool_definition],
                        tool_choice="auto"
                    ),
                    timeout=self.timeout_seconds
                )
                
                self.tokens_used = response.get("total_tokens", 0)
                
                # Step 2: Handle tool calls if present
                if response.get("tool_calls"):
                    logger.info(f"Grok requested {len(response['tool_calls'])} tool call(s)")
                    
                    messages = [
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": user_message},
                        {
                            "role": "assistant",
                            "content": response.get("content"),
                            "tool_calls": response["tool_calls"]
                        }
                    ]
                    
                    # Execute tool calls
                    for tc in response["tool_calls"]:
                        if tc["function"]["name"] == "x_search":
                            result = await self._execute_tool_call(tc)
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": json.dumps(result)
                            })
                            
                            if result.get("success"):
                                logger.info(f"x_search returned {result.get('tweet_count', 0)} tweets from {self.community}")
                            else:
                                logger.warning(f"x_search failed: {result.get('error')}")
                    
                    # Step 3: Get final response with structured output
                    logger.info("Getting prediction from Grok...")
                    final_response = await asyncio.wait_for(
                        self.grok_service.chat_completion_with_messages(
                            messages=messages,
                            output_schema=self.output_schema,
                            tools=None
                        ),
                        timeout=self.timeout_seconds
                    )
                    
                    self.tokens_used += final_response.get("total_tokens", 0)
                    content = final_response.get("content", "{}")
                else:
                    content = response.get("content", "{}")
                
                # Parse and validate output
                try:
                    raw_output = json.loads(content)
                except json.JSONDecodeError:
                    # Fallback if response isn't valid JSON
                    raw_output = {
                        "prediction": 50,
                        "reasoning": content[:500] if content else "Unable to generate prediction",
                        "sentiment": "neutral",
                        "tweets_analyzed": 0,
                        "confidence": 0.3
                    }
                
                validated_output = self.output_schema(**raw_output)
                self.output_data = validated_output.model_dump()
                self.status = "completed"
                
                if progress_callback:
                    await progress_callback(self.agent_name, "completed", self.output_data)
                
                logger.info(f"NoiseTrader ({self.community}) prediction: {self.output_data['prediction']}%")
                return self.output_data

            except asyncio.TimeoutError:
                self.error_message = f"Timeout after {self.timeout_seconds}s"
                logger.warning(f"Attempt {attempt + 1} timed out")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue

            except Exception as e:
                self.error_message = str(e)
                logger.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue

        self.status = "failed"
        if progress_callback:
            await progress_callback(self.agent_name, "failed", {"error": self.error_message})
        
        raise Exception(f"Agent {self.agent_name} failed after {self.max_retries} attempts: {self.error_message}")


# Backwards compatibility alias
NoiseAgent = NoiseTrader
