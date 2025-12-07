"""Core X Search tool - fetches tweets with community-based expansion."""

from __future__ import annotations

import asyncio
import logging
import os
import random
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Iterable

import httpx
from pydantic import BaseModel, Field, HttpUrl, ValidationError, validator

from .communities import SPHERES, get_sphere

LOGGER = logging.getLogger("x_search")


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


class XApiError(RuntimeError):
    """Raised when the X API returns an unrecoverable error."""


class XSearchRequest(BaseModel):
    """Incoming request payload."""

    topic: str = Field(..., min_length=1, max_length=256)
    username: str | None = Field(
        default=None,
        description="Optional seed username. If None, performs keyword-only search.",
    )
    start_time: datetime
    max_tweets: int = Field(default=50, ge=1, le=200)
    lang: str | None = Field(default="en", max_length=8)
    include_retweets: bool = False
    include_replies: bool = False
    verified_only: bool = Field(
        default=False,
        description="Only return posts from verified users (adds is:verified to query)",
    )
    sphere: str | None = Field(
        default=None,
        description="Sphere of influence for context (e.g., eacc_sovereign, fintwit_market)",
    )

    @validator("topic")
    def _sanitize_topic(cls, value: str) -> str:
        return value.strip()

    @validator("username")
    def _sanitize_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().lstrip("@")
        if not value:
            return None
        return value

    @validator("sphere")
    def _validate_sphere(cls, value: str | None) -> str | None:
        if value is not None and value not in SPHERES:
            valid = ", ".join(SPHERES.keys())
            raise ValueError(f"Invalid sphere '{value}'. Valid options: {valid}")
        return value


class RelatedUser(BaseModel):
    id: str
    username: str
    name: str | None = None
    score: float


class TweetResult(BaseModel):
    id: str
    text: str
    author_username: str
    author_name: str | None = None
    created_at: datetime
    like_count: int | None = None
    reply_count: int | None = None
    retweet_count: int | None = None
    quote_count: int | None = None
    url: HttpUrl


class XSearchResponse(BaseModel):
    topic: str
    seed_user: str
    start_time: datetime
    generated_at: datetime
    tweets: list[TweetResult]
    related_users: list[RelatedUser]


class XSearchConfig(BaseModel):
    bearer_token: str | None = Field(
        default_factory=lambda: os.getenv("X_BEARER_TOKEN")
    )
    base_url: str = "https://api.x.com/2"
    http_timeout_seconds: float = 15.0
    request_retries: int = 3
    request_backoff_seconds: float = 2.0
    follower_sample_size: int = 3
    following_sample_per_follower: int = 5
    max_related_users: int = 0
    graph_concurrency: int = 8
    search_concurrency: int = 1
    # Twitter API v2 Basic tier has 512 char query limit
    # Batch usernames to stay under limit (8-10 users per batch is safe)
    max_users_per_query: int = 8

    @validator("bearer_token")
    def _require_token(cls, value: str | None) -> str:
        if not value:
            raise ValueError("X_BEARER_TOKEN env var missing")
        return value


@dataclass
class _User:
    id: str
    username: str
    name: str | None


class XApiClient:
    """Minimal async client around the X v2 REST API."""

    def __init__(self, config: XSearchConfig):
        self._config = config
        self._client = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=config.http_timeout_seconds,
            headers={
                "Authorization": f"Bearer {config.bearer_token}",
                "User-Agent": "x-search/0.1",
            },
        )

    async def __aenter__(self) -> "XApiClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self._client.aclose()

    async def get_user_by_username(self, username: str) -> _User:
        payload = await self._request(
            "GET",
            f"/users/by/username/{username}",
            params={"user.fields": "name,username,verified,public_metrics"},
        )
        data = payload.get("data")
        if not data:
            raise XApiError(f"user '{username}' not found")
        return _User(id=data["id"], username=data["username"], name=data.get("name"))

    async def get_followers(self, user_id: str, max_results: int) -> list[_User]:
        params = {
            "max_results": min(max_results, 1000),
            "user.fields": "name,username",
        }
        payload = await self._request(
            "GET", f"/users/{user_id}/followers", params=params
        )
        return [
            _User(id=item["id"], username=item["username"], name=item.get("name"))
            for item in payload.get("data", [])
        ]

    async def get_following(self, user_id: str, max_results: int) -> list[_User]:
        params = {
            "max_results": min(max_results, 1000),
            "user.fields": "name,username",
        }
        payload = await self._request(
            "GET", f"/users/{user_id}/following", params=params
        )
        return [
            _User(id=item["id"], username=item["username"], name=item.get("name"))
            for item in payload.get("data", [])
        ]

    async def search_tweets(
        self,
        query: str,
        start_time: datetime,
        max_results: int,
    ) -> dict[str, Any]:
        params = {
            "query": query,
            "max_results": max(10, min(100, max_results)),
            "start_time": start_time.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "tweet.fields": "id,text,author_id,created_at,public_metrics",
            "expansions": "author_id",
            "user.fields": "username,name",
        }
        return await self._request("GET", "/tweets/search/recent", params=params)

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        backoff = self._config.request_backoff_seconds
        last_exc: Exception | None = None
        for attempt in range(1, self._config.request_retries + 2):
            try:
                response = await self._client.request(method, path, params=params)
            except httpx.HTTPError as exc:
                last_exc = exc
            else:
                if response.status_code == 429:
                    reset_after = response.headers.get("x-rate-limit-reset")
                    delay = (
                        backoff
                        if not reset_after
                        else max(1, int(float(reset_after)) - int(_utc_now().timestamp()))
                    )
                    LOGGER.warning("X API rate limit hit; sleeping %s", delay)
                    await asyncio.sleep(delay)
                    backoff *= 2
                    continue
                if response.is_success:
                    return response.json()
                last_exc = XApiError(
                    f"X API error {response.status_code}: {response.text}"
                )
            await asyncio.sleep(backoff)
            backoff *= 2
        raise XApiError(f"X API request failed after retries: {last_exc}") from last_exc


