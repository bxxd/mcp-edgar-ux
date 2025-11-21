"""
BBG Lite formatters for MCP tool results

Format handler results as Bloomberg Terminal-inspired text output.
Used by both CLI and MCP adapters for consistent presentation.
"""

from typing import Any


def format_fetch_filing(result: dict[str, Any]) -> str:
    """Format fetch_filing result as BBG Lite text.

    Example output:
        TSLA 10-K | 2025-04-30 | FETCHED (cached)

        COMPANY:     Tesla, Inc.
        FORM:        10-K
        FILED:       2025-04-30
        SIZE:        427 KB (10,234 lines)

        PATH: /var/idio-mcp-cache/sec-filings/TSLA/10-K/2025-04-30.txt

        Try: Read(path, offset=0, limit=50) | search_filing("TSLA", "10-K", "SEARCH TERM")
    """
    if not result.get("success"):
        return f"ERROR: {result.get('error', 'Unknown error')}"

    meta = result['metadata']
    lines = []

    # Header
    cached_indicator = "(cached)" if result.get('cached') else "(downloaded)"
    lines.append(f"{meta['ticker'].upper()} {meta['form_type'].upper()} | {meta['filing_date']} | FETCHED {cached_indicator}")
    lines.append("")

    # Metadata
    company = meta.get('company', 'N/A')
    lines.append(f"COMPANY:     {company}")
    lines.append(f"FORM:        {meta['form_type']}")
    lines.append(f"FILED:       {meta['filing_date']}")

    size_kb = meta['size_bytes'] / 1024
    size_str = f"{size_kb:.0f} KB"
    if meta.get('total_lines'):
        size_str += f" ({meta['total_lines']:,} lines)"
    lines.append(f"SIZE:        {size_str}")
    lines.append("")

    # Path
    lines.append(f"PATH: {result['path']}")

    # Affordances
    lines.append("")
    lines.append(f'Try: Read(path, offset=0, limit=50) | search_filing("{meta["ticker"]}", "{meta["form_type"]}", "SEARCH TERM")')

    return "\n".join(lines)


def format_search_filing(result: dict[str, Any]) -> str:
    """Format search_filing result as BBG Lite text.

    Example output:
        TSLA 10-K | 2025-04-30 | SEARCH "supply chain"

        MATCHES (12 found | 10,234 lines)
        ──────────────────────────────────────────────────────────────────────
          1234: matching line with supply chain
          1235: context after

          2456: another matching line
          2457: more context

        PATH: /var/idio-mcp-cache/sec-filings/TSLA/10-K/2025-04-30.txt
        Try: Read(path, offset=LINE, limit=50) | search_filing(..., pattern="OTHER")
    """
    if not result.get("success"):
        return f"ERROR: {result.get('error', 'Unknown error')}"

    meta = result['metadata']
    pattern = result['pattern']
    match_count = result['match_count']
    file_path = result['file_path']
    offset = result.get('offset', 0)
    max_results = result.get('max_results', 20)

    # No matches
    if match_count == 0:
        return f"""{meta['ticker'].upper()} {meta['form_type'].upper()} | {meta['filing_date']} | SEARCH "{pattern}"

NO MATCHES FOUND

PATH: {file_path}
Try: Different search term | Read(path) for full filing
"""

    lines = []

    # Header with filename
    filename = file_path.split('/')[-1] if '/' in file_path else file_path
    lines.append(f"{meta['ticker'].upper()} {meta['form_type'].upper()} | {meta['filing_date']} | SEARCH \"{pattern}\"")
    lines.append(f"FILE: {filename}")
    lines.append("")

    # Summary with correct range
    returned = len(result['matches'])
    start_idx = offset + 1
    end_idx = offset + returned

    if match_count > returned:
        if offset == 0:
            range_str = f" (showing first {returned})"
        else:
            range_str = f" (showing {start_idx}-{end_idx})"
    else:
        range_str = ""
    lines.append(f"MATCHES ({match_count} found{range_str})")
    lines.append("─" * 70)

    # Format each match with line numbers
    for i, match in enumerate(result['matches'], 1):
        if i > 1:
            lines.append("")  # Blank line between matches

        line_num = match['line_number']
        context_before = match.get('context_before', [])
        context_after = match.get('context_after', [])

        # Context before (with calculated line numbers)
        for j, ctx_line in enumerate(context_before):
            ctx_line_num = line_num - len(context_before) + j
            lines.append(f"  {ctx_line_num:>4}: {ctx_line}")

        # Matching line
        lines.append(f"  {line_num:>4}: {match['line']}")

        # Context after (with calculated line numbers)
        for j, ctx_line in enumerate(context_after, 1):
            ctx_line_num = line_num + j
            lines.append(f"  {ctx_line_num:>4}: {ctx_line}")

    lines.append("")
    lines.append(f"PATH: {file_path}")

    # Navigation hints
    if match_count > returned:
        lines.append(f'More: search_filing(..., max_results={match_count}) | Read(path, offset=LINE, limit=50)')
    else:
        lines.append(f'Try: Read(path, offset=LINE, limit=50) | search_filing(..., pattern="OTHER")')

    return "\n".join(lines)


