"""
Noise Trader - Prediction market agent with X Search tool integration
Analyzes X/Twitter sentiment to generate probability predictions for prediction markets

Supports two modes:
1. Tool-based: Grok calls x_search tool directly (original behavior)
2. Semantic filter: Pre-filters tweets for relevance before prediction (recommended)
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

from x_search.communities import SPHERES, get_sphere, get_sphere_names
from x_search.tool import XSearchConfig

# Import semantic filter
from app.noise_traders.semantic_filter import (
    SemanticFilter,
    SemanticFilterConfig,
    SemanticFilterOutput,
)


class ReasonWithStrength(BaseModel):
    """A reason with its strength rating"""
    reason: str = Field(description="The reason")
    strength: int = Field(ge=1, le=10, description="Strength rating 1-10")


class NoiseTraderOutput(BaseModel):
    """Output schema for Noise Trader predictions - Superforecaster methodology"""
    
    # Core prediction
    prediction: int = Field(
        ge=0, le=100,
        description="Final probability 0-100 that the market resolves YES (calibrated, Brier-optimized)"
    )
    
    # Structured reasoning
    key_facts: list[str] = Field(
        default_factory=list,
        description="Core factual points extracted from background information and sources"
    )
    reasons_no: list[ReasonWithStrength] = Field(
        default_factory=list,
        description="Reasons why the answer might be NO, with strength ratings 1-10"
    )
    reasons_yes: list[ReasonWithStrength] = Field(
        default_factory=list,
        description="Reasons why the answer might be YES, with strength ratings 1-10"
    )
    
    # Analysis
    analysis: str = Field(
        description="Aggregated analysis of competing factors, bias adjustments, and key considerations"
    )
    initial_probability: int = Field(
        ge=0, le=100,
        description="Initial/tentative probability before reflection"
    )
    reflection: str = Field(
        description="Sanity checks, base rate considerations, and calibration adjustments"
    )
    
    # Metadata
    signal: str = Field(
        default="uncertain",
        description="Overall signal from X community: yes, no, uncertain, or mixed"
    )
    tweets_analyzed: int = Field(
        default=0,
        description="Number of tweets analyzed"
    )
    baseline_probability: int = Field(
        default=50,
        description="Market baseline probability. Do not rely on this as an anchor."
    )
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="Confidence in this prediction (based on evidence quality)"
    )


def get_x_search_tool():
    """Get x_search tool runner"""
    from x_search.tool import run_tool
    return run_tool


def _build_tool_definition(sphere_key: str) -> Dict[str, Any]:
    """Build tool definition for a specific sphere"""
    sphere = get_sphere(sphere_key)
    sphere_name = sphere.name if sphere else sphere_key
    sphere_vibe = sphere.vibe[:100] if sphere else "General discourse"
    
    return {
        "type": "function",
        "function": {
            "name": "x_search",
            "description": (
                f"Search tweets about the market topic from the {sphere_name} on X/Twitter. "
                f"Sphere vibe: {sphere_vibe}... "
                "Use this to gauge real-time signals and inform your probability prediction."
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


SUPERFORECASTER_SYSTEM_PROMPT = """You are an advanced AI forecasting system fine-tuned to provide calibrated probabilistic forecasts under uncertainty. Your performance is evaluated according to the Brier score.

CRITICAL CALIBRATION RULES:
- Do NOT treat 0.5% (1:199 odds) and 5% (1:19) as similarly "small" probabilities
- Do NOT treat 90% (9:1) and 99% (99:1) as similarly "high" probabilities  
- These represent markedly different odds - be precise with tail probabilities
- Your baseline is the current market price - do not rely on it as an anchor.

BIAS AWARENESS:
- News has negativity bias - doesn't represent overall trends or base rates
- News has sensationalism bias - dramatic/shocking stories are overrepresented
- Adjust for these biases when weighing evidence from social media

