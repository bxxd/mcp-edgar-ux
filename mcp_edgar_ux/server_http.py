#!/usr/bin/env python3
"""
bitter-edgar MCP Server - HTTP/SSE transport

Network server for multi-tenant Claude Code access.
Same MCP protocol as stdio server, different transport.

Run with: make server (or: poetry run uvicorn bitter_edgar.server_http:app --host 127.0.0.1 --port 5002)

Configuration:
- PORT: Server port (default: 5002)
- CACHE_DIR: Filing cache directory (default: /tmp/sec-filings)
"""

import os
import signal
from pathlib import Path
from typing import Any, Optional

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent, Tool
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from .core import fetch_filing as core_fetch_filing
from .core import list_cached_filings as core_list_cached
from .core import list_filings as core_list_filings
from .core import search_filing as core_search_filing

# Configuration
DEFAULT_PORT = 5002
DEFAULT_CACHE_DIR = "/var/idio-mcp-cache/sec-filings"


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


# Cache directory (shared across all users - SEC filings are public data)
CACHE_DIR = get_cache_dir()

# MCP Server instance
mcp_server = Server("bitter-edgar-mcp")

# SSE transport for multi-client support
sse_transport = SseServerTransport("/messages")


@mcp_server.list_tools()  # type: ignore[misc,no-untyped-call]
async def list_tools() -> list[Tool]:
    """List available MCP tools"""
    return [
        Tool(
            name="fetch_filing",
            description="""
Download SEC filing to disk, return path + preview.

The Bitter Lesson: Don't dump 241K tokens into context.
Save to disk, read what you need (Read/Grep/Bash on the path).

Args:
- ticker: Stock ticker (e.g., "TSLA", "AAPL")
- form_type: Form type ("10-K", "10-Q", "8-K", "DEF 14A", etc.)
- date: Optional date filter (YYYY-MM-DD). Returns filing >= date. Defaults to most recent.
- format: Output format - "text" (default, clean), "markdown" (may have XBRL), or "html"
- preview_lines: Number of lines to preview (default: 50, 0 to disable)

Returns:
- path: File path to cached filing (use Read/Grep/Bash)
- preview: First N lines with line numbers (like Read tool)
- metadata: company, ticker, form_type, filing_date, size_bytes, total_lines, etc.

Example:
  fetch_filing(ticker="TSLA", form_type="10-K")
  → Shows path, preview (first 50 lines), metadata

  Then: search_filing("TSLA", "10-K", "supply chain")
  Or: Read(path, offset=100, limit=100)
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker (e.g., 'TSLA', 'AAPL')"
                    },
                    "form_type": {
                        "type": "string",
                        "description": "Form type (e.g., '10-K', '10-Q', '8-K', 'DEF 14A')"
                    },
                    "date": {
                        "type": "string",
                        "description": "Optional date filter (YYYY-MM-DD). Returns filing >= date. Defaults to most recent."
                    },
                    "format": {
                        "type": "string",
                        "enum": ["text", "markdown", "html"],
                        "description": "Output format: 'text' (default, clean), 'markdown' (may have XBRL), 'html'"
                    },
                    "preview_lines": {
                        "type": "integer",
                        "description": "Number of lines to preview (default: 50, 0 to disable)",
                        "default": 50
                    },
                },
                "required": ["ticker", "form_type"]
            }
        ),
        Tool(
            name="search_filing",
            description="""
Search for pattern in SEC filing (like grep with line numbers).

Auto-fetches filing if not cached. Returns matches with surrounding context.
Use this to find specific content in filings without reading the entire document.

Args:
- ticker: Stock ticker (e.g., "TSLA", "AAPL")
- form_type: Form type ("10-K", "10-Q", "8-K", etc.)
- pattern: Search pattern (extended regex: use | for alternation, case-insensitive by default)
- date: Optional date filter (YYYY-MM-DD). Defaults to most recent.
- context_lines: Lines of context before/after match (default: 2)
- max_results: Maximum matches to return (default: 20)

Returns:
- matches: List of matching passages with line numbers
- file_path: Cached filing path (use Read for deep dive)
- match_count: Total number of matches found

Example:
  search_filing(ticker="TSLA", form_type="10-K", pattern="supply chain")
  → Shows all "supply chain" mentions with line numbers and context

  search_filing(ticker="LNG", form_type="10-Q", pattern="Corpus Christi|Stage 3|expansion")
  → Shows matches for ANY of these terms (extended regex with | alternation)

  Then: Read(path, offset=1230, limit=50)  # Deep dive at specific line
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker (e.g., 'TSLA', 'AAPL')"
                    },
                    "form_type": {
                        "type": "string",
                        "description": "Form type (e.g., '10-K', '10-Q', '8-K')"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Search pattern (regex supported, case-insensitive)"
                    },
                    "date": {
                        "type": "string",
                        "description": "Optional date filter (YYYY-MM-DD). Defaults to most recent."
                    },
                    "context_lines": {
                        "type": "integer",
                        "description": "Lines of context before/after match (default: 2)",
                        "default": 2
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum matches to return (default: 20)",
                        "default": 20
                    }
                },
                "required": ["ticker", "form_type", "pattern"]
            }
        ),
        Tool(
            name="list_filings",
            description="""
List available SEC filings for ticker/form (both cached + available from SEC).

Discovery tool - shows which filings exist and which are already cached.
Use this BEFORE fetch_filing to see what's available.

Args:
- ticker: Stock ticker (e.g., "TSLA", "AAPL")
- form_type: Form type ("10-K", "10-Q", "8-K", etc.)

Returns:
- filings: List of all available filings (sorted by date, newest first)
- Each filing shows: filing_date, cached (✓ or blank), size (if cached)
- Shows which filings need to be fetched vs already cached

Example:
  list_filings(ticker="TSLA", form_type="10-K")
  → Shows all TSLA 10-K filings available (20+ years)
  → Indicates which are cached locally

  Then: fetch_filing("TSLA", "10-K", "2023-01-31")  # Fetch specific filing
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker (e.g., 'TSLA', 'AAPL')"
                    },
                    "form_type": {
                        "type": "string",
                        "description": "Form type (e.g., '10-K', '10-Q', '8-K')"
                    },
                },
                "required": ["ticker", "form_type"]
            }
        ),
        Tool(
            name="list_cached",
            description="""
List SEC filings cached on disk.

Returns all cached filings with paths, or filter by ticker/form_type.

Args:
- ticker: Optional ticker filter (e.g., "TSLA")
- form_type: Optional form type filter (e.g., "10-K")

Returns:
- filings: List of cached filings with path, ticker, form_type, filing_date, size
- count: Total number of cached filings
- disk_usage_mb: Total disk usage

Example:
  list_cached()  # All cached filings
  list_cached(ticker="TSLA")  # TSLA filings only
  list_cached(form_type="10-K")  # All 10-Ks
""",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Optional ticker filter"
                    },
                    "form_type": {
                        "type": "string",
                        "description": "Optional form type filter"
                    },
                },
                "required": []
            }
        ),
    ]


@mcp_server.call_tool()  # type: ignore[misc]
async def call_tool(name: str, arguments: Any) -> list[TextContent]:  # noqa: ANN401
    """Handle tool execution - thin wrapper around core business logic"""
    print(f"[MCP-SERVER] call_tool: name={name}, arguments={arguments}", flush=True)

    if name == "fetch_filing":
        ticker = arguments.get("ticker")
        form_type = arguments.get("form_type")
        date = arguments.get("date")
        format_type = arguments.get("format", "text")
        preview_lines = arguments.get("preview_lines", 50)

        if not ticker or not form_type:
            msg = "fetch_filing() requires 'ticker' and 'form_type' parameters"
            raise ValueError(msg)

        try:
            result = await core_fetch_filing(
                ticker=ticker,
                form_type=form_type,
                cache_dir=str(CACHE_DIR),
                date=date,
                format=format_type,
                preview_lines=preview_lines
            )
            # Return formatted result as text
            formatted = format_filing_result(result)
            print(f"[MCP-SERVER] fetch_filing({ticker}, {form_type}) returning {len(formatted)} chars", flush=True)
            return [TextContent(type="text", text=formatted)]
        except Exception as e:
            error_msg = f"Failed to fetch filing: {str(e)}"
            print(f"[MCP-SERVER] ERROR: {error_msg}", flush=True)
            return [TextContent(type="text", text=error_msg)]

    if name == "search_filing":
        ticker = arguments.get("ticker")
        form_type = arguments.get("form_type")
        pattern = arguments.get("pattern")
        date = arguments.get("date")
        context_lines = arguments.get("context_lines", 2)
        max_results = arguments.get("max_results", 20)

        if not ticker or not form_type or not pattern:
            msg = "search_filing() requires 'ticker', 'form_type', and 'pattern' parameters"
            raise ValueError(msg)

        try:
            result = await core_search_filing(
                ticker=ticker,
                form_type=form_type,
                pattern=pattern,
                cache_dir=str(CACHE_DIR),
                date=date,
                context_lines=context_lines,
                max_results=max_results
            )
            # Return formatted result as text
            formatted = format_search_result(result)
            print(f"[MCP-SERVER] search_filing({ticker}, {form_type}, '{pattern}') returning {len(formatted)} chars", flush=True)
            return [TextContent(type="text", text=formatted)]
        except Exception as e:
            error_msg = f"Failed to search filing: {str(e)}"
            print(f"[MCP-SERVER] ERROR: {error_msg}", flush=True)
            return [TextContent(type="text", text=error_msg)]

    if name == "list_filings":
        ticker = arguments.get("ticker")
        form_type = arguments.get("form_type")

        if not ticker or not form_type:
            msg = "list_filings() requires 'ticker' and 'form_type' parameters"
            raise ValueError(msg)

        try:
            result = await core_list_filings(
                ticker=ticker,
                form_type=form_type,
                cache_dir=str(CACHE_DIR)
            )
            # Return formatted result as text
            formatted = format_filings_list(result)
            print(f"[MCP-SERVER] list_filings({ticker}, {form_type}) returning {len(formatted)} chars", flush=True)
            return [TextContent(type="text", text=formatted)]
        except Exception as e:
            error_msg = f"Failed to list filings: {str(e)}"
            print(f"[MCP-SERVER] ERROR: {error_msg}", flush=True)
            return [TextContent(type="text", text=error_msg)]

    if name == "list_cached":
        ticker = arguments.get("ticker")
        form_type = arguments.get("form_type")

        try:
            result = await core_list_cached(
                cache_dir=str(CACHE_DIR),
                ticker=ticker,
                form_type=form_type
            )
            # Return formatted result as text
            formatted = format_cached_list(result)
            filter_desc = f"ticker={ticker}, form_type={form_type}" if ticker or form_type else "all"
            print(f"[MCP-SERVER] list_cached({filter_desc}) returning {len(formatted)} chars", flush=True)
            return [TextContent(type="text", text=formatted)]
        except Exception as e:
            error_msg = f"Failed to list cached filings: {str(e)}"
            print(f"[MCP-SERVER] ERROR: {error_msg}", flush=True)
            return [TextContent(type="text", text=error_msg)]

    msg = f"Unknown tool: {name}"
    raise ValueError(msg)


def format_filing_result(result: dict) -> str:
    """Format filing fetch result for display"""
    if not result.get("success", False):
        return f"ERROR: {result.get('error', 'Unknown error')}"

    # Format filing info
    path = result.get("path", "")
    company = result.get("company", "")
    ticker = result.get("ticker", "")
    form_type = result.get("form_type", "")
    filing_date = result.get("filing_date", "")
    format_type = result.get("format", "text")
    size_bytes = result.get("size_bytes", 0)
    size_kb = size_bytes / 1024 if size_bytes else 0
    cached = result.get("cached", False)
    preview = result.get("preview", [])
    total_lines = result.get("total_lines")

    cached_indicator = "(cached)" if cached else "(downloaded)"

    lines = [
        f"{ticker} {form_type} | {filing_date} | FETCHED {cached_indicator}",
        "",
        f"COMPANY:     {company}",
        f"FORM:        {form_type}",
        f"FILED:       {filing_date}",
        f"SIZE:        {size_kb:.0f} KB" + (f" ({total_lines:,} lines)" if total_lines else ""),
        "",
        f"PATH: {path}"
    ]

    # Add preview if present
    if preview:
        lines.extend([
            "",
            f"PREVIEW (first {len(preview)} lines):",
            "─" * 70
        ])
        lines.extend(preview)

    # Add affordances
    lines.extend([
        "",
        f"Try: search_filing(\"{ticker}\", \"{form_type}\", \"SEARCH TERM\") | Read(path, offset=100, limit=100)"
    ])

    return "\n".join(lines)


def format_cached_list(result: dict) -> str:
    """Format cached filings list for display"""
    if not result.get("success", False):
        return f"ERROR: {result.get('error', 'Unknown error')}"

    filings = result.get("filings", [])
    count = result.get("count", 0)
    disk_usage_mb = result.get("disk_usage_mb", 0.0)

    if count == 0:
        return "No cached filings found."

    # Build table
    lines = [
        f"CACHED SEC FILINGS ({count} total, {disk_usage_mb:.1f} MB)",
        "",
        "TICKER  FORM     FILED       SIZE     PATH",
        "─" * 70,
    ]

    for filing in filings[:20]:  # Show first 20
        ticker = filing.get("ticker", "")[:6].ljust(6)
        form_type = filing.get("form_type", "")[:8].ljust(8)
        filing_date = filing.get("filing_date", "")[:10].ljust(10)
        size_mb = filing.get("size_bytes", 0) / (1024 * 1024)
        size_str = f"{size_mb:.2f} MB".ljust(8)
        path = filing.get("path", "")

        lines.append(f"{ticker}  {form_type} {filing_date} {size_str} {path}")

    if count > 20:
        lines.append(f"\n... {count - 20} more filings (use ticker/form_type filters to narrow)")

    return "\n".join(lines)


def format_filings_list(result: dict) -> str:
    """Format filings list (cached + available) for display"""
    if not result.get("success", False):
        error_msg = result.get("error", "Unknown error")
        return f"ERROR: {error_msg}"

    filings = result.get("filings", [])
    count = result.get("count", 0)
    cached_count = result.get("cached_count", 0)
    ticker = result.get("ticker", "")
    form_type = result.get("form_type", "")

    if count == 0:
        return f"No {form_type} filings found for {ticker}"

    # Build table
    lines = [
        f"{ticker} {form_type} FILINGS AVAILABLE",
        "─" * 70,
        "FILED       CACHED  SIZE     [ACTIONS]",
    ]

    for filing in filings[:15]:  # Show first 15
        date = filing.get("filing_date", "")[:10].ljust(10)
        cached = "✓" if filing.get("cached", False) else " "

        # Size (if cached) - check paths dict for any cached format
        size_bytes = None
        paths = filing.get("paths", {})
        if paths:
            # Get size from first available cached format
            for path in paths.values():
                try:
                    from pathlib import Path
                    size_bytes = Path(path).stat().st_size
                    break
                except Exception:
                    pass

        if size_bytes:
            size_kb = size_bytes / 1024
            size_str = f"{size_kb:.0f} KB".ljust(8)
        else:
            size_str = "-".ljust(8)

        # Action example (for first uncached item)
        action = ""
        if not filing.get("cached", False) and not action:
            action = f'fetch_filing("{ticker}", "{form_type}", "{filing.get("filing_date")}")'
            action = ""  # Only show once in header

        lines.append(f"{date}  {cached}       {size_str} {action}")

    if count > 15:
        lines.append(f"\n... {count - 15} more filings")

    # Add affordances
    lines.extend([
        "",
        f"Showing {min(count, 15)} of {count} filings ({cached_count} cached)",
        "",
        f"Try: fetch_filing(ticker, form, date) | search_filing(ticker, form, pattern)"
    ])

    return "\n".join(lines)


def format_search_result(result: dict) -> str:
    """Format search result with BBG Lite styling"""
    if not result.get("success", False):
        return f"ERROR: {result.get('error', 'Unknown error')}"

    matches = result.get("matches", [])
    match_count = result.get("match_count", 0)
    returned = result.get("returned_matches", len(matches))
    truncated = result.get("truncated", False)
    file_path = result.get("file_path", "")
    total_lines = result.get("total_lines")
    pattern = result.get("pattern", "")
    ticker = result.get("ticker", "")
    form_type = result.get("form_type", "")
    filing_date = result.get("filing_date", "")

    # No matches
    if match_count == 0:
        return f"""{ticker} {form_type} | {filing_date} | SEARCH "{pattern}"

NO MATCHES FOUND

PATH: {file_path}
Try: Different search term | Read(path) for full filing
"""

    # Build output
    lines = [
        f'{ticker} {form_type} | {filing_date} | SEARCH "{pattern}"',
        ""
    ]

    # Summary line
    total_str = f"{total_lines:,} lines" if total_lines else "unknown length"
    truncated_str = f" (showing first {returned})" if truncated else ""
    lines.append(f"MATCHES ({match_count} found{truncated_str} | {total_str})")
    lines.append("─" * 70)

    # Format each match group
    for i, match_group in enumerate(matches, 1):
        if i > 1:
            lines.append("")  # Blank line between matches

        # Each line in match_group has format "LINE_NUM:content" or "LINE_NUM-content"
        for line in match_group:
            # Handle both grep formats: "123:match" and "123-context"
            if ':' in line or '-' in line:
                # Find first : or - separator
                sep_idx = min(
                    line.find(':') if ':' in line else len(line),
                    line.find('-') if '-' in line else len(line)
                )
                line_num = line[:sep_idx]
                content = line[sep_idx+1:]

                # Right-align line numbers for readability
                lines.append(f"  {line_num:>6}→{content}")
            else:
                lines.append(f"  {line}")

    lines.append("")
    lines.append(f"PATH: {file_path}")
    lines.append(f'Try: Read(path, offset=LINE, limit=50) | search_filing(..., pattern="OTHER TERM")')

    return "\n".join(lines)


# Starlette endpoint handlers

async def handle_ping(_request: Request) -> JSONResponse:
    """Health check endpoint"""
    return JSONResponse({"status": "ok", "cache_dir": str(CACHE_DIR)})


async def handle_shutdown(_request: Request) -> JSONResponse:
    """Graceful shutdown endpoint"""
    # Send SIGTERM to self for graceful shutdown
    os.kill(os.getpid(), signal.SIGTERM)
    return JSONResponse({"status": "shutting down"})


async def handle_sse(request: Request) -> Response:
    """
    SSE endpoint for MCP protocol.

    Creates a new SSE connection for each client, runs the MCP server
    with the connection streams, and returns when client disconnects.
    """
    client_addr = request.client.host if request.client else "unknown"
    print(f"[MCP-SERVER] New SSE connection from {client_addr}", flush=True)

    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        print("[MCP-SERVER] SSE connected, running MCP server loop", flush=True)
        await mcp_server.run(
            streams[0], streams[1], mcp_server.create_initialization_options()
        )
        print(f"[MCP-SERVER] SSE disconnected from {client_addr}", flush=True)

    # Return empty response to avoid NoneType error (per MCP docs)
    return Response(
        headers={
            "Cache-Control": "no-cache",  # Don't cache filings (user-initiated)
            "X-Content-Type-Options": "nosniff",
        }
    )


# Starlette application
app = Starlette(
    routes=[
        Route("/ping", endpoint=handle_ping, methods=["GET"]),
        Route("/shutdown", endpoint=handle_shutdown, methods=["POST"]),
        Route("/sse", endpoint=handle_sse, methods=["GET"]),
        Mount("/messages", app=sse_transport.handle_post_message),
    ]
)
