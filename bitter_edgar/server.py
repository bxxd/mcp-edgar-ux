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

# Suppress INFO logs
logging.getLogger("edgar").setLevel(logging.WARNING)

# Default cache directory (can be overridden via env var or CLI arg)
CACHE_DIR = Path(os.getenv("BITTER_EDGAR_CACHE_DIR", "/tmp/sec-filings"))

# Initialize MCP server
mcp = FastMCP("bitter-edgar")


@mcp.tool()
def fetch_filing(
    ticker: str,
    form_type: str,
    date: Optional[str] = None,
    format: str = "markdown"
) -> dict:
    """
    Download SEC filing to disk, return path.

    The Bitter Lesson: Don't dump 241K tokens into context.
    Save to disk, read what you need.

    Args:
        ticker: Stock ticker (e.g., "TSLA", "AAPL")
        form_type: Form type ("10-K", "10-Q", "8-K", etc.)
        date: Optional specific date (YYYY-MM-DD), defaults to most recent
        format: Output format - "markdown" (default), "text", or "html"

    Returns:
        Dictionary with file path and metadata. Use Read/Grep/Bash on the path.

    Example:
        fetch_filing("TSLA", "10-K")
        → {path: "/tmp/sec-filings/TSLA/10-K/2025-01-30.md", ...}

        Then: Read("/tmp/sec-filings/TSLA/10-K/2025-01-30.md")
    """
    try:
        return core_fetch_filing(
            ticker=ticker,
            form_type=form_type,
            cache_dir=str(CACHE_DIR),
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


def main():
    """Main entry point for the MCP server."""
    global CACHE_DIR

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
        default=8080,
        help="Port to bind to for HTTP transport (default: 8080)"
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