YOUR FORECASTING PROCESS:
1. Extract key facts from background information (no conclusions yet)
2. List reasons why the answer might be NO with strength ratings (1-10)
3. List reasons why the answer might be YES with strength ratings (1-10)
4. Aggregate considerations - how do competing factors interact?
5. Output initial probability
6. Reflect: sanity checks, base rates, calibration, over/underconfidence
7. Output final prediction

SPHERE OF INFLUENCE CONTEXT:
You are monitoring {sphere_name} on X.

{sphere_description}

Typical participants: {sphere_followers}
Core beliefs of this sphere: {sphere_beliefs}

Weight higher-relevance tweets more heavily. Consider source authority.
Be contrarian if evidence warrants it - don't anchor too heavily on market price."""


def _get_noise_trader_prompt(sphere_key: str, use_semantic_filter: bool = False) -> str:
    """Generate system prompt for a noise trader assigned to a sphere"""
    sphere = get_sphere(sphere_key)
    if sphere is None:
        # Fallback for unknown sphere
        return SUPERFORECASTER_SYSTEM_PROMPT.format(
            sphere_name=sphere_key,
            sphere_description="A sphere of influence on X.",
            sphere_followers="Various participants",
            sphere_beliefs="Diverse viewpoints",
        )
    
    return SUPERFORECASTER_SYSTEM_PROMPT.format(
        sphere_name=sphere.name,
        sphere_description=sphere.vibe,
        sphere_followers=sphere.followers,
        sphere_beliefs=sphere.core_beliefs,
    )