class XSearchTool:
    """Orchestrates tweet search with community expansion."""

    def __init__(self, config: XSearchConfig | None = None):
        self._config = config or XSearchConfig()

    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            request = XSearchRequest(**payload)
        except ValidationError as exc:
            raise ValueError(f"invalid payload: {exc}") from exc

        async with XApiClient(self._config) as client:
            # If no username provided, do keyword-only search
            if request.username is None:
                tweets = await self._fetch_tweets_keyword_only(client, request)
                seed_user_str = "(keyword search)"
                related_users = []
            else:
                seed_user = await client.get_user_by_username(request.username)
                related_users = await self._expand_related_users(client, seed_user)
                tweets = await self._fetch_tweets(client, seed_user, related_users, request)
                seed_user_str = seed_user.username

        response = XSearchResponse(
            topic=request.topic,
            seed_user=seed_user_str,
            start_time=request.start_time,
            generated_at=_utc_now(),
            tweets=tweets,
            related_users=related_users,
        )
        return response.model_dump()

    async def _fetch_tweets_keyword_only(
        self,
        client: XApiClient,
        request: XSearchRequest,
    ) -> list[TweetResult]:
        """Fetch tweets using keyword search only (no user filter)."""
        query = self._build_query(
            topic=request.topic,
            usernames=[],  # No user filter
            lang=request.lang,
            include_retweets=request.include_retweets,
            include_replies=request.include_replies,
            verified_only=request.verified_only,
        )
        
        LOGGER.info("Keyword-only search query: %s", query[:100])
        
        # Fetch in batches since X API limits to 100 per request
        all_tweets: list[TweetResult] = []
        remaining = request.max_tweets
        
        # For now, single request (X API recent search doesn't support cursor well)
        payload = await client.search_tweets(
            query=query,
            start_time=request.start_time,
            max_results=min(100, remaining),
        )
        all_tweets.extend(self._map_tweets(payload))
        
        # Log sphere context if specified
        if request.sphere:
            sphere = get_sphere(request.sphere)
            if sphere:
                LOGGER.info(
                    "Sphere context for filtering: %s",
                    sphere.name,
                )
        
        deduped = self._dedupe_tweets(all_tweets)
        deduped.sort(key=lambda t: t.created_at, reverse=True)
        return deduped[: request.max_tweets]

    async def _expand_related_users(
        self,
        client: XApiClient,
        seed_user: _User,
    ) -> list[RelatedUser]:
        if self._config.max_related_users == 0:
            return []

        sample_followers = await client.get_followers(
            seed_user.id,
            max_results=self._config.follower_sample_size,
        )
        if not sample_followers:
            return []

        sampled = sample_followers[: self._config.follower_sample_size]
        random.shuffle(sampled)
        sampled = sampled[: self._config.follower_sample_size]

        semaphore = asyncio.Semaphore(self._config.graph_concurrency)
        counts: Counter[str] = Counter()
        user_cache: dict[str, _User] = {}

        async def _fan_out(follower: _User) -> None:
            async with semaphore:
                following = await client.get_following(
                    follower.id,
                    max_results=self._config.following_sample_per_follower,
                )
            for followed in following:
                if followed.id == seed_user.id:
                    continue
                counts[followed.id] += 1
                user_cache.setdefault(followed.id, followed)

        await asyncio.gather(*[_fan_out(user) for user in sampled])
        total = max(len(sampled), 1)
        scored = [
            RelatedUser(
                id=user_id,
                username=user_cache[user_id].username,
                name=user_cache[user_id].name,
                score=counts[user_id] / total,
            )
            for user_id in counts
        ]
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[: self._config.max_related_users]

    async def _fetch_tweets(
        self,
        client: XApiClient,
        seed_user: _User,
        related_users: list[RelatedUser],
        request: XSearchRequest,
    ) -> list[TweetResult]:
        all_tweets: list[TweetResult] = []

        # Search seed user's tweets
        seed_query = self._build_query(
            topic=request.topic,
            usernames=[seed_user.username],
            lang=request.lang,
            include_retweets=request.include_retweets,
            include_replies=request.include_replies,
            verified_only=request.verified_only,
        )
        seed_payload = await client.search_tweets(
            query=seed_query,
            start_time=request.start_time,
            max_results=min(100, request.max_tweets),
        )
        all_tweets.extend(self._map_tweets(seed_payload))

        # Log sphere context if specified (spheres are descriptive, not user lists)
        if request.sphere:
            sphere = get_sphere(request.sphere)
            if sphere:
                LOGGER.info(
                    "Search context: %s sphere - %s",
                    sphere.name,
                    sphere.vibe[:100],
                )

        # Search related users individually (from graph expansion)
        if related_users:
            semaphore = asyncio.Semaphore(self._config.search_concurrency)

            async def _search(target: RelatedUser) -> list[TweetResult]:
                async with semaphore:
                    query = self._build_query(
                        topic=request.topic,
                        usernames=[target.username],
                        lang=request.lang,
                        include_retweets=request.include_retweets,
                        include_replies=request.include_replies,
                        verified_only=request.verified_only,
                    )
                    payload = await client.search_tweets(
                        query=query,
                        start_time=request.start_time,
                        max_results=50,
                    )
                return self._map_tweets(payload)

            tweet_batches = await asyncio.gather(
                *(_search(user) for user in related_users)
            )
            for batch in tweet_batches:
                all_tweets.extend(batch)

        deduped = self._dedupe_tweets(all_tweets)
        deduped.sort(key=lambda t: t.created_at, reverse=True)
        return deduped[: request.max_tweets]

    @staticmethod
    def _map_tweets(payload: dict[str, Any]) -> list[TweetResult]:
        data = payload.get("data", [])
        includes = {
            user["id"]: user for user in payload.get("includes", {}).get("users", [])
        }
        results: list[TweetResult] = []
        for item in data:
            author = includes.get(item["author_id"])
            if not author:
                continue
            metrics = item.get("public_metrics", {})
            tweet = TweetResult(
                id=item["id"],
                text=item["text"],
                author_username=author["username"],
                author_name=author.get("name"),
                created_at=datetime.fromisoformat(
                    item["created_at"].replace("Z", "+00:00")
                ),
                like_count=metrics.get("like_count"),
                reply_count=metrics.get("reply_count"),
                retweet_count=metrics.get("retweet_count"),
                quote_count=metrics.get("quote_count"),
                url=f"https://x.com/{author['username']}/status/{item['id']}",
            )
            results.append(tweet)
        return results

    @staticmethod
    def _dedupe_tweets(tweets: Iterable[TweetResult]) -> list[TweetResult]:
        seen: set[str] = set()
        deduped: list[TweetResult] = []
        for tweet in tweets:
            if tweet.id in seen:
                continue
            seen.add(tweet.id)
            deduped.append(tweet)
        return deduped

    @staticmethod
    def _build_query(
        topic: str,
        usernames: list[str],
        lang: str | None,
        include_retweets: bool,
        include_replies: bool,
        verified_only: bool = False,
    ) -> str:
        clauses = [f"({topic})"]
        
        # Build from clause only if usernames provided
        if usernames:
            if len(usernames) == 1:
                from_clause = f"from:{usernames[0]}"
            else:
                from_clause = "(" + " OR ".join(f"from:{u}" for u in usernames) + ")"
            clauses.append(from_clause)
        
        if not include_retweets:
            clauses.append("-is:retweet")
        if not include_replies:
            clauses.append("-is:reply")
        if lang:
            clauses.append(f"lang:{lang}")
        if verified_only:
            clauses.append("is:verified")
        return " ".join(clauses)


async def run_tool(
    payload: dict[str, Any], config: XSearchConfig | None = None
) -> dict[str, Any]:
    """Convenience coroutine to execute the tool."""
    tool = XSearchTool(config=config)
    return await tool.run(payload)


def run_tool_sync(
    payload: dict[str, Any], config: XSearchConfig | None = None
) -> dict[str, Any]:
    """Sync helper for blocking call environments."""

    def _runner() -> dict[str, Any]:
        return asyncio.run(run_tool(payload, config=config))

    return _runner()


# Backwards compatibility aliases
GrokXTool = XSearchTool
GrokXToolConfig = XSearchConfig
GrokXToolRequest = XSearchRequest
GrokXToolResponse = XSearchResponse


