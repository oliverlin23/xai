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

from app.services.grok import GrokService, GROK_MODEL_FAST
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Add x_search to path for imports
_x_search_path = Path(__file__).parent.parent.parent.parent
if str(_x_search_path) not in sys.path:
    sys.path.insert(0, str(_x_search_path))

from x_search.communities import SPHERES, get_sphere, get_sphere_names
from x_search.tool import run_tool as x_search_run_tool, XSearchConfig


class SemanticFilterOutput(BaseModel):
    """Output schema for the semantic filter - indices only"""

    indices: list[int] = Field(description="Indices of relevant tweets (1-indexed)")


class FullSemanticFilterOutput(BaseModel):
    """Full output including reconstructed tweet data"""

    tweets: list[dict] = Field(default_factory=list)
    total_tweets_analyzed: int = Field(default=0)
    relevant_tweet_count: int = Field(default=0)


SEMANTIC_FILTER_PROMPT = """You are filtering tweets for relevance to a prediction market question.

QUESTION: {question}

TARGET SPHERE: {sphere_name}

Return the indices (1-indexed) of tweets that are relevant to answering the prediction question.
Order by relevance (most relevant first). Maximum 15 indices.

Prioritize:
- Tweets directly discussing the prediction topic
- High-engagement tweets (more likes/retweets = more signal)
- Authoritative voices within the target sphere

Exclude: off-topic content, spam, promotions, vague statements.

Output format: {{"indices": [3, 7, 1, 12, ...]}}"""


class SearchQueryOutput(BaseModel):
    """Output schema for search query extraction"""

    query: str = Field(description="Boolean search query with OR operators")


KEYWORD_EXTRACTION_PROMPT = """Convert this prediction market question into a boolean search query for X/Twitter.

TARGET SPHERE: {sphere_name}

Rules:
1. Use OR to join 10-15 keywords: term1 OR term2 OR term3
2. Include: main topic, abbreviations, hashtags, related terms
3. Include sphere-specific terminology
4. DO NOT use AND or restrictive terms

Example: "Will Bitcoin reach $100k?" → bitcoin OR BTC OR crypto OR cryptocurrency OR #bitcoin OR #btc OR blockchain OR hodl OR satoshi"""


