"""
User Agent - Prediction market agent that tracks a specific X account

Monitors posts from a specific X/Twitter account and uses that content
to generate probability predictions for prediction markets.

Unlike NoiseTrader which searches keywords across spheres, UserAgent
tracks a single account's posts as context for forecasting.

Notes are persisted in trader_state_live.system_prompt for continuity across rounds.
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from app.agents.base import BaseAgent
from app.core.config import get_settings
from app.services.grok import GrokService, GROK_MODEL_FAST
from app.db.repositories import TraderRepository
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

from x_search.tool import run_tool as x_search_run_tool, XSearchConfig


# Mapping from user agent names to their X/Twitter usernames
# Add mappings here for each user agent
USER_ACCOUNT_MAPPINGS: Dict[str, str] = {
    "oliver": "OliveeLin",  
    "owen": "OwenZhang159710",       
    "skylar": "SkylarWang15",  
    "tyler": "tyzchen", 
}


class UserAgentOutput(BaseModel):
    """Output schema for User Agent predictions - post-focused"""
    
    prediction: int = Field(
        ge=0, le=100,
        description="Final probability 0-100 that the market resolves YES (calibrated, Brier-optimized)"
    )
    
    analysis: str = Field(
        description="Aggregated analysis of competing factors, bias adjustments, and key considerations"
    )
    
    signal: str = Field(
        default="uncertain",
        description="Overall signal from tracked account: yes, no, uncertain, or mixed"
    )
    posts_analyzed: int = Field(
        default=0,
        description="Number of posts analyzed from the tracked account"
    )
    baseline_probability: int = Field(
        default=50,
        description="Market baseline probability. Do not rely on this as an anchor."
    )
    tracked_account: str = Field(
        default="",
        description="The X account being tracked"
    )
    
    # Memory for next round
    notes_for_next_round: str = Field(
        default="",
        description=(
            "Notes to yourself for the next trading round. Include: "
            "1) Key insights or patterns you noticed, "
            "2) What you were uncertain about that might clarify, "
            "3) Specific things to watch for in new information, "
            "4) Your current thesis and what would change your mind. "
            "This will be provided back to you in the next round."
        )
    )


USER_AGENT_SYSTEM_PROMPT = """You are forecasting based almost entirely on what the tracked user just posted on X.

Rules:
- Use only the post content given to you; do not invent context.
- Calibrate a probability from 0-100 for the market question.
- Keep the answer concise and focused on what the post implies.

