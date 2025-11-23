#!/usr/bin/env python3
"""
CLI for edgar-ux MCP - test tools without MCP restart

Usage:
  ./cli list-tools                        # Show MCP tool definitions
  ./cli fetch TSLA 10-K                   # Fetch filing (uses env CACHE_DIR or /tmp/sec-filings)
  ./cli fetch TSLA 10-K --date 2024-01-01 # Fetch specific date
  ./cli fetch TSLA 10-K --format markdown # Fetch as markdown
  ./cli search TSLA 10-K "supply chain"   # Search within filing
  ./cli list-filings 10-K                 # List latest 10-K filings across all companies
  ./cli list-filings 10-K --ticker TSLA   # List available TSLA 10-K filings
  ./cli financials TSLA                   # Get TSLA financial statements (all statements)
  ./cli financials TSLA --type income     # Get income statement only

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
from .formatters import (
    format_fetch_filing,
    format_search_filing,
    format_list_filings,
    format_financial_statements,
)


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

        # Use BBG Lite formatter
        print(format_fetch_filing(result))

        if not result["success"]:
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

        # Use BBG Lite formatter
        print(format_search_filing(result))

        if not result["success"]:
            return 1

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


async def list_filings_command(
    ticker: str | None,
    form_type: str,
    cache_dir: str,
) -> int:
    """List available SEC filings

    If ticker is None, lists latest filings across all companies.
    """
    try:
        # Initialize container
        container = Container(cache_dir=cache_dir, user_agent=get_user_agent())
        handlers = MCPHandlers(container)

        # Call handler
        result = await handlers.list_filings(ticker=ticker, form_type=form_type)

        # Use BBG Lite formatter
        print(format_list_filings(result))

        if not result["success"]:
            return 1

        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


async def financials_command(
    ticker: str,
    statement_type: str,
    cache_dir: str,
) -> int:
    """Get financial statements"""
    try:
        # Initialize container
        container = Container(cache_dir=cache_dir, user_agent=get_user_agent())
        handlers = MCPHandlers(container)

        # Call handler
        result = await handlers.get_financial_statements(
            ticker=ticker,
            statement_type=statement_type
        )

        # Use BBG Lite formatter
        print(format_financial_statements(result))

        if not result["success"]:
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
    list_filings_parser.add_argument("form_type", help="Form type (e.g., 10-K)")
    list_filings_parser.add_argument("--ticker", help="Optional stock ticker (e.g., TSLA). Omit to see latest filings across all companies.")

    # financials command
    financials_parser = subparsers.add_parser("financials", help="Get financial statements")
    financials_parser.add_argument("ticker", help="Stock ticker (e.g., TSLA)")
    financials_parser.add_argument("--type", dest="statement_type", default="all",
                                    choices=["all", "income", "balance", "cash_flow"],
                                    help="Statement type (default: all)")

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
    elif args.command == "financials":
        return asyncio.run(financials_command(
            ticker=args.ticker,
            statement_type=args.statement_type,
            cache_dir=args.cache_dir
        ))
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
