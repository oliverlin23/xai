from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import ListToolsResult, TextContent, Tool
from pydantic import ValidationError

from .tool import COMMUNITIES, GrokXToolConfig, run_tool


def _json_serializer(obj: Any) -> Any:
    """Custom JSON serializer for objects not serializable by default."""
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if hasattr(obj, "__str__"):
        return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

SERVER_NAME = "grok-x-tool"
TOOL_NAME = "grok_x_related_tweets"

server = Server(
    name=SERVER_NAME,
    instructions="Fetch topic-focused tweets plus graph-adjacent accounts via the X API.",
)

REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "topic": {
            "type": "string",
            "description": "Topic or boolean query to search within tweets",
        },
        "username": {
            "type": "string",
            "description": "Seed X username (without @) whose audience will be expanded",
        },
        "start_time": {
            "type": "string",
            "description": "ISO-8601 timestamp (UTC) to bound the search window",
        },
        "max_tweets": {
            "type": "integer",
            "minimum": 1,
            "maximum": 200,
            "default": 10,
            "description": "Maximum number of tweets to return after dedupe",
        },
        "lang": {
            "type": ["string", "null"],
            "description": "Language code (e.g., en). Null means no filter.",
        },
        "include_retweets": {
            "type": "boolean",
            "default": False,
            "description": "Set true to allow retweets in the result set",
        },
        "include_replies": {
            "type": "boolean",
            "default": False,
            "description": "Set true to allow replies in the result set",
        },
        "max_related_users": {
            "type": "integer",
            "minimum": 0,
            "maximum": 50,
            "default": 0,
            "description": "Number of related users (from seed user's follower graph) to also search. Set >0 to expand search to the user's 'circle'.",
        },
        "follower_sample_size": {
            "type": "integer",
            "minimum": 1,
            "maximum": 20,
            "default": 3,
            "description": "Number of seed user's followers to sample for graph expansion.",
        },
        "following_sample_per_follower": {
            "type": "integer",
            "minimum": 1,
            "maximum": 20,
            "default": 5,
            "description": "Number of accounts to check per sampled follower.",
        },
        "community": {
            "type": ["string", "null"],
            "enum": [None] + list(COMMUNITIES.keys()),
            "default": None,
            "description": f"Community sphere to also search. Options: {', '.join(COMMUNITIES.keys())}. Uses batched query (1 API call) for efficiency.",
        },
    },
    "required": ["topic", "username", "start_time"],
}


@server.list_tools()
async def _list_tools(_: Any = None) -> ListToolsResult:
    tool = Tool(
        name=TOOL_NAME,
        description=(
            "Fetch tweets about a topic from a seed user and graph-adjacent accounts "
            "using the X API with popularity-based fan-out."
        ),
        inputSchema=REQUEST_SCHEMA,
    )
    return ListToolsResult(tools=[tool])


@server.call_tool()
async def _call_tool(name: str, arguments: dict[str, Any] | None):
    if name != TOOL_NAME:
        return [
            TextContent(type="text", text=f"Unknown tool '{name}'. Available: {TOOL_NAME}"),
        ]

    args = arguments or {}
    payload = {
        "topic": args.get("topic"),
        "username": args.get("username"),
        "start_time": args.get("start_time", datetime.now(tz=UTC).isoformat()),
        "max_tweets": args.get("max_tweets", 10),
        "lang": args.get("lang", "en"),
        "include_retweets": args.get("include_retweets", False),
        "include_replies": args.get("include_replies", False),
        "community": args.get("community"),
    }
    config = GrokXToolConfig(
        max_related_users=args.get("max_related_users", 0),
        follower_sample_size=args.get("follower_sample_size", 3),
        following_sample_per_follower=args.get("following_sample_per_follower", 5),
    )
    try:
        result = await run_tool(payload, config=config)
    except ValidationError as exc:
        return [TextContent(type="text", text=f"Invalid payload: {exc}")]
    except Exception as exc:
        return [TextContent(type="text", text=f"Tool failed: {exc}")]

    response = {
        "topic": result["topic"],
        "seed_user": result["seed_user"],
        "start_time": result["start_time"],
        "generated_at": result["generated_at"],
        "tweet_count": len(result["tweets"]),
        "tweets": result["tweets"],
        "related_users": result["related_users"],
    }
    return [TextContent(type="text", text=json.dumps(response, default=_json_serializer, indent=2))]


async def amain() -> None:
    """Entrypoint used by `python -m grok_tool.mcp_server`."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(NotificationOptions(tools_changed=False)),
        )


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()