@dataclass
class SemanticFilterConfig:
    """Configuration for the semantic filter"""

    max_tweets_to_fetch: int = 200  # Cast a wide net, filter with Grok
    max_tweets_to_return: int = 15
    min_relevance_score: float = 0.3
    lookback_days: int = 7  # X API recent search only allows 7 days max
    include_retweets: bool = False
    include_replies: bool = True  # Replies often contain good signal
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
        self.grok_service = GrokService(model=GROK_MODEL_FAST)  # Use fast model for filtering
        self._last_search_query: str | None = None  # Stores the last search query used

    async def filter(
        self,
        question: str,
        sphere: str,
        topic: str | None = None,
    ) -> FullSemanticFilterOutput:
        """
        Search for tweets and semantically filter for relevance to the prediction question.
        
        Args:
            question: The prediction market question (e.g., "Will Bitcoin reach $100k by end of 2025?")
            sphere: Sphere of influence to search (e.g., "fintwit_market", "eacc_sovereign", "america_first")
            topic: Optional topic override for x_search. If not provided, extracted from question.
        
        Returns:
            FullSemanticFilterOutput with relevant tweets reconstructed from indices
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
            return FullSemanticFilterOutput(
                tweets=[],
                total_tweets_analyzed=0,
                relevant_tweet_count=0,
            )

        # Step 2: Use Grok to get indices of relevant tweets
        indices_output = await self._semantic_filter(question, tweets, sphere_data)
        
        # Step 3: Reconstruct full tweets from indices
        relevant_tweets = self._reconstruct_tweets(tweets, indices_output.indices)
        
        return FullSemanticFilterOutput(
            tweets=relevant_tweets,
            total_tweets_analyzed=len(tweets),
            relevant_tweet_count=len(relevant_tweets),
        )

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
            search_topic = await self._extract_search_query(question, self._sphere_data)
        
        # Store the search query for external access (e.g., test scripts)
        self._last_search_query = search_topic
        
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

    async def _extract_search_query(self, question: str, sphere_data: Any = None) -> str:
        """Use Grok to extract search keywords from prediction question"""
        from x_search.communities import Sphere

        sphere_name = sphere_data.name if sphere_data and isinstance(sphere_data, Sphere) else "General"

        try:
            response = await self.grok_service.chat_completion(
                system_prompt=KEYWORD_EXTRACTION_PROMPT.format(sphere_name=sphere_name),
                user_message=question,
                output_schema=SearchQueryOutput,
                temperature=0.3,
                max_tokens=300,
            )

            result = json.loads(response.get("content", "{}"))
            query = result.get("query", "")
            logger.info(f"Keywords: {query[:80]}...")
            return query

        except Exception as e:
            logger.warning(f"Keyword extraction failed: {e}")
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

        # Clean up and return as OR query (expanded to 10+ keywords if possible)
        words = topic.split()
        meaningful_words = [w for w in words if len(w) > 2][:15]  # Increased from 6 to 15

        # Add common variations for first word if we have few keywords
        if meaningful_words and len(meaningful_words) < 10:
            # Simple expansion: add title case and uppercase versions
            first_word = meaningful_words[0]
            meaningful_words.extend([
                first_word.title(),
                first_word.upper(),
            ])

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
        """Use Grok to get indices of relevant tweets"""
        from x_search.communities import Sphere
        
        # Format tweets compactly
        tweets_text = self._format_tweets_for_grok(tweets)
        
        sphere_name = sphere_data.name if sphere_data and isinstance(sphere_data, Sphere) else "General"
        
        system_prompt = SEMANTIC_FILTER_PROMPT.format(
            question=question,
            sphere_name=sphere_name,
        )

        logger.info(f"Filtering {len(tweets)} tweets")

        try:
            response = await self.grok_service.chat_completion(
                system_prompt=system_prompt,
                user_message=tweets_text,
                output_schema=SemanticFilterOutput,
                temperature=0.3,
                max_tokens=150,
            )
            
            content = response.get("content", "{}")
            raw_output = json.loads(content)
            
            output = SemanticFilterOutput(**raw_output)
            output.indices = output.indices[:self.config.max_tweets_to_return]
            
            logger.info(f"Filter: {len(output.indices)}/{len(tweets)} relevant")
            
            return output

        except Exception as e:
            logger.error(f"Filter failed: {e}")
            return self._fallback_indices(tweets)

    def _reconstruct_tweets(
        self,
        tweets: list[dict[str, Any]],
        indices: list[int],
    ) -> list[dict[str, Any]]:
        """Reconstruct full tweet data from indices"""
        result = []
        for idx in indices:
            # Convert 1-indexed to 0-indexed
            array_idx = idx - 1
            if 0 <= array_idx < len(tweets):
                tweet = tweets[array_idx]
                result.append({
                    "author": f"@{tweet.get('author_username', 'unknown')}",
                    "text": tweet.get("text", "")[:280],
                    "likes": tweet.get("like_count", 0),
                    "retweets": tweet.get("retweet_count", 0),
                })
        return result

    def _fallback_indices(self, tweets: list[dict[str, Any]]) -> SemanticFilterOutput:
        """Generate fallback indices when Grok filtering fails"""
        # Return top tweets by engagement
        indexed_tweets = list(enumerate(tweets, 1))
        sorted_tweets = sorted(
            indexed_tweets,
            key=lambda t: (t[1].get("like_count", 0) + t[1].get("retweet_count", 0) * 2),
            reverse=True,
        )[:self.config.max_tweets_to_return]
        
        return SemanticFilterOutput(indices=[idx for idx, _ in sorted_tweets])

    def _format_tweets_for_grok(self, tweets: list[dict[str, Any]]) -> str:
        """Format tweets compactly for Grok"""
        lines = []
        for i, tweet in enumerate(tweets, 1):
            author = tweet.get("author_username", "unknown")
            text = tweet.get("text", "")[:200]  # Shorter truncation
            likes = tweet.get("like_count", 0)
            retweets = tweet.get("retweet_count", 0)
            
            # Compact format: [idx] @author (likes/RTs): text
            lines.append(f"[{i}] @{author} ({likes}L/{retweets}RT): {text}")

        return "\n".join(lines)


async def semantic_search(
    question: str,
    sphere: str,
    topic: str | None = None,
    config: SemanticFilterConfig | None = None,
) -> FullSemanticFilterOutput:
    """
    Convenience function to perform semantic search for a prediction question.
    
    Args:
        question: The prediction market question
        sphere: Sphere of influence to search (e.g., "fintwit_market", "eacc_sovereign")
        topic: Optional topic override for x_search
        config: Optional configuration
    
    Returns:
        FullSemanticFilterOutput with filtered tweets
    
    Example:
        >>> result = await semantic_search(
        ...     question="Will Bitcoin reach $100k by end of 2025?",
        ...     sphere="fintwit_market"
        ... )
        >>> for tweet in result.tweets:
        ...     print(f"{tweet['author']}: {tweet['text'][:50]}")
    """
    filter_instance = SemanticFilter(config=config)
    return await filter_instance.filter(question, sphere, topic)
