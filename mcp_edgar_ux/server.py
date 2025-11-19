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
    max_results: int = 20,
    offset: int = 0,
    case_sensitive: bool = False
) -> dict:
    """
    Search for text in a cached SEC filing (grep-like with line numbers).

    Auto-fetches filing if not cached. Returns matching lines with context.
    Case-insensitive by default. Full regex support.

    Args:
        ticker: Stock ticker (e.g., "TSLA", "AAPL")
        form_type: Form type ("10-K", "10-Q", "8-K", etc.)
        pattern: Search pattern (full regex support, case-insensitive default)
        date: Optional date filter (YYYY-MM-DD) to select specific filing
        context_lines: Number of context lines before/after match (default: 2)
        max_results: Maximum matches to return (default: 20)
        offset: Number of matches to skip for pagination (default: 0)
        case_sensitive: Case-sensitive search (default: False)

    Returns:
        Dictionary with matches, line numbers, context, and file path

    Pattern Tips:
        - OR patterns work: "revenue|revenues|sales" (tries all terms)
        - Regex works: "property.*equipment" (matches "property and equipment")
        - Start broad: Try "equipment" before "capital expenditure"
        - Text may wrap: "Property and equipment" might span 2 lines in filing
        - Case-insensitive by default: "Revenue" matches "REVENUE", "revenue"

    Examples:
        # Simple search
        search_filing("TSLA", "10-K", "revenue")
        → {matches: [...], count: 6, total_lines: 5819}

        # OR pattern (try multiple terms)
        search_filing("LLY", "10-Q", "capex|capital expenditure|PP&E")
        → Searches for ANY of those terms

        # Regex pattern (flexible matching)
        search_filing("LLY", "10-Q", "property.*equipment")
        → Matches "property and equipment", "property, plant and equipment"

        # If no matches, try broader terms
        search_filing("LLY", "10-Q", "equipment")  # Simpler, more likely to match

        # Use file path for deep dive at specific line
        result = search_filing("TSLA", "10-K", "risk factors")
        Read(result["path"], offset=LINE_FROM_RESULT, limit=50)
    """
    try:
        return await core_search_filing(
            ticker=ticker,
            form_type=form_type,
            pattern=pattern,
            cache_dir=str(CACHE_DIR),
            date=date,
            context_lines=context_lines,
            max_results=max_results,
            offset=offset,
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
