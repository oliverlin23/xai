"""
Streaming helper for UserAgent using Tweepy AsyncStreamingClient.

Listens for posts from a specific X account (via a `from:username` rule),
runs the existing UserAgent pipeline when a new post arrives, and allows an
optional trade callback to execute/report trades.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Dict, Optional

import tweepy
from tweepy.asynchronous import AsyncStreamingClient

from app.core.config import get_settings
from app.traders.user_agent import UserAgent, UserAgentOutput

logger = logging.getLogger(__name__)


MarketInputProvider = Callable[[], Awaitable[Dict[str, object]] | Dict[str, object]]
TradeCallback = Callable[[UserAgentOutput, tweepy.Tweet], Awaitable[None]]


class UserStreamClient(AsyncStreamingClient):
    """
    Async streaming client that listens for posts from a tracked X account and
    triggers a forecast + optional trade callback when new tweets arrive.
    """

    def __init__(
        self,
        bearer_token: str,
        target_username: str,
        user_agent: UserAgent,
        market_input_provider: MarketInputProvider,
        trade_callback: Optional[TradeCallback] = None,
        *,
        max_retries: int = 3,
        timeout: float = 30.0,
        **kwargs,
    ):
        super().__init__(bearer_token, max_retries=max_retries, timeout=timeout, **kwargs)
        self.target_username = target_username.lstrip("@").lower()
        self.user_agent = user_agent
        self.market_input_provider = market_input_provider
        self.trade_callback = trade_callback
        self._seen_ids: set[str] = set()

    async def _reset_rules(self) -> None:
        """Replace existing rules with a from:<username> rule."""
        existing = await self.get_rules()
        if existing and existing.data:
            await self.delete_rules([rule.id for rule in existing.data])

        await self.add_rules(
            tweepy.StreamRule(value=f"from:{self.target_username}", tag=f"user:{self.target_username}")
        )
        logger.info("Streaming rule set: from:%s", self.target_username)

    async def on_tweet(self, tweet: tweepy.Tweet) -> None:
        """Handle incoming tweet by running the user agent and optional trade callback."""
        if tweet.id in self._seen_ids:
            return
        self._seen_ids.add(tweet.id)

        logger.info(
            "New tweet from @%s (id=%s): %s",
            self.target_username,
            tweet.id,
            getattr(tweet, "text", "")[:120],
        )

        try:
            input_data = self.market_input_provider()
            if asyncio.iscoroutine(input_data):
                input_data = await input_data

            result = await self.user_agent.execute(input_data)

            if self.trade_callback:
                await self.trade_callback(result, tweet)
        except Exception as exc:  # noqa: BLE001 - want to log everything for stream stability
            logger.exception("Failed to process tweet %s: %s", tweet.id, exc)

    async def start(
        self,
        *,
        backfill_minutes: Optional[int] = None,
        tweet_fields: Optional[list[str]] = None,
        user_fields: Optional[list[str]] = None,
    ) -> None:
        """
        Configure rules and start the filtered stream. This call blocks until disconnected.
        """
        await self._reset_rules()
        await self.filter(
            backfill_minutes=backfill_minutes,
            tweet_fields=tweet_fields
            or ["created_at", "public_metrics", "text", "author_id", "lang"],
            user_fields=user_fields or ["username", "name", "verified"],
            expansions=["author_id"],
        )


def start_user_stream(
    target_username: str,
    user_agent: UserAgent,
    market_input_provider: MarketInputProvider,
    trade_callback: Optional[TradeCallback] = None,
    *,
    bearer_token: Optional[str] = None,
    max_retries: int = 3,
    timeout: float = 30.0,
) -> UserStreamClient:
    """
    Convenience factory that wires settings + stream client.

    Example:
        agent = create_user_agent("oliver")
        stream = start_user_stream(
            target_username="oliveelin",
            user_agent=agent,
            market_input_provider=lambda: {
                "market_topic": "Will BTC > $100k by 2025?",
                "order_book": {...},
                "recent_trades": [...],
            },
            trade_callback=report_trade,
        )
        asyncio.create_task(stream.start())
    """
    settings = get_settings()
    token = bearer_token or settings.x_bearer_token
    if not token:
        raise ValueError("X bearer token is required for streaming (settings.x_bearer_token missing).")

    return UserStreamClient(
        bearer_token=token,
        target_username=target_username,
        user_agent=user_agent,
        market_input_provider=market_input_provider,
        trade_callback=trade_callback,
        max_retries=max_retries,
        timeout=timeout,
    )

