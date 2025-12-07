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

from x_search.communities import COMMUNITIES, get_community_users
from x_search.tool import run_tool as x_search_run_tool, XSearchConfig


class RelevantTweet(BaseModel):
    """A tweet deemed relevant by the semantic filter"""

    author: str = Field(description="Tweet author username")
    text: str = Field(description="Tweet text content")
    relevance_score: float = Field(
        ge=0.0, le=1.0, description="Relevance score from 0-1"
    )
    relevance_reason: str = Field(
        description="Brief explanation of why this tweet is relevant"
    )
    sentiment: str = Field(
        description="Sentiment toward the prediction outcome: bullish, bearish, neutral"
    )
    likes: int = Field(default=0, description="Number of likes")
    retweets: int = Field(default=0, description="Number of retweets")


class SemanticFilterOutput(BaseModel):
    """Output schema for the semantic filter"""

    relevant_tweets: list[RelevantTweet] = Field(
        description="List of tweets relevant to the prediction question, ranked by relevance"
    )
    summary: str = Field(
        description="Brief summary of what the relevant tweets indicate about the prediction"
    )
    overall_sentiment: str = Field(
        description="Overall sentiment across relevant tweets: bullish, bearish, neutral, mixed"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the filtering (based on tweet quality and relevance)",
    )
    total_tweets_analyzed: int = Field(description="Total tweets that were analyzed")
    relevant_tweet_count: int = Field(
        description="Number of tweets deemed relevant"
    )


SEMANTIC_FILTER_PROMPT = """You are a semantic relevance filter for prediction market research.

Your task is to analyze tweets and determine which ones are ACTUALLY relevant to answering a specific prediction market question.

PREDICTION QUESTION: {question}

FILTERING CRITERIA:
1. **Direct Relevance**: Does the tweet discuss the topic of the prediction?
2. **Informational Value**: Does it provide facts, opinions, or signals that could inform the prediction?
3. **Source Authority**: Is the author someone whose opinion matters for this topic?
4. **Recency Signal**: Does it reflect current sentiment or recent developments?

EXCLUDE tweets that are:
- Off-topic or only tangentially related
- Pure spam, promotions, or engagement bait
- Duplicate information already captured in other tweets
- Too vague to provide actionable insight

For each relevant tweet, provide:
- relevance_score: 0.0-1.0 (1.0 = highly relevant and informative)
- relevance_reason: Why this tweet matters for the prediction
- sentiment: Whether this tweet is bullish (supports YES), bearish (supports NO), or neutral

Return ONLY tweets with relevance_score >= 0.3. Rank them by relevance_score descending.

Provide a summary of what the relevant tweets collectively indicate about the prediction question."""


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

Your task is to convert a prediction market question into a SIMPLE search query that will find relevant tweets.

CRITICAL RULES:
1. NEVER use AND - it's way too restrictive and returns almost no results
2. NEVER use multiple keyword groups - X API treats spaces as AND
3. ONLY use OR to combine 3-6 keywords into a single flat list
4. Include common abbreviations and slang (BTC for Bitcoin, ETH for Ethereum)
5. Focus on the CORE TOPIC only - ignore prediction framing words

CORRECT FORMAT:
keyword1 OR keyword2 OR keyword3 OR keyword4

EXAMPLES:
- "Will Bitcoin reach $100k by end of 2025?" → "bitcoin OR BTC OR crypto"
- "Will Trump win the 2024 election?" → "trump OR maga OR election"
- "Will OpenAI release GPT-5 in 2025?" → "openai OR gpt5 OR chatgpt OR altman"
- "Will Ethereum flip Bitcoin market cap?" → "ethereum OR ETH OR bitcoin OR BTC"
- "Will there be a US recession in 2025?" → "recession OR economy OR inflation"

WRONG - NEVER DO THIS:
- "(bitcoin OR BTC) (price OR 100k)" ← WRONG: spaces act as AND
- "bitcoin AND price" ← WRONG: AND is too restrictive
- "(trump) (election)" ← WRONG: two groups = AND logic
- "bitcoin price 100k" ← WRONG: spaces = AND

Return ONLY a flat list of OR'd keywords. Nothing else."""