Output must follow the provided JSON schema."""


class UserAccountFilter:
    """
    Filter that fetches posts from a specific X account.
    
    Similar to SemanticFilter but searches a specific user's timeline
    instead of keyword-based search across spheres.
    """
    
    def __init__(
        self,
        target_username: str,
        max_posts_to_fetch: int = 50,
        max_posts_to_return: int = 15,
        lookback_days: int = 7,
        include_replies: bool = True,
    ):
        self.target_username = target_username.lstrip("@")
        self.max_posts_to_fetch = max_posts_to_fetch
        self.max_posts_to_return = max_posts_to_return
        self.lookback_days = lookback_days
        self.include_replies = include_replies
        self.grok_service = GrokService(model=GROK_MODEL_FAST)
    
    async def fetch_posts(
        self,
        question: str,
    ) -> Dict[str, Any]:
        """
        Fetch recent posts from the target account.
        
        Args:
            question: The prediction market question (used to filter for relevance)
        
        Returns:
            Dict with posts and metadata
        """
        # Build x_search payload to get posts FROM the specific user
        start_time = datetime.now(UTC) - timedelta(days=self.lookback_days)
        
        # Extract keywords from question for topic filtering
        topic = await self._extract_topic(question)
        
        payload = {
            "topic": topic,
            "username": self.target_username,  # Key difference: search specific user
            "start_time": start_time.isoformat(),
            "max_tweets": self.max_posts_to_fetch,
            "lang": "en",
            "include_retweets": False,
            "include_replies": self.include_replies,
        }
        
        logger.info(f"Fetching posts from @{self.target_username} with topic: {topic[:50]}...")
        
        try:
            settings = get_settings()
            x_config = XSearchConfig(bearer_token=settings.x_bearer_token)
            
            result = await x_search_run_tool(payload, config=x_config)
            posts = result.get("tweets", [])
            
            logger.info(f"Fetched {len(posts)} posts from @{self.target_username}")
            
            # Format posts for output
            formatted_posts = [
                {
                    "id": post.get("id"),
                    "author": f"@{post.get('author_username', self.target_username)}",
                    "text": post.get("text", "")[:500],
                    "likes": post.get("like_count", 0),
                    "retweets": post.get("retweet_count", 0),
                    "created_at": str(post.get("created_at", "")),
                }
                for post in posts[:self.max_posts_to_return]
            ]
            
            return {
                "posts": formatted_posts,
                "total_fetched": len(posts),
                "target_account": f"@{self.target_username}",
                "latest_post_id": formatted_posts[0]["id"] if formatted_posts else None,
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch posts from @{self.target_username}: {e}")
            return {
                "posts": [],
                "total_fetched": 0,
                "target_account": f"@{self.target_username}",
                "error": str(e),
            }
    
    async def _extract_topic(self, question: str) -> str:
        """Extract topic keywords from the prediction question"""
        # Simple extraction - remove common prediction phrasing
        topic = question.lower()
        for phrase in [
            "will ", "would ", "does ", "is ", "are ", "can ", "should ",
            "by end of ", "by the end of ", "before ", "after ",
            "in 2024", "in 2025", "in 2026",
            "resolve yes", "resolve no", "?",
        ]:
            topic = topic.replace(phrase, " ")
        
        # Clean up and return
        words = topic.split()
        meaningful_words = [w for w in words if len(w) > 2][:10]
        
        if meaningful_words:
            return " OR ".join(meaningful_words)
        return topic.strip()


class UserAgent(BaseAgent):
    """
    User Agent - Prediction market agent that tracks a specific X account.
    
    Each UserAgent instance monitors one X account and provides probability
    predictions based on analysis of that account's posts.
    
    The tracked account is determined by the agent's name field, which maps
    to an X username via USER_ACCOUNT_MAPPINGS.
    
    Notes are persisted in trader_state_live.system_prompt for continuity across rounds.
    """
    
    def __init__(
        self,
        name: str,
        session_id: str | None = None,
        target_username: str | None = None,
        agent_name: str | None = None,
        phase: str = "prediction",
        max_retries: int = 3,
        timeout_seconds: int = 300,
        max_posts_to_fetch: int = 50,
        max_posts_to_return: int = 15,
        lookback_days: int = 7,
    ):
        """
        Initialize the User Agent.
        
        Args:
            name: User agent name (e.g., "oliver", "owen"). Used to look up X username.
            session_id: Optional session ID for DB persistence of notes.
            target_username: Optional explicit X username override. If not provided,
                           uses USER_ACCOUNT_MAPPINGS[name].
            agent_name: Optional custom agent name for logging. Defaults to "user_agent_{name}".
            phase: Agent phase (default "prediction").
            max_retries: Maximum retry attempts.
            timeout_seconds: Timeout for API calls.
            max_posts_to_fetch: Maximum posts to fetch from the account.
            max_posts_to_return: Maximum posts to include in context.
            lookback_days: How many days back to search for posts.
        """
        self.user_name = name.lower()
        self.session_id = session_id
        self.trader_name = name.lower()  # For user agents, trader_name = user name
        self._last_seen_post_id: str | None = None
        self._trader_repo = TraderRepository() if session_id else None
        self._previous_notes: str = ""
        
        # Determine target X username
        if target_username:
            self.target_username = target_username.lstrip("@")
        elif name.lower() in USER_ACCOUNT_MAPPINGS:
            self.target_username = USER_ACCOUNT_MAPPINGS[name.lower()]
        else:
            raise ValueError(
                f"Unknown user '{name}'. Either provide target_username or add to USER_ACCOUNT_MAPPINGS. "
                f"Known users: {', '.join(USER_ACCOUNT_MAPPINGS.keys())}"
            )
        
        # Auto-generate agent name if not provided
        if agent_name is None:
            agent_name = f"user_agent_{self.user_name}"
        
        # Build system prompt with target username
        system_prompt = USER_AGENT_SYSTEM_PROMPT.format(
            tracked_username=self.target_username
        )
        
        super().__init__(
            agent_name=agent_name,
            phase=phase,
            system_prompt=system_prompt,
            output_schema=UserAgentOutput,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds
        )
        
        # Initialize account filter
        self._account_filter = UserAccountFilter(
            target_username=self.target_username,
            max_posts_to_fetch=max_posts_to_fetch,
            max_posts_to_return=max_posts_to_return,
            lookback_days=lookback_days,
        )
    
    def load_previous_notes(self) -> str:
        """
        Load previous notes from trader_state_live.system_prompt.
        Returns empty string if no notes found or session_id not set.
        """
        if not self.session_id or not self._trader_repo:
            return self._previous_notes
        
        try:
            trader = self._trader_repo.get_trader(self.session_id, self.trader_name)
            if trader and trader.get("system_prompt"):
                notes = trader["system_prompt"]
                self._previous_notes = notes
                logger.info(f"UserAgent ({self.user_name}) loaded notes from DB ({len(notes)} chars)")
                return notes
        except Exception as e:
            logger.warning(f"Failed to load notes from DB: {e}")
        
        return self._previous_notes
    
    def save_notes(self, notes: str) -> bool:
        """
        Save notes to trader_state_live.system_prompt.
        Returns True if successful, False otherwise.
        """
        if not self.session_id:
            logger.warning(f"UserAgent ({self.user_name}) cannot save notes: no session_id")
            return False
        
        if not self._trader_repo:
            logger.warning(f"UserAgent ({self.user_name}) cannot save notes: no trader_repo")
            return False
        
        if not notes:
            logger.info(f"UserAgent ({self.user_name}) has no notes to save (model didn't generate notes_for_next_round)")
        
        try:
            result = self._trader_repo.save_system_prompt(
                session_id=self.session_id,
                trader_name=self.trader_name,
                system_prompt=notes
            )
            if result:
                logger.info(f"UserAgent ({self.user_name}) saved notes to DB ({len(notes)} chars)")
                return True
            else:
                # Try to create if doesn't exist
                self._trader_repo.upsert_trader(
                    session_id=self.session_id,
                    trader_name=self.trader_name,
                    trader_type="user",
                    system_prompt=notes
                )
                logger.info(f"UserAgent ({self.user_name}) created/updated trader with notes")
                return True
        except Exception as e:
            logger.error(f"UserAgent ({self.user_name}) failed to save notes: {e}")
            return False
    
    async def build_user_message(
        self,
        input_data: Dict[str, Any],
        fetched_posts: Dict[str, Any] | None = None,
    ) -> str:
        """
        Build a concise user message centered on the tracked user's posts.
        """
        posts = fetched_posts.get("posts", []) if fetched_posts else []
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
        
        # Format background information from fetched posts
        if posts:
            background_info = self._format_background_info(fetched_posts)
        else:
            background_info = f"No new posts from @{self.target_username}. Limited background information available."
        
        # Current date
        current_date = datetime.now(UTC).strftime("%Y-%m-%d")
        
        # Focused message on the user's latest posts
        message = f"""MARKET QUESTION: {market_topic}