def format_list_filings(result: dict[str, Any]) -> str:
    """Format list_filings result as BBG Lite text.

    Example output:
        TSLA 10-K FILINGS AVAILABLE
        ────────────────────────────────────────────────────────────────
        83 filings available (2 cached)

        Date         Location (if cached)
        ────────────────────────────────────────────────────────────────
        2025-11-19   (not cached - will download on demand)
        2025-08-27   /var/idio-mcp-cache/sec-filings/TSLA/10-K/2025-08-27.txt
        2025-04-30   /var/idio-mcp-cache/sec-filings/TSLA/10-K/2025-04-30.txt
        2024-01-29   (not cached - will download on demand)
        ...

        ────────────────────────────────────────────────────────────────
        Showing 15 of 83 filings (2 cached)

        Try: fetch_filing(ticker, form, date) | search_filing(ticker, form, pattern)
             Read(path) to read cached filing directly
    """
    if not result.get("success"):
        return f"ERROR: {result.get('error', 'Unknown error')}"

    lines = []

    # Extract ticker/form from first filing (if available)
    ticker = result['filings'][0]['ticker'].upper() if result['filings'] else "FILINGS"
    form_type = result['filings'][0]['form_type'].upper() if result['filings'] else ""

    # Get pagination parameters
    start = result.get('start', 0)
    max_results = result.get('max', 15)
    total_count = result['count']

    # Calculate pagination
    end = min(start + max_results, total_count)
    filings_to_show = result['filings'][start:end]

    # Header
    lines.append(f"{ticker} {form_type} FILINGS AVAILABLE")
    lines.append("─" * 70)
    lines.append(f"FILED       LOCATION (if cached)")
    lines.append("─" * 70)

    # Table rows (paginated)
    for filing in filings_to_show:
        date = filing['filing_date'][:10].ljust(10)
        cached_info = filing.get('cached', {})

        if cached_info and isinstance(cached_info, dict):
            # Get first available format path (prefer txt, then md, then any)
            path = None
            for fmt in ['txt', 'md']:
                if fmt in cached_info:
                    fmt_data = cached_info[fmt]
                    if isinstance(fmt_data, dict) and 'path' in fmt_data:
                        path = fmt_data['path']
                        break

            # If no txt/md, get first available format
            if not path:
                for fmt_data in cached_info.values():
                    if isinstance(fmt_data, dict) and 'path' in fmt_data:
                        path = fmt_data['path']
                        break

            if path:
                lines.append(f"{date}  {path}")
            else:
                lines.append(f"{date}  (not cached - will download on demand)")
        else:
            lines.append(f"{date}  (not cached - will download on demand)")

    # Footer
    lines.append("")
    lines.append(f"Showing {start + 1}-{start + len(filings_to_show)} of {total_count} filings ({result['cached_count']} cached)")
    lines.append("")
    lines.append(f"Try: fetch_filing(ticker, form, date) | search_filing(ticker, form, pattern)")
    lines.append(f"     Read(path) to read cached filing directly")

    return "\n".join(lines)


def format_list_cached(result: dict[str, Any]) -> str:
    """Format list_cached result as BBG Lite text.

    Example output:
        CACHED SEC FILINGS
        ────────────────────────────────────────────────────────────────
        3 filings cached (1.2 MB total)

        Ticker   Form     Date         Format   Size
        ────────────────────────────────────────────────────────────────
        TSLA     10-K     2025-04-30   txt      427,000 bytes
        TSLA     10-K     2025-04-30   md       523,400 bytes
        NVDA     10-Q     2025-08-27   txt      313,200 bytes

        ────────────────────────────────────────────────────────────────
        Cache directory: /var/idio-mcp-cache/sec-filings
    """
    if not result.get("success"):
        return f"ERROR: {result.get('error', 'Unknown error')}"

    lines = []

    # Header
    lines.append("CACHED SEC FILINGS")
    lines.append("─" * 68)
    lines.append(f"{result['count']} filings cached ({result['disk_usage_mb']:.2f} MB total)")

    if result['count'] == 0:
        lines.append("")
        lines.append("No filings cached yet")
        return "\n".join(lines)

    lines.append("")

    # Table header
    lines.append(f"{'Ticker':<8} {'Form':<8} {'Date':<12} {'Format':<8} {'Size':<15}")
    lines.append("─" * 68)

    # Table rows (first 50)
    for filing in result['filings'][:50]:
        ticker = filing['ticker']
        form = filing['form_type']
        date = filing['filing_date']
        fmt = filing['format']
        size = f"{filing['size_bytes']:,} bytes"
        lines.append(f"{ticker:<8} {form:<8} {date:<12} {fmt:<8} {size:<15}")

    # Show remaining count
    if result['count'] > 50:
        lines.append("")
        lines.append(f"... {result['count'] - 50} more cached filings")

    # Footer
    lines.append("")
    lines.append("─" * 68)
    lines.append(f"Cache directory: {result.get('cache_dir', 'Unknown')}")

    return "\n".join(lines)
