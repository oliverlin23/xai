"""
Semantic Filter - Uses Grok to filter x_search results for relevance to prediction questions.

This module performs a two-step process:
1. Fetch tweets via x_search (direct Python call)
2. Use Grok to semantically filter and rank results by relevance to the prediction question
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.services.grok import GrokService
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Add x_search to path for imports
_x_search_path = Path(__file__).parent.parent.parent.parent
if str(_x_search_path) not in sys.path:
    sys.path.insert(0, str(_x_search_path))

from x_search.communities import SPHERES, get_sphere, get_sphere_names
from x_search.tool import run_tool as x_search_run_tool, XSearchConfig


class RelevantTweet(BaseModel):
    """A tweet deemed relevant by the semantic filter"""

    author: str = Field(description="Tweet author username")
    text: str = Field(description="Tweet text content")
    created_at: str = Field(description="Tweet timestamp (ISO format)")
    relevance_score: float = Field(
        ge=0.0, le=1.0, description="Relevance score from 0-1"
    )
    relevance_reason: str = Field(
        description="Brief explanation of why this tweet is relevant"
    )
    signal: str = Field(
        description="Signal direction: yes (supports YES outcome), no (supports NO outcome), or uncertain"
    )
    likes: int = Field(default=0, description="Number of likes")
    retweets: int = Field(default=0, description="Number of retweets")


class SemanticFilterOutput(BaseModel):
    """Output schema for the semantic filter"""

    relevant_tweets: list[RelevantTweet] = Field(
        description="List of tweets relevant to the prediction question, ranked by relevance"
    )
    summary: str = Field(
        description="Brief factual summary of what topics/perspectives the relevant tweets cover"
    )
    total_tweets_analyzed: int = Field(description="Total tweets that were analyzed")
    relevant_tweet_count: int = Field(
        description="Number of tweets deemed relevant"
    )


SEMANTIC_FILTER_PROMPT = """You are a semantic relevance filter for prediction market research.

IMPORTANT: Today's date is {current_date}. Use this to interpret temporal references in tweets.
- All tweets are within 7 days from the current date.

Your task is to analyze tweets and determine which ones are ACTUALLY relevant to answering a specific prediction market question, filtered through a specific sphere of influence.

PREDICTION QUESTION: {question}

This question resolves YES if the stated outcome occurs, and NO if it does not.

TARGET SPHERE OF INFLUENCE: {sphere_name}
{sphere_description}

FILTERING CRITERIA:
1. **Direct Relevance**: Does the tweet discuss the topic of the prediction?
2. **Sphere Alignment**: Does this tweet come from or resonate with the target sphere? Prioritize voices that would be influential within this sphere.
3. **Informational Value**: Does it provide facts, opinions, or signals that could inform the prediction?
4. **Source Authority**: Is the author someone whose opinion matters for this topic within this sphere?
5. **Recency Signal**: Does it reflect current sentiment or recent developments?

ENGAGEMENT WEIGHTING (factor this into relevance_score):
- High-engagement tweets from authoritative accounts should receive HIGHER relevance scores
- A tweet with 500+ likes from a verified expert is more signal-worthy than one with 5 likes
- Use engagement as a multiplier: base_relevance * engagement_boost
  - 0-50 likes: 1.0x (no boost)
  - 50-200 likes: 1.1x boost
  - 200-500 likes: 1.2x boost  
  - 500+ likes: 1.3x boost
- Retweets count as 2x likes for this calculation

EXCLUDE tweets that are:
- Off-topic or only tangentially related
- Not aligned with the target sphere's discourse style or concerns
- Pure spam, promotions, or engagement bait
- Too vague to provide actionable insight

For each relevant tweet, provide:
- author: The @username from the tweet
- text: The tweet text (can be truncated)
- created_at: The timestamp from the tweet (preserve the ISO format)
- relevance_score: 0.0-1.0 (1.0 = highly relevant, sphere-aligned, and informative) - INCLUDE engagement weighting
- relevance_reason: Why this tweet matters for the prediction AND why it's relevant to this sphere
- signal: The direction this tweet points toward:
  - "yes" = suggests the outcome WILL happen (increases probability)
  - "no" = suggests the outcome will NOT happen (decreases probability)
  - "uncertain" = provides context but no clear directional signal
- likes: Number of likes
- retweets: Number of retweets

Return ONLY tweets with relevance_score >= 0.3. Rank them by relevance_score descending.

