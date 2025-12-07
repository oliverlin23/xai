# MCP Integration Guide

This repo now exposes the Grok X graph tool as a Model Context Protocol (MCP)
server so MCP-compatible clients (e.g., Cursor, Context7) can call it like any
other tool.

## 1. Install Dependencies

```
uv sync  # or pip install -e . inside an activated virtualenv
```

Ensure `X_BEARER_TOKEN` is exported. The MCP server reads the same environment
variable as the CLI.

## 2. Run the MCP Server

```
uv run python -m grok_tool.mcp_server
```

The server speaks MCP over stdio, so keep it running in the background. Logs are
emitted to stderr.

## 3. Register with Cursor / Context7

Edit `~/.cursor/mcp.json` (or the per-project override) to add an entry:

```json
{
  "mcpServers": {
    "grok_x_tool": {
      "command": "uv",
      "args": ["run", "python", "-m", "grok_tool.mcp_server"]
    },
    "context7": {
      "url": "https://mcp.context7.com/mcp",
      "headers": {
        "CONTEXT7_API_KEY": "YOUR_API_KEY"
      }
    }
  }
}
```

Restart Cursor (or whichever MCP client you use) so it reloads the configuration.

## 4. Call the Tool

Once registered, the tool name is `grok_x_related_tweets`. Required arguments:

- `topic`: keyword or boolean search string
- `username`: seed account without `@`
- `start_time`: ISO 8601 timestamp in UTC (e.g., `2025-12-07T00:00:00Z`)

Optional arguments mirror the CLI flags:

- `max_tweets` (default 10)
- `lang` (default `en`)
- `include_retweets` / `include_replies` (default `false`)

The tool returns a JSON blob identical to the CLI/SDK response so Grok or any
other agent can consume it directly.

## 5. Troubleshooting

- **401 Unauthorized**: ensure your Pro+ bearer token is set in `X_BEARER_TOKEN`.
- **429 Rate limit**: scale down `follower_sample_size` / `max_related_users` via
  environment variables or directly in `GrokXToolConfig`.
- **Command not found**: confirm `uv` (or Python interpreter) is on your PATH in
  the shell Cursor launches MCP servers from.


