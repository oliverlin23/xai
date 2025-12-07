# X API Cheatsheet for Grok Tooling

This note distills the parts of the public X (formerly Twitter) API that matter
for the Grok graph-aware tweet retriever. Always cross-check the live
documentation inside the X Developer Portal for quotas that change frequently.

## Auth & Products

- **Essential** tier (free) does *not* allow follower graph fan-out or advanced
  search. You need at least **Pro** (formerly Elevated) or **Enterprise**.
- Use **OAuth 2.0 App-Only** flow for server tools. The resulting bearer token
  carries the `tweet.read`, `users.read`, and `follows.read` scopes.
- Store the token in a secure secret manager; never embed in the Grok tool body.

## Core Endpoints Used

| Purpose | Endpoint | Notes |
| --- | --- | --- |
| Resolve username | `GET /2/users/by/username/:username` | Request `user.fields=created_at,verified,public_metrics`. |
| Followers sample | `GET /2/users/:id/followers` | `max_results` up to 1,000 on Pro; 200 default. Paginate via `pagination_token`. |
| Following (friends) sample | `GET /2/users/:id/following` | Same contract as followers. |
| Recent search | `GET /2/tweets/search/recent` | 7-day history. Requires `query`, optional `start_time`, `end_time`. Add `expansions=author_id` and matching `user.fields`. |

### Rate Limits (as of 2024-10)

- Recent search: 450 requests / 15 min / app on Pro.
- Followers/following: 15 requests / 15 min / app.
- Username lookup: 75 requests / 15 min / app.

Always implement adaptive backoff (`Retry-After` header) and cut off fan-out when
close to the cap.

## Query Construction Tips

- Combine topic keywords with the `from:` operator for author scoping, e.g.
  `"(agentic OR 'ai agent') (from:xai OR from:merlin)"`.
- Use `lang:en` or the locale relevant to your use case to reduce noise.
- `start_time` must be RFC 3339 with timezone, e.g. `2025-12-07T00:00:00Z`.
- Add `-is:retweet` or `-is:reply` if you only want original tweets.

## Graph-Based Expansion Strategy

1. Resolve the seed account (user input).
2. Pull up to *N* followers (e.g., 400) to capture the audience.
3. For each follower, fetch who they follow (limited sample). Maintain a counter
   keyed by `user_id`.
4. Score by `co_follow_count / total_followers_sampled` to capture "people who
   followers also follow."
5. Drop the seed user and verified organizations already included to avoid
   redundancy.
6. Use the highest-scoring *k* accounts as additional `from:` clauses.

## Error Handling

- HTTP 429 → read `x-rate-limit-reset` to decide the sleep duration.
- HTTP 503/504 → exponential backoff with jitter.
- Missing data (`errors` array) → log and skip rather than fail the full batch.

## Compliance

- Respect user privacy: do not persist follower graphs beyond the time required
  to fulfill the Grok tool call.
- Cache only transiently in memory; persistent caching requires additional
  review per X policy.
- Display requirements: if surface renders tweet text, abide by X's display
  policy (author name, handle, timestamp, link).

## Useful References

- <https://developer.x.com/en/docs/twitter-api/users/lookup/introduction>
- <https://developer.x.com/en/docs/twitter-api/tweets/search/introduction>
- <https://developer.x.com/en/docs/twitter-api/users/follows/api-reference/get-users-id-followers>


