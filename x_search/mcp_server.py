"""MCP server for X Search tool."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any

from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import ListToolsResult, TextContent, Tool
from pydantic import ValidationError

from .communities import SPHERES, get_sphere_names
from .tool import XSearchConfig, run_tool

SERVER_NAME = "x-search"
TOOL_NAME = "x_search"


def _json_serializer(obj: Any) -> Any:
    """Custom JSON serializer for objects not serializable by default."""
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if hasattr(obj, "__str__"):
        return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


server = Server(
    name=SERVER_NAME,
    instructions="Search tweets by topic from specific spheres of influence via the X API.",
)

REQUEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "topic": {
            "type": "string",
            "description": "Topic or boolean query to search within tweets (e.g., 'AI', 'trump tariffs', 'bitcoin OR ethereum')",
        },
        "username": {
            "type": "string",
            "description": "Seed X username (without @) to search tweets from",
        },
        "start_time": {
            "type": "string",
            "description": "ISO-8601 timestamp (UTC) to bound the search window (e.g., 2025-12-01T00:00:00Z)",
        },
        "max_tweets": {
            "type": "integer",
            "minimum": 1,
            "maximum": 200,
            "default": 10,
            "description": "Maximum number of tweets to return",
        },
        "lang": {
            "type": ["string", "null"],
            "description": "Language code (e.g., 'en'). Null means no filter.",
        },
        "include_retweets": {
            "type": "boolean",
            "default": False,
            "description": "Set true to include retweets in results",
        },
        "include_replies": {
            "type": "boolean",
            "default": False,
            "description": "Set true to include replies in results",
        },
        "sphere": {
            "type": "string",
            "enum": get_sphere_names(),
            "description": f"Sphere of influence to search. Options: {', '.join(get_sphere_names())}",
        },
        "max_related_users": {
            "type": "integer",
            "minimum": 0,
            "maximum": 50,
            "default": 0,
            "description": "Number of related users (from follower graph) to also search. Usually 0 - use community instead.",
        },
    },
    "required": ["topic", "username", "start_time"],
}


@server.list_tools()
async def _list_tools(_: Any = None) -> ListToolsResult:
    tool = Tool(
        name=TOOL_NAME,
        description=(
            "Search tweets about a topic from a specific user and optionally from "
            "a sphere of influence (eacc_sovereign, america_first, blue_establishment, "
            "progressive_left, optimizer_idw, fintwit_market, builder_engineering, "
            "academic_research, osint_intel)."
        ),
        inputSchema=REQUEST_SCHEMA,
    )
    return ListToolsResult(tools=[tool])


@server.call_tool()
async def _call_tool(name: str, arguments: dict[str, Any] | None):
    if name != TOOL_NAME:
        return [
            TextContent(
                type="text", text=f"Unknown tool '{name}'. Available: {TOOL_NAME}"
            ),
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
        "sphere": args.get("sphere"),
    }
    config = XSearchConfig(
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
    return [
        TextContent(
            type="text", text=json.dumps(response, default=_json_serializer, indent=2)
        )
    ]


async def amain() -> None:
    """Async entrypoint for the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(
                NotificationOptions(tools_changed=False)
            ),
        )


def main() -> None:
    """Sync entrypoint for the MCP server."""
    asyncio.run(amain())


if __name__ == "__main__":
    main()


