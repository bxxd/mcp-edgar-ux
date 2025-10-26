"""
bitter-edgar MCP Server

MCP delivery layer - wraps core.py functions as MCP tools.
Separation of concerns: this file only handles MCP protocol.
"""
import argparse
import logging
import os
from pathlib import Path
from typing import Optional
from mcp.server.fastmcp import FastMCP
from .core import fetch_filing as core_fetch_filing
from .core import list_cached_filings as core_list_cached
from .core import search_filing as core_search_filing

# Suppress INFO logs
logging.getLogger("edgar").setLevel(logging.WARNING)

# Default cache directory (can be overridden via env var or CLI arg)
CACHE_DIR = Path(os.getenv("BITTER_EDGAR_CACHE_DIR", "/tmp/sec-filings"))

# Get port from env or default
HTTP_PORT = int(os.getenv("BITTER_EDGAR_HTTP_PORT", "6660"))
HTTP_HOST = os.getenv("BITTER_EDGAR_HTTP_HOST", "0.0.0.0")

# Initialize MCP server with HTTP config
mcp = FastMCP("bitter-edgar", host=HTTP_HOST, port=HTTP_PORT)


@mcp.tool()
def fetch_filing(
    ticker: str,
    form_type: str,
    date: Optional[str] = None,
    format: str = "text"
) -> dict:
    """
    Download SEC filing to disk, return path.

    The Bitter Lesson: Don't dump 241K tokens into context.
    Save to disk, read what you need.

    Args:
        ticker: Stock ticker (e.g., "TSLA", "AAPL")
        form_type: Form type ("10-K", "10-Q", "8-K", etc.)
        date: Optional date filter (YYYY-MM-DD). Returns filing closest >= date. Defaults to most recent.
        format: Output format - "text" (default, clean), "markdown" (may have XBRL), or "html"

    Returns:
        Dictionary with file path and metadata. Use Read/Grep/Bash on the path.

    Example:
        fetch_filing("TSLA", "10-K")
        → {path: "/tmp/sec-filings/TSLA/10-K/2025-01-30.txt", ...}

        fetch_filing("TSLA", "10-K", date="2024-01-01")
        → Returns first 10-K filed on or after 2024-01-01

        Then: Read("/tmp/sec-filings/TSLA/10-K/2025-01-30.txt")
    """
    try:
        return core_fetch_filing(
            ticker=ticker,
            form_type=form_type,
            cache_dir=str(CACHE_DIR),
            date=date,
            format=format
        )
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to fetch filing: {str(e)}"
        }


@mcp.tool()
def list_cached(ticker: Optional[str] = None, form_type: Optional[str] = None) -> dict:
    """
    List SEC filings cached on disk.

    Args:
        ticker: Optional ticker filter
        form_type: Optional form type filter

    Returns:
        List of cached filings with paths
    """
    try:
        return core_list_cached(
            cache_dir=str(CACHE_DIR),
            ticker=ticker,
            form_type=form_type
        )
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to list cached filings: {str(e)}"
        }


@mcp.tool()
async def search_filing(
    ticker: str,
    form_type: str,
    pattern: str,
    date: Optional[str] = None,
    context_lines: int = 2,
    case_sensitive: bool = False
) -> dict:
    """
    Search for text in a cached SEC filing.

    The filing must be fetched first with fetch_filing().
    Returns matching lines with context.

    Args:
        ticker: Stock ticker (e.g., "TSLA", "AAPL")
        form_type: Form type ("10-K", "10-Q", "8-K", etc.)
        pattern: Search pattern (supports regex)
        date: Optional date filter (YYYY-MM-DD) to select specific filing
        context_lines: Number of context lines before/after match (default: 2)
        case_sensitive: Case-sensitive search (default: False)

    Returns:
        Dictionary with matches, line numbers, and context

    Example:
        # First fetch the filing
        fetch_filing("TSLA", "10-K")

        # Then search it
        search_filing("TSLA", "10-K", "revenue")
        → {matches: [...], count: 6, total_lines: 5819}

        # Search with regex
        search_filing("TSLA", "10-K", "revenue|revenues")
    """
    try:
        return await core_search_filing(
            ticker=ticker,
            form_type=form_type,
            pattern=pattern,
            cache_dir=str(CACHE_DIR),
            date=date,
            context_lines=context_lines,
            case_sensitive=case_sensitive
        )
    except Exception as e:
        return {
            "success": False,
            "error": f"Search failed: {str(e)}"
        }


def main():
    """Main entry point for the MCP server."""
    global CACHE_DIR, mcp

    parser = argparse.ArgumentParser(
        description="bitter-edgar: Scale beats cleverness. SEC filings MCP."
    )
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "streamable-http"],
        help="Transport method (default: stdio)"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to for HTTP transport (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=6660,
        help="Port to bind to for HTTP transport (default: 6660)"
    )
    parser.add_argument(
        "--cache-dir",
        default=None,
        help=f"Cache directory for filings (default: {CACHE_DIR}, or set BITTER_EDGAR_CACHE_DIR env var)"
    )
    args = parser.parse_args()

    # Override cache dir if specified
    if args.cache_dir:
        CACHE_DIR = Path(args.cache_dir)

    # Run the server
    if args.transport == "streamable-http":
        print(f"Starting bitter-edgar on http://{args.host}:{args.port}")
        print(f"Cache directory: {CACHE_DIR}")
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
