#!/usr/bin/env python3
"""
CLI for bitter-edgar MCP - test tools without MCP restart

Usage:
  ./cli list-tools                        # Show MCP tool definitions
  ./cli fetch TSLA 10-K                   # Fetch filing (uses env CACHE_DIR or /tmp/sec-filings)
  ./cli fetch TSLA 10-K --date 2024-01-01 # Fetch specific date
  ./cli fetch TSLA 10-K --format markdown # Fetch as markdown
  ./cli list                              # List all cached filings
  ./cli list --ticker TSLA                # List TSLA filings
  ./cli list --form-type 10-K             # List all 10-Ks

Fast iteration: Calls core.py functions directly (no MCP layer)
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from .core import fetch_filing as core_fetch_filing
from .core import list_cached_filings as core_list_cached
from .core import list_filings as core_list_filings
from .core import search_filing as core_search_filing
from .server_http import format_cached_list, format_filing_result, format_filings_list, format_search_result, list_tools


def get_default_cache_dir() -> str:
    """Get default cache directory from env or use fallback"""
    return os.environ.get("CACHE_DIR", "/var/idio-mcp-cache/sec-filings")


async def list_tools_command() -> int:
    """Show MCP tool definitions"""
    tools = await list_tools()

    print("=" * 80)
    print("MCP TOOL DEFINITIONS")
    print("=" * 80)
    print()

    for tool in tools:
        print(f"Tool: {tool.name}")
        print(f"Claude sees: mcp__bitter-edgar__{tool.name}")
        print()
        print("Description:")
        print(tool.description)
        print()
        print("Input Schema:")
        print(json.dumps(tool.inputSchema, indent=2))
        print()
        print("-" * 80)
        print()

    return 0


async def fetch_command(
    ticker: str,
    form_type: str,
    date: str | None,
    format_type: str,
    cache_dir: str,
) -> int:
    """Fetch SEC filing"""
    try:
        result = await core_fetch_filing(
            ticker=ticker,
            form_type=form_type,
            cache_dir=cache_dir,
            date=date,
            format=format_type
        )
        output = format_filing_result(result)
        print(output)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


async def list_command(
    ticker: str | None,
    form_type: str | None,
    cache_dir: str,
) -> int:
    """List cached SEC filings"""
    try:
        result = await core_list_cached(
            cache_dir=cache_dir,
            ticker=ticker,
            form_type=form_type
        )
        output = format_cached_list(result)
        print(output)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


async def list_filings_command(
    ticker: str,
    form_type: str,
    cache_dir: str,
) -> int:
    """List available SEC filings (cached + available from SEC)"""
    try:
        result = await core_list_filings(
            ticker=ticker,
            form_type=form_type,
            cache_dir=cache_dir
        )
        output = format_filings_list(result)
        print(output)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


async def search_command(
    ticker: str,
    form_type: str,
    pattern: str,
    date: str | None,
    context_lines: int,
    max_results: int,
    offset: int,
    cache_dir: str,
) -> int:
    """Search SEC filing"""
    try:
        result = await core_search_filing(
            ticker=ticker,
            form_type=form_type,
            pattern=pattern,
            cache_dir=cache_dir,
            date=date,
            context_lines=context_lines,
            max_results=max_results,
            offset=offset
        )
        output = format_search_result(result)
        print(output)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""
    default_cache = get_default_cache_dir()

    parser = argparse.ArgumentParser(
        description="CLI for bitter-edgar MCP tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  %(prog)s list-tools                              # Show tool definitions
  %(prog)s list-filings TSLA 10-K                  # List available TSLA 10-K filings (cached + SEC)
  %(prog)s fetch TSLA 10-K                         # Fetch latest TSLA 10-K
  %(prog)s fetch TSLA 10-K --date 2024-01-01       # Fetch TSLA 10-K >= date
  %(prog)s search TSLA 10-K "supply chain"         # Search for "supply chain"
  %(prog)s search TSLA 10-K "rare earth" --context 3  # More context lines
  %(prog)s list                                    # List all cached filings
  %(prog)s list --ticker TSLA                      # List TSLA filings only

Cache directory: {default_cache} (from CACHE_DIR env or default)
        """
    )

    parser.add_argument(
        "--cache-dir",
        default=default_cache,
        help=f"Cache directory (default: $CACHE_DIR or {default_cache})"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # list-tools command
    subparsers.add_parser("list-tools", help="Show MCP tool definitions")

    # fetch command
    fetch_parser = subparsers.add_parser("fetch", help="Fetch SEC filing")
    fetch_parser.add_argument("ticker", help="Stock ticker (e.g., TSLA)")
    fetch_parser.add_argument("form_type", help="Form type (e.g., 10-K, 10-Q, 8-K)")
    fetch_parser.add_argument(
        "--date",
        help="Optional date filter (YYYY-MM-DD). Returns filing >= date."
    )
    fetch_parser.add_argument(
        "--format",
        choices=["text", "markdown", "html"],
        default="text",
        help="Output format (default: text)"
    )

    # list command
    list_parser = subparsers.add_parser("list", help="List cached SEC filings")
    list_parser.add_argument(
        "--ticker",
        help="Optional ticker filter (e.g., TSLA)"
    )
    list_parser.add_argument(
        "--form-type",
        help="Optional form type filter (e.g., 10-K)"
    )

    # list-filings command
    list_filings_parser = subparsers.add_parser("list-filings", help="List available SEC filings (cached + SEC)")
    list_filings_parser.add_argument("ticker", help="Stock ticker (e.g., TSLA)")
    list_filings_parser.add_argument("form_type", help="Form type (e.g., 10-K, 10-Q)")

    # search command
    search_parser = subparsers.add_parser("search", help="Search SEC filing")
    search_parser.add_argument("ticker", help="Stock ticker (e.g., TSLA)")
    search_parser.add_argument("form_type", help="Form type (e.g., 10-K)")
    search_parser.add_argument("pattern", help="Search pattern (regex supported)")
    search_parser.add_argument(
        "--date",
        help="Optional date filter (YYYY-MM-DD)"
    )
    search_parser.add_argument(
        "--context",
        type=int,
        default=2,
        help="Lines of context before/after match (default: 2)"
    )
    search_parser.add_argument(
        "--max-results",
        type=int,
        default=20,
        help="Maximum matches to return (default: 20)"
    )
    search_parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Number of matches to skip for pagination (default: 0)"
    )

    return parser.parse_args()


async def async_main() -> int:
    args = parse_args()

    if not args.command:
        print("Error: No command specified")
        print("Usage: ./cli list-tools | fetch <ticker> <form> | search <ticker> <form> <pattern> | list [options]")
        return 1

    if args.command == "list-tools":
        return await list_tools_command()

    if args.command == "fetch":
        return await fetch_command(
            ticker=args.ticker,
            form_type=args.form_type,
            date=args.date,
            format_type=args.format,
            cache_dir=args.cache_dir,
        )

    if args.command == "list-filings":
        return await list_filings_command(
            ticker=args.ticker,
            form_type=args.form_type,
            cache_dir=args.cache_dir,
        )

    if args.command == "search":
        return await search_command(
            ticker=args.ticker,
            form_type=args.form_type,
            pattern=args.pattern,
            date=args.date,
            context_lines=args.context,
            max_results=args.max_results,
            offset=args.offset,
            cache_dir=args.cache_dir,
        )

    if args.command == "list":
        return await list_command(
            ticker=args.ticker,
            form_type=args.form_type,
            cache_dir=args.cache_dir,
        )

    print(f"Unknown command: {args.command}")
    return 1


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    sys.exit(main())