Provide a brief factual summary of what topics and perspectives the relevant tweets cover. Do NOT make predictions or choose an overall signal - just summarize the content."""


class SearchQueryOutput(BaseModel):
    """Output schema for search query extraction"""

    query: str = Field(
        description="Boolean search query using OR operators (e.g., 'bitcoin OR BTC OR crypto')"
    )
    primary_keywords: list[str] = Field(
        description="Primary keywords extracted from the question"
    )
    synonyms: list[str] = Field(
        description="Synonyms and related terms to expand search coverage"
    )
    reasoning: str = Field(
        description="Brief explanation of keyword selection"
    )


KEYWORD_EXTRACTION_PROMPT = """You are a search query optimizer for the X (Twitter) API.

Your task is to convert a prediction market question into a BROAD boolean search query.

CRITICAL: In X API search, spaces between groups act as AND. So "(bitcoin) (100k)" means bitcoin AND 100k - very restrictive!

RULES FOR BROAD SEARCH:
1. Use a SINGLE group with OR to maximize results: bitcoin OR BTC OR crypto
2. Focus on just the PRIMARY ENTITY/TOPIC - cast a wide net!
3. Include common abbreviations and slang (BTC, ETH, GPT, etc.)
4. DO NOT add restrictive terms like prices, dates, or outcomes
5. We filter for relevance AFTER fetching - your job is to find tweets, not filter them

EXAMPLES:
- "Will Bitcoin reach $100k by end of 2025?" → "bitcoin OR BTC OR btc"
- "Will Trump win the 2024 election?" → "trump OR election OR vote"
- "Will OpenAI release GPT-5 in 2025?" → "openai OR gpt5 OR gpt-5 OR chatgpt"
- "Will Ethereum flip Bitcoin market cap?" → "ethereum OR ETH OR bitcoin OR BTC"
- "Will the Fed cut interest rates?" → "fed OR federal reserve OR interest rates OR rate cut"
- "Will Tesla stock reach $500?" → "tesla OR TSLA OR elon musk"