@dataclass
class SemanticFilterConfig:
    """Configuration for the semantic filter"""

    max_tweets_to_fetch: int = 100  # X API allows up to 100 per query
    max_tweets_to_return: int = 15
    min_relevance_score: float = 0.3
    lookback_days: int = 7  # X API recent search only allows 7 days max
    include_retweets: bool = False
    include_replies: bool = True  # Replies often contain good signal
    lang: str = "en"


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
        community: str,
        topic: str | None = None,
    ) -> SemanticFilterOutput:
        """
        Search for tweets and semantically filter for relevance to the prediction question.
        
        Args:
            question: The prediction market question (e.g., "Will Bitcoin reach $100k by end of 2025?")
            community: Community to search (e.g., "crypto_web3", "tech_vc", "maga_right")
            topic: Optional topic override for x_search. If not provided, extracted from question.
        
        Returns:
            SemanticFilterOutput with relevant tweets, summary, and metadata
        """
        # Validate community
        if community not in COMMUNITIES:
            valid = ", ".join(COMMUNITIES.keys())
            raise ValueError(f"Invalid community '{community}'. Valid options: {valid}")

        # Step 1: Fetch tweets via x_search
        tweets = await self._fetch_tweets(question, community, topic)
        
        if not tweets:
            logger.warning(f"No tweets found for question: {question[:50]}...")
            return SemanticFilterOutput(
                relevant_tweets=[],
                summary="No tweets found for this topic in the specified community.",
                overall_sentiment="neutral",
                confidence=0.0,
                total_tweets_analyzed=0,
                relevant_tweet_count=0,
            )

        # Step 2: Use Grok to semantically filter and rank
        filtered_output = await self._semantic_filter(question, tweets)
        
        return filtered_output

    async def _fetch_tweets(
        self,
        question: str,
        community: str,
        topic: str | None,
    ) -> list[dict[str, Any]]:
        """Fetch tweets from x_search"""
        community_users = get_community_users(community)
        if not community_users:
            logger.error(f"No users found for community: {community}")
            return []

        # Use provided topic or extract optimized boolean query from question
        if topic:
            search_topic = topic
        else:
            search_topic = await self._extract_search_query(question)
        
        # Build x_search payload
        start_time = datetime.now(UTC) - timedelta(days=self.config.lookback_days)
        payload = {
            "topic": search_topic,
            "username": community_users[0],  # Seed user
            "start_time": start_time.isoformat(),
            "max_tweets": self.config.max_tweets_to_fetch,
            "community": community,
            "lang": self.config.lang,
            "include_retweets": self.config.include_retweets,
            "include_replies": self.config.include_replies,
        }

        logger.info(f"Fetching tweets for query '{search_topic}' from {community} community")

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
    ) -> SemanticFilterOutput:
        """Use Grok to semantically filter and rank tweets"""
        
        # Format tweets for Grok
        tweets_text = self._format_tweets_for_grok(tweets)
        
        system_prompt = SEMANTIC_FILTER_PROMPT.format(question=question)
        
        user_message = f"""Analyze these {len(tweets)} tweets and filter for relevance to the prediction question.

PREDICTION QUESTION: {question}

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
                f"Semantic filter: {output.relevant_tweet_count}/{len(tweets)} tweets relevant, "
                f"sentiment={output.overall_sentiment}, confidence={output.confidence:.2f}"
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
            
            lines.append(
                f"[{i}] @{author} (❤️ {likes}, 🔄 {retweets}):\n{text}\n"
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

        relevant = [
            RelevantTweet(
                author=f"@{t.get('author_username', 'unknown')}",
                text=t.get("text", "")[:300],
                relevance_score=0.5,  # Default score
                relevance_reason="Ranked by engagement (fallback mode)",
                sentiment="neutral",
                likes=t.get("like_count", 0),
                retweets=t.get("retweet_count", 0),
            )
            for t in sorted_tweets
        ]

        return SemanticFilterOutput(
            relevant_tweets=relevant,
            summary="Fallback mode: tweets ranked by engagement, not semantic relevance.",
            overall_sentiment="neutral",
            confidence=0.2,
            total_tweets_analyzed=len(tweets),
            relevant_tweet_count=len(relevant),
        )


async def semantic_search(
    question: str,
    community: str,
    topic: str | None = None,
    config: SemanticFilterConfig | None = None,
) -> SemanticFilterOutput:
    """
    Convenience function to perform semantic search for a prediction question.
    
    Args:
        question: The prediction market question
        community: Community to search (e.g., "crypto_web3", "tech_vc")
        topic: Optional topic override for x_search
        config: Optional configuration
    
    Returns:
        SemanticFilterOutput with filtered and ranked tweets
    
    Example:
        >>> result = await semantic_search(
        ...     question="Will Bitcoin reach $100k by end of 2025?",
        ...     community="crypto_web3"
        ... )
        >>> print(result.summary)
        >>> for tweet in result.relevant_tweets:
        ...     print(f"{tweet.author}: {tweet.relevance_score:.2f} - {tweet.sentiment}")
    """
    filter_instance = SemanticFilter(config=config)
    return await filter_instance.filter(question, community, topic)
