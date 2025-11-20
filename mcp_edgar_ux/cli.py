#!/usr/bin/env python3
"""
CLI for edgar-ux MCP - test tools without MCP restart

Usage:
  ./cli list-tools                        # Show MCP tool definitions
  ./cli fetch TSLA 10-K                   # Fetch filing (uses env CACHE_DIR or /tmp/sec-filings)
  ./cli fetch TSLA 10-K --date 2024-01-01 # Fetch specific date
  ./cli fetch TSLA 10-K --format markdown # Fetch as markdown
  ./cli search TSLA 10-K "supply chain"   # Search within filing
  ./cli list-filings TSLA 10-K            # List available filings
  ./cli list-cached                       # List all cached filings
  ./cli list-cached --ticker TSLA         # List TSLA cached filings

Fast iteration: Uses hexagonal core directly (no MCP layer)
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from .container import Container
from .adapters.mcp import TOOL_SCHEMAS, MCPHandlers


def get_default_cache_dir() -> str:
    """Get default cache directory from env or use fallback"""
    return os.environ.get("CACHE_DIR", "/var/idio-mcp-cache/sec-filings")


def get_user_agent() -> str:
    """Get user agent from env or use fallback"""
    return os.environ.get("USER_AGENT", "breed research breed@idio.sh")


async def list_tools_command() -> int:
    """Show MCP tool definitions"""
    print("=" * 80)
    print("MCP TOOL DEFINITIONS")
    print("=" * 80)
    print()

    for tool_name, tool_schema in TOOL_SCHEMAS.items():
        print(f"Tool: {tool_schema['name']}")
        print(f"Claude sees: mcp__edgar-ux__{tool_schema['name']}")
        print()
        print("Description:")
        print(tool_schema['description'])
        print()
        print("Input Schema:")
        print(json.dumps(tool_schema['inputSchema'], indent=2))
        print()
        print("-" * 80)
        print()

    return 0


async def fetch_command(
    ticker: str,
    form_type: str,
    date: str | None,
    format_type: str,
    preview_lines: int,
    cache_dir: str,
) -> int:
    """Fetch SEC filing"""
    try:
        # Initialize container
        container = Container(cache_dir=cache_dir, user_agent=get_user_agent())
        handlers = MCPHandlers(container)

        # Call handler
        result = await handlers.fetch_filing(
            ticker=ticker,
            form_type=form_type,
            date=date,
            format=format_type,
            preview_lines=preview_lines
        )

        if result["success"]:
            print(f"Success: Fetched {result['metadata']['ticker']} {result['metadata']['form_type']}")
            print(f"Date: {result['metadata']['filing_date']}")
            print(f"Path: {result['path']}")
            print(f"Size: {result['metadata']['size_bytes']:,} bytes")
            print(f"Lines: {result['metadata']['total_lines']:,}")
            print()
            if result.get('preview'):
                print("Preview (first {} lines):".format(len(result['preview'])))
                print("-" * 80)
                for line in result['preview'][:20]:  # Show first 20 lines
                    print(line)
                if len(result['preview']) > 20:
                    print(f"... ({len(result['preview']) - 20} more lines)")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            return 1

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


async def search_command(
    ticker: str,
    form_type: str,
    pattern: str,
    date: str | None,
    context_lines: int,
    max_results: int,
    cache_dir: str,
) -> int:
    """Search within SEC filing"""
    try:
        # Initialize container
        container = Container(cache_dir=cache_dir, user_agent=get_user_agent())
        handlers = MCPHandlers(container)

        # Call handler
        result = await handlers.search_filing(
            ticker=ticker,
            form_type=form_type,
            pattern=pattern,
            date=date,
            context_lines=context_lines,
            max_results=max_results
        )

        if result["success"]:
            print(f"Search: {result['pattern']}")
            print(f"Filing: {result['metadata']['ticker']} {result['metadata']['form_type']} ({result['metadata']['filing_date']})")
            print(f"Matches: {result['match_count']}")
            print(f"File: {result['file_path']}")
            print()

            for i, match in enumerate(result['matches'], 1):
                print(f"Match {i} (line {match['line_number']}):")
                if match['context_before']:
                    for line in match['context_before']:
                        print(f"  {line}")
                print(f"→ {match['line']}")
                if match['context_after']:
                    for line in match['context_after']:
                        print(f"  {line}")
                print()
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            return 1

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


async def list_filings_command(
    ticker: str,
    form_type: str,
    cache_dir: str,
) -> int:
    """List available SEC filings"""
    try:
        # Initialize container
        container = Container(cache_dir=cache_dir, user_agent=get_user_agent())
        handlers = MCPHandlers(container)

        # Call handler
        result = await handlers.list_filings(ticker=ticker, form_type=form_type)

        if result["success"]:
            print(f"{result['count']} {ticker.upper()} {form_type.upper()} filings available")
            print(f"Cached: {result['cached_count']}")
            print()
            print(f"{'Date':<12} {'Cached':<8} {'Formats':<20}")
            print("-" * 80)

            for filing in result['filings'][:20]:  # Show first 20
                date = filing['filing_date']
                cached = "✓" if filing.get('cached') else ""
                formats = ", ".join(filing.get('cached', {}).keys()) if filing.get('cached') else ""
                print(f"{date:<12} {cached:<8} {formats:<20}")

            if result['count'] > 20:
                print(f"... ({result['count'] - 20} more filings)")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            return 1

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


async def list_cached_command(
    ticker: str | None,
    form_type: str | None,
    cache_dir: str,
) -> int:
    """List cached SEC filings"""
    try:
        # Initialize container
        container = Container(cache_dir=cache_dir, user_agent=get_user_agent())
        handlers = MCPHandlers(container)

        # Call handler
        result = await handlers.list_cached(ticker=ticker, form_type=form_type)

        if result["success"]:
            print(f"Cached filings: {result['count']}")
            print(f"Disk usage: {result['disk_usage_mb']:.2f} MB")
            print()
            print(f"{'Ticker':<8} {'Form':<8} {'Date':<12} {'Format':<8} {'Size':<12}")
            print("-" * 80)

            for filing in result['filings'][:50]:  # Show first 50
                ticker_str = filing['ticker']
                form = filing['form_type']
                date = filing['filing_date']
                fmt = filing['format']
                size = f"{filing['size_bytes']:,} bytes"
                print(f"{ticker_str:<8} {form:<8} {date:<12} {fmt:<8} {size:<12}")

            if result['count'] > 50:
                print(f"... ({result['count'] - 50} more filings)")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            return 1

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="edgar-ux CLI - Test MCP tools without server restart"
    )
    parser.add_argument(
        "--cache-dir",
        default=get_default_cache_dir(),
        help="Cache directory (default: $CACHE_DIR or /var/idio-mcp-cache/sec-filings)"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # list-tools command
    subparsers.add_parser("list-tools", help="Show MCP tool definitions")

    # fetch command
    fetch_parser = subparsers.add_parser("fetch", help="Fetch SEC filing")
    fetch_parser.add_argument("ticker", help="Stock ticker (e.g., TSLA)")
    fetch_parser.add_argument("form_type", help="Form type (e.g., 10-K, 10-Q)")
    fetch_parser.add_argument("--date", help="Filing date filter (YYYY-MM-DD)")
    fetch_parser.add_argument(
        "--format",
        choices=["text", "markdown", "html"],
        default="text",
        help="Output format (default: text)"
    )
    fetch_parser.add_argument(
        "--preview-lines",
        type=int,
        default=50,
        help="Number of preview lines (default: 50, 0 for none)"
    )

    # search command
    search_parser = subparsers.add_parser("search", help="Search within filing")
    search_parser.add_argument("ticker", help="Stock ticker (e.g., TSLA)")
    search_parser.add_argument("form_type", help="Form type (e.g., 10-K)")
    search_parser.add_argument("pattern", help="Search pattern (regex)")
    search_parser.add_argument("--date", help="Filing date filter (YYYY-MM-DD)")
    search_parser.add_argument("--context", type=int, default=2, help="Context lines (default: 2)")
    search_parser.add_argument("--max", type=int, default=20, help="Max results (default: 20)")

    # list-filings command
    list_filings_parser = subparsers.add_parser("list-filings", help="List available filings")
    list_filings_parser.add_argument("ticker", help="Stock ticker (e.g., TSLA)")
    list_filings_parser.add_argument("form_type", help="Form type (e.g., 10-K)")

    # list-cached command
    list_cached_parser = subparsers.add_parser("list-cached", help="List cached filings")
    list_cached_parser.add_argument("--ticker", help="Filter by ticker")
    list_cached_parser.add_argument("--form-type", help="Filter by form type")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Run command
    if args.command == "list-tools":
        return asyncio.run(list_tools_command())
    elif args.command == "fetch":
        return asyncio.run(fetch_command(
            ticker=args.ticker,
            form_type=args.form_type,
            date=args.date,
            format_type=args.format,
            preview_lines=args.preview_lines,
            cache_dir=args.cache_dir
        ))
    elif args.command == "search":
        return asyncio.run(search_command(
            ticker=args.ticker,
            form_type=args.form_type,
            pattern=args.pattern,
            date=args.date,
            context_lines=args.context,
            max_results=args.max,
            cache_dir=args.cache_dir
        ))
    elif args.command == "list-filings":
        return asyncio.run(list_filings_command(
            ticker=args.ticker,
            form_type=args.form_type,
            cache_dir=args.cache_dir
        ))
    elif args.command == "list-cached":
        return asyncio.run(list_cached_command(
            ticker=args.ticker,
            form_type=args.form_type,
            cache_dir=args.cache_dir
        ))
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