IMPORTANT: Return a SINGLE group of OR'd keywords. DO NOT use multiple space-separated groups.
We want BROAD coverage - the semantic filter will handle relevance later."""


@dataclass
class SemanticFilterConfig:
    """Configuration for the semantic filter"""

    max_tweets_to_fetch: int = 200  # Cast a wide net, filter with Grok
    max_tweets_to_return: int = 15
    min_relevance_score: float = 0.3
    lookback_days: int = 7
    include_retweets: bool = False
    include_replies: bool = False
    lang: str = "en"
    verified_only: bool = False  # Don't restrict to verified - filter by sphere instead


class SemanticFilter:
    """
    Semantic filter that uses x_search + Grok to find relevant tweets for a prediction question.
    
    This provides a higher-quality signal than raw keyword search by using Grok to
    understand the semantic relevance of each tweet to the prediction question.
    """

    def __init__(self, config: SemanticFilterConfig | None = None):
        self.config = config or SemanticFilterConfig()
        self.grok_service = GrokService()

    async def filter(
        self,
        question: str,
        sphere: str,
        topic: str | None = None,
    ) -> SemanticFilterOutput:
        """
        Search for tweets and semantically filter for relevance to the prediction question.
        
        Args:
            question: The prediction market question (e.g., "Will Bitcoin reach $100k by end of 2025?")
            sphere: Sphere of influence to search (e.g., "fintwit_market", "eacc_sovereign", "america_first")
            topic: Optional topic override for x_search. If not provided, extracted from question.
        
        Returns:
            SemanticFilterOutput with relevant tweets, summary, and metadata
        """
        # Validate sphere
        if sphere not in SPHERES:
            valid = ", ".join(SPHERES.keys())
            raise ValueError(f"Invalid sphere '{sphere}'. Valid options: {valid}")

        # Get sphere data for filtering context
        sphere_data = get_sphere(sphere)
        
        # Step 1: Fetch tweets via x_search (keyword-only, no user filter)
        tweets = await self._fetch_tweets(question, sphere, topic)
        
        if not tweets:
            logger.warning(f"No tweets found for question: {question[:50]}...")
            return SemanticFilterOutput(
                relevant_tweets=[],
                summary="No tweets found for this topic.",
                total_tweets_analyzed=0,
                relevant_tweet_count=0,
            )

        # Step 2: Use Grok to semantically filter by relevance AND sphere alignment
        filtered_output = await self._semantic_filter(question, tweets, sphere_data)
        
        return filtered_output

    async def _fetch_tweets(
        self,
        question: str,
        sphere: str,
        topic: str | None,
    ) -> list[dict[str, Any]]:
        """Fetch tweets from x_search using keyword-only search"""
        self._sphere_data = get_sphere(sphere)
        if not self._sphere_data:
            logger.error(f"Sphere not found: {sphere}")
            return []

        # Use provided topic or extract optimized boolean query from question
        if topic:
            search_topic = topic
        else:
            search_topic = await self._extract_search_query(question)
        
        # Build x_search payload - keyword-only search (no username filter)
        start_time = datetime.now(UTC) - timedelta(days=self.config.lookback_days)
        payload = {
            "topic": search_topic,
            # No username - keyword-only search
            "start_time": start_time.isoformat(),
            "max_tweets": self.config.max_tweets_to_fetch,
            "lang": self.config.lang,
            "include_retweets": self.config.include_retweets,
            "include_replies": self.config.include_replies,
            "verified_only": self.config.verified_only,
        }

        logger.info(f"Keyword search: '{search_topic}' (will filter for {self._sphere_data.name})")

        try:
            # Pass bearer token from app config to x_search
            settings = get_settings()
            x_config = XSearchConfig(bearer_token=settings.x_bearer_token)
            
            result = await x_search_run_tool(payload, config=x_config)
            tweets = result.get("tweets", [])
            logger.info(f"Fetched {len(tweets)} tweets from x_search")
            return tweets
        except Exception as e:
            logger.error(f"x_search failed: {e}")
            return []

    async def _extract_search_query(self, question: str) -> str:
        """Use Grok to extract optimized boolean search query from prediction question"""
        logger.info(f"Extracting search keywords from question: {question[:50]}...")
        
        try:
            response = await self.grok_service.chat_completion(
                system_prompt=KEYWORD_EXTRACTION_PROMPT,
                user_message=f"Convert this prediction market question into a boolean search query:\n\n{question}",
                output_schema=SearchQueryOutput,
                temperature=0.3,
                max_tokens=500,
            )
            
            content = response.get("content", "{}")
            result = json.loads(content)
            query = result.get("query", "")
            
            logger.info(f"Extracted search query: {query}")
            logger.debug(f"Keywords: {result.get('primary_keywords')}, Synonyms: {result.get('synonyms')}")
            
            return query
            
        except Exception as e:
            logger.warning(f"Grok keyword extraction failed, using fallback: {e}")
            return self._extract_topic_fallback(question)

    def _extract_topic_fallback(self, question: str) -> str:
        """Fallback: Extract search topic from prediction question (simple heuristic)"""
        # Remove common prediction market phrasing
        topic = question.lower()
        for phrase in [
            "will ", "would ", "does ", "is ", "are ", "can ", "should ",
            "by end of ", "by the end of ", "before ", "after ",
            "in 2024", "in 2025", "in 2026",
            "resolve yes", "resolve no", "?",
        ]:
            topic = topic.replace(phrase, " ")
        
        # Clean up and return as OR query
        words = topic.split()
        meaningful_words = [w for w in words if len(w) > 2][:6]
        
        # Format as boolean OR query
        if meaningful_words:
            return " OR ".join(meaningful_words)
        return topic.strip()

    async def _semantic_filter(
        self,
        question: str,
        tweets: list[dict[str, Any]],
        sphere_data: Any = None,
    ) -> SemanticFilterOutput:
        """Use Grok to semantically filter and rank tweets by relevance AND sphere alignment"""
        from x_search.communities import Sphere
        
        # Format tweets for Grok
        tweets_text = self._format_tweets_for_grok(tweets)
        
        # Include current date for temporal context
        now = datetime.now(UTC)
        current_date = now.strftime("%Y-%m-%d")
        
        # Build sphere description for the prompt
        if sphere_data and isinstance(sphere_data, Sphere):
            sphere_name = sphere_data.name
            sphere_description = f"""Vibe: {sphere_data.vibe}
Typical participants: {sphere_data.followers}
Core beliefs: {sphere_data.core_beliefs}"""
        else:
            sphere_name = "General"
            sphere_description = "General audience - no specific sphere filter applied."
        
        system_prompt = SEMANTIC_FILTER_PROMPT.format(
            question=question,
            current_date=current_date,
            sphere_name=sphere_name,
            sphere_description=sphere_description,
        )
        
        user_message = f"""Analyze these {len(tweets)} tweets and filter for relevance to the prediction question AND alignment with the target sphere.

PREDICTION QUESTION: {question}

TARGET SPHERE: {sphere_name}

TWEETS TO ANALYZE:
{tweets_text}