class NoiseTrader(BaseAgent):
    """
    Noise Trader - Prediction market agent assigned to a specific X sphere of influence
    
    Each NoiseTrader instance monitors one sphere and provides probability
    predictions based on sentiment analysis of that sphere's discourse.
    
    Supports two modes:
    - Tool mode (enable_tools=True, use_semantic_filter=False): Grok calls x_search directly
    - Semantic filter mode (use_semantic_filter=True): Pre-filters tweets for relevance (recommended)
    """

    def __init__(
        self,
        sphere: str,
        agent_name: str = None,
        phase: str = "prediction",
        max_retries: int = 3,
        timeout_seconds: int = 300,
        enable_tools: bool = True,
        use_semantic_filter: bool = True,  # New: use semantic filtering by default
        semantic_filter_config: SemanticFilterConfig | None = None,
    ):
        # Validate sphere
        if sphere not in SPHERES:
            valid = ", ".join(SPHERES.keys())
            raise ValueError(f"Invalid sphere '{sphere}'. Valid options: {valid}")
        
        self.sphere = sphere
        self._sphere_data = get_sphere(sphere)
        self._use_semantic_filter = use_semantic_filter
        
        # Auto-generate agent name if not provided
        if agent_name is None:
            agent_name = f"noise_trader_{sphere}"
        
        super().__init__(
            agent_name=agent_name,
            phase=phase,
            system_prompt=_get_noise_trader_prompt(sphere, use_semantic_filter),
            output_schema=NoiseTraderOutput,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds
        )
        
        self._tools_enabled = enable_tools and not use_semantic_filter
        self._tool_definition = _build_tool_definition(sphere)
        
        # Initialize semantic filter if enabled
        if use_semantic_filter:
            self._semantic_filter = SemanticFilter(
                config=semantic_filter_config or SemanticFilterConfig(
                    max_tweets_to_fetch=50,
                    max_tweets_to_return=15,
                    min_relevance_score=0.3,
                    lookback_days=7,
                )
            )
        else:
            self._semantic_filter = None

    async def build_user_message(
        self, 
        input_data: Dict[str, Any],
        filtered_tweets: SemanticFilterOutput | None = None,
    ) -> str:
        """
        Build user message in superforecaster format
        
        Expected input_data keys:
            - market_topic: str - The prediction market question
            - resolution_criteria: str - How the market resolves (optional)
            - resolution_date: str - When the market resolves (optional)
            - order_book: dict - Current bids and asks
            - recent_trades: list - Last 5 trades
        
        Args:
            input_data: Market data dictionary
            filtered_tweets: Pre-filtered tweets from semantic filter (optional)
        """
        market_topic = input_data.get("market_topic", "")
        resolution_criteria = input_data.get("resolution_criteria", "Standard YES/NO resolution based on outcome occurrence.")
        resolution_date = input_data.get("resolution_date", "Not specified")
        order_book = input_data.get("order_book", {})
        recent_trades = input_data.get("recent_trades", [])
        
        # Calculate baseline from order book
        bids = order_book.get("bids", [])
        asks = order_book.get("asks", [])
        baseline_probability = 50  # Default
        
        if bids and asks:
            best_bid = max(b.get("price", 0) for b in bids)
            best_ask = min(a.get("price", 1) for a in asks)
            mid_price = (best_bid + best_ask) / 2
            baseline_probability = int(mid_price * 100) if mid_price <= 1 else int(mid_price)
        elif bids:
            best_bid = max(b.get("price", 0) for b in bids)
            baseline_probability = int(best_bid * 100) if best_bid <= 1 else int(best_bid)
        elif asks:
            best_ask = min(a.get("price", 1) for a in asks)
            baseline_probability = int(best_ask * 100) if best_ask <= 1 else int(best_ask)
        
        self._baseline_probability = baseline_probability
        
        # Format market data
        market_data_text = self._format_market_data(order_book, recent_trades)
        
        # Format background information from semantic filter
        if filtered_tweets and filtered_tweets.relevant_tweets:
            background_info = self._format_background_info(filtered_tweets)
        else:
            background_info = "No relevant tweets found from the monitored community. Limited background information available."
        
        # Current date
        current_date = datetime.now(UTC).strftime("%Y-%m-%d")
        
        # Get sphere name for display
        sphere_name = self._sphere_data.name if self._sphere_data else self.sphere.upper()
        
        # Build superforecaster-style message
        message = f"""FORECAST QUESTION: {market_topic}

RESOLUTION CRITERIA:
{resolution_criteria}

IMPORTANT: Today's date is {current_date}. Your pretraining knowledge may be outdated.

RESOLUTION DATE: {resolution_date}

BASELINE FORECAST (Current Market Price): {baseline_probability}%
This is the market's current implied probability. Do not rely on this as an anchor.

MARKET DATA:
{market_data_text}

BACKGROUND INFORMATION (from {sphere_name} on X):
{background_info}

Recall the question you are forecasting: {market_topic}

Please provide your forecast following the structured format:
1. Extract key facts from the background information (no conclusions yet)
2. List reasons why NO (with strength 1-10 for each)
3. List reasons why YES (with strength 1-10 for each)
4. Analyze how competing factors interact, adjust for news negativity/sensationalism bias
5. Output initial probability
6. Reflect: sanity checks, base rates, over/underconfidence, calibration
7. Output final prediction (0-100)
"""
        
        return message

    def _format_market_data(self, order_book: Dict, recent_trades: List) -> str:
        """Format order book and trades into readable text"""
        bids = order_book.get("bids", [])
        asks = order_book.get("asks", [])
        
        lines = []
        
        # Order book
        if bids:
            lines.append("BID ORDERS (betting YES):")
            for bid in bids[:3]:
                qty = bid.get("quantity", bid.get("qty", 0))
                price = bid.get("price", 0)
                prob = int(price * 100) if price <= 1 else int(price)
                lines.append(f"  {qty} shares @ {prob}%")
        
        if asks:
            lines.append("ASK ORDERS (betting NO):")
            for ask in asks[:3]:
                qty = ask.get("quantity", ask.get("qty", 0))
                price = ask.get("price", 0)
                prob = int(price * 100) if price <= 1 else int(price)
                lines.append(f"  {qty} shares @ {prob}%")
        
        # Recent trades
        if recent_trades:
            lines.append("\nRECENT TRADES:")
            for trade in recent_trades[:5]:
                side = trade.get("side", "unknown").upper()
                qty = trade.get("quantity", trade.get("qty", 0))
                price = trade.get("price", 0)
                prob = int(price * 100) if price <= 1 else int(price)
                time_ago = trade.get("time_ago", "recently")
                lines.append(f"  {side} {qty} @ {prob}% ({time_ago})")
        
        return "\n".join(lines) if lines else "No market data available."

    def _format_background_info(self, filtered: SemanticFilterOutput) -> str:
        """Format filtered tweets as background information"""
        lines = []
        
        # Summary
        lines.append(f"SUMMARY: {filtered.summary}")
        lines.append(f"Tweets Analyzed: {filtered.total_tweets_analyzed} total, {filtered.relevant_tweet_count} relevant")
        lines.append("")
        
        # Individual tweets
        lines.append("RELEVANT TWEETS:")
        for i, tweet in enumerate(filtered.relevant_tweets, 1):
            signal_str = tweet.signal.upper()
            lines.append(
                f"\n[{i}] {tweet.author} | Relevance: {tweet.relevance_score:.0%} | Signal: {signal_str}"
            )
            lines.append(f"    \"{tweet.text[:300]}{'...' if len(tweet.text) > 300 else ''}\"")
            lines.append(f"    Engagement: ❤️ {tweet.likes} 🔄 {tweet.retweets}")
            lines.append(f"    Why relevant: {tweet.relevance_reason}")
        
        return "\n".join(lines)

    async def _execute_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an x_search tool call for this trader's sphere"""
        args = json.loads(tool_call["function"]["arguments"])
        topic = args.get("topic", "")
        max_tweets = args.get("max_tweets", 25)
        
        # Build the actual x_search payload using this trader's sphere
        # Use a generic seed user since spheres don't have user lists
        start_time = (datetime.now(UTC) - timedelta(days=7)).isoformat()
        
        payload = {
            "topic": topic,
            "username": "x",  # Generic seed, actual search is topic-based
            "start_time": start_time,
            "max_tweets": max_tweets,
            "sphere": self.sphere,
            "lang": "en"
        }
        
        logger.info(f"Executing x_search for {self.sphere} sphere with topic: {topic}")
        
        try:
            # Pass bearer token from app config to x_search
            settings = get_settings()
            x_config = XSearchConfig(bearer_token=settings.x_bearer_token)
            
            run_tool = get_x_search_tool()
            result = await run_tool(payload, config=x_config)
            
            tweets = result.get("tweets", [])
            return {
                "success": True,
                "sphere": self.sphere,
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
            return {"success": False, "error": str(e), "sphere": self.sphere}

    async def execute(
        self,
        input_data: Dict[str, Any],
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Execute the noise trader to generate a prediction"""
        
        # Use semantic filter mode if enabled
        if self._use_semantic_filter:
            return await self._execute_with_semantic_filter(input_data, progress_callback)
        
        # Otherwise use tool-based mode
        if not self._tools_enabled:
            logger.info(f"NoiseTrader ({self.sphere}) running without tools")
            return await super().execute(input_data, progress_callback)
        
        return await self._execute_with_tools(input_data, progress_callback)

    async def _execute_with_semantic_filter(
        self,
        input_data: Dict[str, Any],
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Execute using semantic filter (recommended mode)"""
        self.status = "running"
        if progress_callback:
            await progress_callback(self.agent_name, "started")

        market_topic = input_data.get("market_topic", "")
        
        for attempt in range(self.max_retries):
            try:
                # Step 1: Get pre-filtered tweets via semantic filter
                logger.info(f"NoiseTrader ({self.sphere}) fetching filtered tweets...")
                filtered_tweets = await self._semantic_filter.filter(
                    question=market_topic,
                    sphere=self.sphere,
                )
                
                logger.info(
                    f"Semantic filter returned {filtered_tweets.relevant_tweet_count} relevant tweets "
                    f"(from {filtered_tweets.total_tweets_analyzed} total)"
                )
                
                # Step 2: Build user message with pre-filtered tweets
                user_message = await self.build_user_message(input_data, filtered_tweets)
                
                # Step 3: Get prediction from Grok (no tool calls needed)
                logger.info(f"NoiseTrader ({self.sphere}) getting prediction from Grok...")
                response = await asyncio.wait_for(
                    self.grok_service.chat_completion(
                        system_prompt=self.system_prompt,
                        user_message=user_message,
                        output_schema=self.output_schema,
                        temperature=0.5,
                    ),
                    timeout=self.timeout_seconds
                )
                
                self.tokens_used = response.get("total_tokens", 0)
                content = response.get("content", "{}")
                
                # Parse and validate output
                try:
                    raw_output = json.loads(content)
                except json.JSONDecodeError:
                    # Fallback for unparseable response
                    baseline = getattr(self, '_baseline_probability', 50)
                    raw_output = {
                        "prediction": baseline,
                        "key_facts": [],
                        "reasons_no": [],
                        "reasons_yes": [],
                        "analysis": content[:500] if content else "Unable to generate analysis",
                        "initial_probability": baseline,
                        "reflection": "Response could not be parsed",
                        "signal": "uncertain",
                        "tweets_analyzed": filtered_tweets.relevant_tweet_count,
                        "baseline_probability": baseline,
                        "confidence": 0.3,
                    }
                
                # Ensure metadata fields are populated
                if "tweets_analyzed" not in raw_output or raw_output["tweets_analyzed"] == 0:
                    raw_output["tweets_analyzed"] = filtered_tweets.relevant_tweet_count
                if "baseline_probability" not in raw_output:
                    raw_output["baseline_probability"] = getattr(self, '_baseline_probability', 50)
                if "signal" not in raw_output:
                    raw_output["signal"] = "uncertain"
                
                validated_output = self.output_schema(**raw_output)
                self.output_data = validated_output.model_dump()
                self.status = "completed"
                
                if progress_callback:
                    await progress_callback(self.agent_name, "completed", self.output_data)
                
                logger.info(f"NoiseTrader ({self.sphere}) prediction: {self.output_data['prediction']}%")
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

    async def _execute_with_tools(
        self,
        input_data: Dict[str, Any],
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Execute using tool calls (original mode)"""
        self.status = "running"
        if progress_callback:
            await progress_callback(self.agent_name, "started")

        for attempt in range(self.max_retries):
            try:
                user_message = await self.build_user_message(input_data)
                
                # Step 1: Call Grok with x_search tool
                logger.info(f"NoiseTrader ({self.sphere}) calling Grok with tools...")
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
                                logger.info(f"x_search returned {result.get('tweet_count', 0)} tweets for {self.sphere}")
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
                    raw_output = {
                        "prediction": 50,
                        "key_facts": [],
                        "reasons_no": [],
                        "reasons_yes": [],
                        "analysis": content[:500] if content else "Unable to generate analysis",
                        "initial_probability": 50,
                        "reflection": "Response could not be parsed",
                        "signal": "uncertain",
                        "tweets_analyzed": 0,
                        "baseline_probability": 50,
                        "confidence": 0.3,
                    }
                
                validated_output = self.output_schema(**raw_output)
                self.output_data = validated_output.model_dump()
                self.status = "completed"
                
                if progress_callback:
                    await progress_callback(self.agent_name, "completed", self.output_data)
                
                logger.info(f"NoiseTrader ({self.sphere}) prediction: {self.output_data['prediction']}%")
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


# Backwards compatibility aliases
NoiseAgent = NoiseTrader

# Legacy parameter name support - allow 'community' as alias for 'sphere'
def create_noise_trader(community: str = None, sphere: str = None, **kwargs) -> NoiseTrader:
    """Factory function supporting both 'community' and 'sphere' parameter names."""
    sphere_key = sphere or community
    if not sphere_key:
        raise ValueError("Either 'sphere' or 'community' must be provided")
    return NoiseTrader(sphere=sphere_key, **kwargs)
