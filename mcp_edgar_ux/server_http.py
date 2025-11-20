#!/usr/bin/env python3
"""
MCP HTTP/SSE Server - Hexagonal Architecture

Clean HTTP/SSE server using dependency injection and hexagonal architecture.

Run with: make server (or: poetry run uvicorn mcp_edgar_ux.server_http:app --host 127.0.0.1 --port 5002)

Configuration:
- PORT: Server port (default: 5002)
- CACHE_DIR: Filing cache directory (default: /var/idio-mcp-cache/sec-filings)
"""

import os
import signal
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent, Tool
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from .container import Container
from .adapters.mcp import TOOL_SCHEMAS, MCPHandlers

# Configuration
DEFAULT_PORT = 5002
DEFAULT_CACHE_DIR = "/var/idio-mcp-cache/sec-filings"
DEFAULT_USER_AGENT = "breed research breed@idio.sh"


def get_port() -> int:
    """Get server port from environment or use default"""
    port_str = os.environ.get("PORT", str(DEFAULT_PORT))
    try:
        return int(port_str)
    except ValueError:
        msg = f"Invalid PORT value: {port_str}"
        raise ValueError(msg) from None


def get_cache_dir() -> Path:
    """Get cache directory from environment or use default"""
    cache_str = os.environ.get("CACHE_DIR", DEFAULT_CACHE_DIR)
    return Path(cache_str)


def get_user_agent() -> str:
    """Get user agent from environment or use default"""
    return os.environ.get("USER_AGENT", DEFAULT_USER_AGENT)


# Initialize dependency injection container
container = Container(
    cache_dir=get_cache_dir(),
    user_agent=get_user_agent()
)

# Initialize MCP handlers
handlers = MCPHandlers(container)

# MCP Server instance
mcp_server = Server("edgar-ux-mcp")

# SSE transport for multi-client support
sse_transport = SseServerTransport("/messages")


@mcp_server.list_tools()  # type: ignore[misc,no-untyped-call]
async def list_tools() -> list[Tool]:
    """List available MCP tools"""
    return [
        Tool(**TOOL_SCHEMAS["fetch_filing"]),
        Tool(**TOOL_SCHEMAS["search_filing"]),
        Tool(**TOOL_SCHEMAS["list_filings"]),
        Tool(**TOOL_SCHEMAS["list_cached"]),
    ]


@mcp_server.call_tool()  # type: ignore[misc,no-untyped-call]
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls"""

    if name == "fetch_filing":
        result = await handlers.fetch_filing(
            ticker=arguments["ticker"],
            form_type=arguments["form_type"],
            date=arguments.get("date"),
            format=arguments.get("format", "text"),
            preview_lines=arguments.get("preview_lines", 50)
        )

    elif name == "search_filing":
        result = await handlers.search_filing(
            ticker=arguments["ticker"],
            form_type=arguments["form_type"],
            pattern=arguments["pattern"],
            date=arguments.get("date"),
            format=arguments.get("format", "text"),
            context_lines=arguments.get("context_lines", 2),
            max_results=arguments.get("max_results", 20),
            offset=arguments.get("offset", 0)
        )

    elif name == "list_filings":
        result = await handlers.list_filings(
            ticker=arguments["ticker"],
            form_type=arguments["form_type"]
        )

    elif name == "list_cached":
        result = await handlers.list_cached(
            ticker=arguments.get("ticker"),
            form_type=arguments.get("form_type")
        )

    else:
        return [TextContent(
            type="text",
            text=f"Unknown tool: {name}"
        )]

    # Format result as BBG Lite text (could be extracted to formatters later)
    import json
    formatted_text = json.dumps(result, indent=2)

    return [TextContent(
        type="text",
        text=formatted_text
    )]


# HTTP routes
async def handle_ping(request: Request) -> Response:
    """Health check endpoint"""
    return JSONResponse({"status": "ok"})


async def handle_sse(request: Request) -> Response:
    """SSE endpoint for MCP communication"""
    print("[MCP-SERVER] New SSE connection from", request.client.host if request.client else "unknown", flush=True)
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        print("[MCP-SERVER] SSE connected, running MCP server loop", flush=True)
        await mcp_server.run(
            streams[0], streams[1], mcp_server.create_initialization_options()
        )
    return Response()


routes = [
    Route("/ping", handle_ping),
    Route("/sse", handle_sse),
    Mount("/messages", app=sse_transport.handle_post_message),
]

app = Starlette(debug=True, routes=routes)


# Graceful shutdown on SIGTERM
def handle_sigterm(signum, frame):
    print("\n[MCP-SERVER] Received SIGTERM, shutting down gracefully...", flush=True)
    import sys
    sys.exit(0)


signal.signal(signal.SIGTERM, handle_sigterm)


if __name__ == "__main__":
    import uvicorn
    port = get_port()
    print(f"Starting MCP HTTP server on port {port}...", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=port)