Return your analysis as JSON matching the SemanticFilterOutput schema."""

        logger.info(f"Sending {len(tweets)} tweets to Grok for semantic filtering")

        try:
            response = await self.grok_service.chat_completion(
                system_prompt=system_prompt,
                user_message=user_message,
                output_schema=SemanticFilterOutput,
                temperature=0.3,  # Lower temperature for more consistent filtering
                max_tokens=4000,
            )
            
            content = response.get("content", "{}")
            raw_output = json.loads(content)
            
            # Validate and return
            output = SemanticFilterOutput(**raw_output)
            
            # Apply additional filtering based on config
            output.relevant_tweets = [
                t for t in output.relevant_tweets
                if t.relevance_score >= self.config.min_relevance_score
            ][:self.config.max_tweets_to_return]
            
            output.relevant_tweet_count = len(output.relevant_tweets)
            output.total_tweets_analyzed = len(tweets)
            
            logger.info(
                f"Semantic filter: {output.relevant_tweet_count}/{len(tweets)} tweets relevant"
            )
            
            return output

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Grok response: {e}")
            return self._fallback_output(tweets)
        except Exception as e:
            logger.error(f"Grok semantic filter failed: {e}")
            return self._fallback_output(tweets)

    def _format_tweets_for_grok(self, tweets: list[dict[str, Any]]) -> str:
        """Format tweets into a readable string for Grok"""
        lines = []
        for i, tweet in enumerate(tweets, 1):
            author = tweet.get("author_username", "unknown")
            text = tweet.get("text", "")[:500]  # Truncate long tweets
            likes = tweet.get("like_count", 0)
            retweets = tweet.get("retweet_count", 0)
            created_at = tweet.get("created_at", "unknown")
            
            # Format timestamp for readability
            if isinstance(created_at, datetime):
                timestamp_str = created_at.strftime("%Y-%m-%d %H:%M UTC")
            else:
                timestamp_str = str(created_at)[:19]  # Truncate ISO string

            lines.append(
                f"[{i}] @{author} | {timestamp_str} | ❤️ {likes} 🔄 {retweets}\n{text}\n"
            )

        return "\n".join(lines)

    def _fallback_output(self, tweets: list[dict[str, Any]]) -> SemanticFilterOutput:
        """Generate fallback output when Grok filtering fails"""
        # Return top tweets by engagement as fallback
        sorted_tweets = sorted(
            tweets,
            key=lambda t: (t.get("like_count", 0) + t.get("retweet_count", 0) * 2),
            reverse=True,
        )[:self.config.max_tweets_to_return]

        relevant = []
        for t in sorted_tweets:
            created_at = t.get("created_at", "")
            if isinstance(created_at, datetime):
                created_at_str = created_at.isoformat()
            else:
                created_at_str = str(created_at) if created_at else "unknown"
            
            relevant.append(
                RelevantTweet(
                    author=f"@{t.get('author_username', 'unknown')}",
                    text=t.get("text", "")[:300],
                    created_at=created_at_str,
                    relevance_score=0.5,  # Default score
                    relevance_reason="Ranked by engagement (fallback mode)",
                    signal="uncertain",
                    likes=t.get("like_count", 0),
                    retweets=t.get("retweet_count", 0),
                )
            )

        return SemanticFilterOutput(
            relevant_tweets=relevant,
            summary="Fallback mode: tweets ranked by engagement, not semantic relevance.",
            total_tweets_analyzed=len(tweets),
            relevant_tweet_count=len(relevant),
        )


async def semantic_search(
    question: str,
    sphere: str,
    topic: str | None = None,
    config: SemanticFilterConfig | None = None,
) -> SemanticFilterOutput:
    """
    Convenience function to perform semantic search for a prediction question.
    
    Args:
        question: The prediction market question
        sphere: Sphere of influence to search (e.g., "fintwit_market", "eacc_sovereign")
        topic: Optional topic override for x_search
        config: Optional configuration
    
    Returns:
        SemanticFilterOutput with filtered and ranked tweets
    
    Example:
        >>> result = await semantic_search(
        ...     question="Will Bitcoin reach $100k by end of 2025?",
        ...     sphere="fintwit_market"
        ... )
        >>> print(result.summary)
        >>> for tweet in result.relevant_tweets:
        ...     print(f"{tweet.author}: {tweet.relevance_score:.2f} - {tweet.signal}")
    """
    filter_instance = SemanticFilter(config=config)
    return await filter_instance.filter(question, sphere, topic)