TODAY: {current_date}
RESOLUTION: {resolution_date}
BASELINE (market): {baseline_probability}%

LATEST POSTS FROM @{self.target_username}:
{background_info}

INSTRUCTIONS:
- Use only what these posts imply about the market question.
- Return a calibrated probability 0-100 and brief reasoning tied directly to the posts."""
        
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
    
    def _format_background_info(self, fetched_posts: Dict[str, Any]) -> str:
        """Format fetched posts as background information"""
        posts = fetched_posts.get("posts", [])
        total_fetched = fetched_posts.get("total_fetched", 0)
        target_account = fetched_posts.get("target_account", f"@{self.target_username}")
        
        lines = []
        
        # Summary
        lines.append(f"Posts Retrieved: {len(posts)} shown (from {total_fetched} total)")
        lines.append("")
        
        # Individual posts
        lines.append("RECENT POSTS (ordered by recency):")
        for i, post in enumerate(posts, 1):
            author = post.get("author", target_account)
            text = post.get("text", "")
            likes = post.get("likes", 0)
            retweets = post.get("retweets", 0)
            
            lines.append(f"\n[{i}] {author} | ❤️ {likes} | 🔄 {retweets}")
            lines.append(f"    \"{text[:400]}{'...' if len(text) > 400 else ''}\"")
        
        return "\n".join(lines)
    
    async def execute(
        self,
        input_data: Dict[str, Any],
        progress_callback: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Execute the user agent to generate a prediction only when a new post is detected"""
        
        self.status = "running"
        if progress_callback:
            await progress_callback(self.agent_name, "started")
        
        # Load previous notes from DB if session_id is set
        if self.session_id:
            db_notes = self.load_previous_notes()
            if db_notes and "previous_notes" not in input_data:
                input_data["previous_notes"] = db_notes
        
        market_topic = input_data.get("market_topic", "")
        
        for attempt in range(self.max_retries):
            try:
                # Step 1: Fetch posts from the tracked account
                logger.info(f"UserAgent ({self.user_name}) fetching posts from @{self.target_username}...")
                fetched_posts = await self._account_filter.fetch_posts(
                    question=market_topic,
                )
                posts = fetched_posts.get("posts", [])
                latest_post_id = fetched_posts.get("latest_post_id")
                posts_count = len(posts)

                # Skip if no new posts
                if self._last_seen_post_id is not None and latest_post_id == self._last_seen_post_id:
                    self.status = "skipped"
                    skip_payload = {
                        "skipped": True,
                        "reason": "no new posts",
                        "tracked_account": f"@{self.target_username}",
                        "posts_analyzed": 0,
                        "prediction": None,
                        "signal": "uncertain",
                        "baseline_probability": getattr(self, "_baseline_probability", 50),
                    }
                    if progress_callback:
                        await progress_callback(self.agent_name, "skipped", skip_payload)
                    return skip_payload

                # Update last seen post id
                if latest_post_id:
                    self._last_seen_post_id = latest_post_id

                logger.info(
                    f"Fetched {posts_count} posts from @{self.target_username}"
                )
                
                # Step 2: Build user message with fetched posts
                user_message = await self.build_user_message(input_data, fetched_posts)
                
                # Step 3: Get prediction from Grok
                logger.info(f"UserAgent ({self.user_name}) getting prediction from Grok...")
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
                        "analysis": content[:500] if content else "Unable to generate analysis",
                        "signal": "uncertain",
                        "posts_analyzed": posts_count,
                        "baseline_probability": baseline,
                        "tracked_account": f"@{self.target_username}",
                        "notes_for_next_round": "Response could not be parsed; rerun when new post arrives.",
                    }
                
                # Ensure metadata fields are populated
                if "posts_analyzed" not in raw_output or raw_output["posts_analyzed"] == 0:
                    raw_output["posts_analyzed"] = posts_count
                if "baseline_probability" not in raw_output:
                    raw_output["baseline_probability"] = getattr(self, '_baseline_probability', 50)
                if "signal" not in raw_output:
                    raw_output["signal"] = "uncertain"
                if "tracked_account" not in raw_output:
                    raw_output["tracked_account"] = f"@{self.target_username}"
                if "notes_for_next_round" not in raw_output:
                    raw_output["notes_for_next_round"] = ""
                
                validated_output = self.output_schema(**raw_output)
                self.output_data = validated_output.model_dump()
                self.status = "completed"
                
                # Save notes to DB for next round (always save, even if empty)
                if self.session_id:
                    self.save_notes(self.output_data.get("notes_for_next_round", ""))
                
                if progress_callback:
                    await progress_callback(self.agent_name, "completed", self.output_data)
                
                logger.info(f"UserAgent ({self.user_name}) prediction: {self.output_data['prediction']}%")
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


# Convenience function for creating user agents
def create_user_agent(
    name: str,
    target_username: str | None = None,
    **kwargs
) -> UserAgent:
    """
    Factory function to create a UserAgent.
    
    Args:
        name: User agent name (e.g., "oliver", "owen")
        target_username: Optional X username override
        **kwargs: Additional arguments passed to UserAgent constructor
    
    Returns:
        Configured UserAgent instance
    
    Example:
        >>> agent = create_user_agent("oliver")
        >>> result = await agent.execute({"market_topic": "Will Bitcoin reach $100k?"})
    """
    return UserAgent(name=name, target_username=target_username, **kwargs)


# List of available user agent names
def get_user_agent_names() -> List[str]:
    """Get list of available user agent names"""
    return list(USER_ACCOUNT_MAPPINGS.keys())
