"""Thin CLI wrapper so you can smoke-test the tool locally."""

import argparse
import asyncio
import json
from datetime import datetime

from .tool import GrokXToolConfig, run_tool


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Grok X graph tool once")
    parser.add_argument("--username", required=True, help="Seed username (without @)")
    parser.add_argument("--topic", required=True, help="Topic keywords to search")
    parser.add_argument(
        "--start-time",
        required=True,
        help="ISO-8601 timestamp (e.g. 2025-12-07T00:00:00Z)",
    )
    parser.add_argument("--max-tweets", type=int, default=50)
    parser.add_argument("--lang", default="en")
    parser.add_argument("--include-retweets", action="store_true")
    parser.add_argument("--include-replies", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    payload = {
        "username": args.username,
        "topic": args.topic,
        "start_time": datetime.fromisoformat(args.start_time.replace("Z", "+00:00")).isoformat(),
        "max_tweets": args.max_tweets,
        "lang": args.lang,
        "include_retweets": args.include_retweets,
        "include_replies": args.include_replies,
    }
    config = GrokXToolConfig()
    result = asyncio.run(run_tool(payload, config=config))
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()


