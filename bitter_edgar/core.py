"""
bitter-edgar core logic

Pure async functions for fetching, caching, and converting SEC filings.
No MCP delivery concerns - just the business logic.
"""
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from edgar import Company, set_identity


class FilingCache:
    """Manages SEC filing cache on disk."""

    def __init__(self, cache_dir: str = "/tmp/sec-filings"):
        self.cache_dir = Path(cache_dir)

    def ensure_dir(self, ticker: str, form_type: str) -> Path:
        """Ensure cache directory exists for ticker/form."""
        path = self.cache_dir / ticker.upper() / form_type.upper()
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_path(self, ticker: str, form_type: str, filing_date: str, format: str = "markdown") -> Path:
        """Get path for cached filing."""
        ext = {"markdown": ".md", "text": ".txt", "html": ".html"}[format]
        cache_dir = self.ensure_dir(ticker, form_type)
        return cache_dir / f"{filing_date}{ext}"

    def is_cached(self, ticker: str, form_type: str, filing_date: str, format: str = "markdown") -> bool:
        """Check if filing is already cached."""
        path = self.get_path(ticker, form_type, filing_date, format)
        return path.exists()

    def save(self, ticker: str, form_type: str, filing_date: str, content: str, format: str = "markdown") -> Path:
        """Save filing content to cache."""
        path = self.get_path(ticker, form_type, filing_date, format)
        path.write_text(content, encoding='utf-8')
        return path

    def list_cached(self, ticker: Optional[str] = None, form_type: Optional[str] = None) -> list[Dict[str, Any]]:
        """List all cached filings."""
        if not self.cache_dir.exists():
            return []

        filings = []
        for ticker_dir in self.cache_dir.iterdir():
            if not ticker_dir.is_dir():
                continue
            if ticker and ticker_dir.name.upper() != ticker.upper():
                continue

            for form_dir in ticker_dir.iterdir():
                if not form_dir.is_dir():
                    continue
                if form_type and form_dir.name.upper() != form_type.upper():
                    continue

                for file_path in form_dir.iterdir():
                    if file_path.is_file() and file_path.suffix in ['.md', '.txt', '.html']:
                        stat = file_path.stat()
                        filings.append({
                            "ticker": ticker_dir.name,
                            "form_type": form_dir.name,
                            "filing_date": file_path.stem,
                            "path": str(file_path),
                            "size_bytes": stat.st_size,
                            "format": file_path.suffix[1:]
                        })

        # Sort by date descending
        filings.sort(key=lambda x: x["filing_date"], reverse=True)
        return filings

    def get_disk_usage(self) -> int:
        """Get total disk usage in bytes."""
        if not self.cache_dir.exists():
            return 0

        total = 0
        for ticker_dir in self.cache_dir.iterdir():
            if not ticker_dir.is_dir():
                continue
            for form_dir in ticker_dir.iterdir():
                if not form_dir.is_dir():
                    continue
                for file_path in form_dir.iterdir():
                    if file_path.is_file():
                        total += file_path.stat().st_size
        return total


class EdgarFetcher:
    """Fetches SEC filings from EDGAR."""

    def __init__(self, user_agent: str = "breed research breed@idio.sh"):
        set_identity(user_agent)

    def get_company(self, identifier: str) -> Company:
        """Get company by ticker or CIK."""
        return Company(identifier)

    def list_available(self, ticker: str, form_type: str) -> list[Dict[str, Any]]:
        """
        List all available filings from SEC (no content download).

        Args:
            ticker: Stock ticker
            form_type: Form type (e.g., "10-K")

        Returns:
            List of filing metadata dicts (sorted by date descending)
        """
        company = self.get_company(ticker)
        filings = company.get_filings(form=form_type)

        if not filings:
            return []

        result = []
        for filing in filings:
            # Format filing date
            filing_date = filing.filing_date
            if hasattr(filing_date, 'strftime'):
                date_str = filing_date.strftime('%Y-%m-%d')
            elif hasattr(filing_date, 'date'):
                date_str = filing_date.date().strftime('%Y-%m-%d')
            else:
                date_str = str(filing_date)

            result.append({
                "ticker": ticker.upper(),
                "form_type": filing.form,
                "filing_date": date_str,
                "accession_number": filing.accession_number,
                "sec_url": filing.url
            })

        # Sort by date descending (most recent first)
        result.sort(key=lambda x: x["filing_date"], reverse=True)
        return result

    def fetch_latest(self, ticker: str, form_type: str, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch filing metadata (no content download).

        Args:
            ticker: Stock ticker
            form_type: Form type (e.g., "10-K")
            date: Optional date filter (YYYY-MM-DD). Returns filing closest >= date.

        Returns:
            Dict with filing metadata
        """
        company = self.get_company(ticker)
        filings = company.get_filings(form=form_type)

        if not filings:
            raise ValueError(f"No {form_type} filings found for {ticker}")

        # Filter by date if specified
        if date:
            target_date = datetime.strptime(date, '%Y-%m-%d').date()
            filtered = []
            for filing in filings:
                filing_date = filing.filing_date
                if hasattr(filing_date, 'date'):
                    filing_date = filing_date.date()
                elif isinstance(filing_date, str):
                    filing_date = datetime.strptime(filing_date, '%Y-%m-%d').date()

                # Include filings >= target date
                if filing_date >= target_date:
                    filtered.append((filing, filing_date))

            if not filtered:
                raise ValueError(f"No {form_type} filings found for {ticker} on or after {date}")

            # Sort by date ascending, get closest
            filtered.sort(key=lambda x: x[1])
            filing = filtered[0][0]
        else:
            # No date filter - get most recent
            filing = list(filings)[0]

        # Format filing date
        filing_date = filing.filing_date
        if hasattr(filing_date, 'strftime'):
            date_str = filing_date.strftime('%Y-%m-%d')
        else:
            date_str = str(filing_date)

        return {
            "filing": filing,
            "company": company.name,
            "ticker": ticker.upper(),
            "cik": filing.cik,
            "form_type": filing.form,
            "filing_date": date_str,
            "accession_number": filing.accession_number,
            "sec_url": filing.url
        }

    def download_content(self, filing, format: str = "markdown") -> tuple[str, str]:
        """
        Download filing content in specified format.

        Returns:
            Tuple of (content, actual_format) - format may differ if fallback occurs
        """
        if format == "html":
            return filing.html(), "html"
        elif format == "markdown":
            # Markdown is just cleaned HTML rendered with markdownify
            # BeautifulSoup handles XBRL/XML stripping
            try:
                from markdownify import markdownify as md
                from bs4 import BeautifulSoup

                html_content = filing.html()
                soup = BeautifulSoup(html_content, 'lxml')

                # Remove all XBRL/iXBRL tags (tags with namespace prefix like ix:, us-gaap:, etc)
                # These are hidden metadata inside <body>
                for tag in soup.find_all():
                    if ':' in tag.name:
                        tag.decompose()

                # Get body
                body = soup.find('body')
                if body:
                    return md(str(body), heading_style="ATX"), "markdown"
                else:
                    # Fallback to edgartools text() if no body
                    return filing.text(), "text"
            except ImportError:
                # Fallback to text if libs not available
                return filing.text(), "text"
        else:  # text
            return filing.text(), "text"


def _read_preview(path: Path, num_lines: int) -> tuple[list[str], int]:
    """
    Read first N lines from file with line numbers.

    Returns:
        Tuple of (preview_lines, total_lines)
    """
    preview = []
    total = 0

    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f, 1):
                total = i
                if i <= num_lines:
                    # Format with line number (like Read tool)
                    preview.append(f"{i:6}→{line.rstrip()}")

        return preview, total
    except Exception:
        return [], 0


async def fetch_filing(
    ticker: str,
    form_type: str,
    cache_dir: str = "/tmp/sec-filings",
    date: Optional[str] = None,
    format: str = "text",
    preview_lines: int = 50,
    user_agent: str = "breed research breed@idio.sh"
) -> Dict[str, Any]:
    """
    Fetch SEC filing and save to cache (async).

    Pure function - no global state.

    The Bitter Lesson: Use text format (scales), not markdown (clever but brittle).

    Args:
        ticker: Stock ticker (e.g., "TSLA", "AAPL")
        form_type: Form type ("10-K", "10-Q", "8-K", etc.)
        cache_dir: Cache directory path
        date: Optional date filter (YYYY-MM-DD). Returns filing closest >= date.
        format: Output format - "text" (default), "markdown", or "html"
        preview_lines: Number of lines to include in preview (default: 50, 0 to disable)
        user_agent: SEC User-Agent identity

    Returns:
        Dict with file path, metadata, and optional preview
    """
    cache = FilingCache(cache_dir)
    fetcher = EdgarFetcher(user_agent)

    # Fetch metadata (edgartools is sync, run in thread pool)
    metadata = await asyncio.to_thread(fetcher.fetch_latest, ticker, form_type, date)
    filing_date = metadata["filing_date"]

    # Check if cached
    if cache.is_cached(ticker, form_type, filing_date, format):
        path = cache.get_path(ticker, form_type, filing_date, format)

        # Read preview if requested (async file I/O)
        preview = []
        total_lines = None
        if preview_lines > 0:
            preview, total_lines = await asyncio.to_thread(_read_preview, path, preview_lines)

        result = {
            "success": True,
            "cached": True,
            "path": str(path),
            "company": metadata["company"],
            "ticker": metadata["ticker"],
            "cik": metadata["cik"],
            "form_type": metadata["form_type"],
            "filing_date": filing_date,
            "accession_number": metadata["accession_number"],
            "size_bytes": path.stat().st_size,
            "format": format,
            "sec_url": metadata["sec_url"],
            "message": "Already cached. Use Read tool to view."
        }

        if preview:
            result["preview"] = preview
            result["total_lines"] = total_lines

        return result

    # Download content (may fallback to different format) - run in thread pool
    content, actual_format = await asyncio.to_thread(
        fetcher.download_content, metadata["filing"], format
    )

    # Save to cache - run in thread pool (file I/O)
    path = await asyncio.to_thread(cache.save, ticker, form_type, filing_date, content, actual_format)

    # Read preview if requested (async file I/O)
    preview = []
    total_lines = None
    if preview_lines > 0:
        preview, total_lines = await asyncio.to_thread(_read_preview, path, preview_lines)

    result = {
        "success": True,
        "cached": False,
        "path": str(path),
        "company": metadata["company"],
        "ticker": metadata["ticker"],
        "cik": metadata["cik"],
        "form_type": metadata["form_type"],
        "filing_date": filing_date,
        "accession_number": metadata["accession_number"],
        "size_bytes": path.stat().st_size,
        "format": actual_format,
        "sec_url": metadata["sec_url"],
        "message": f"Downloaded {metadata['form_type']} filing. Use Read tool to view: Read('{path}')"
    }

    if preview:
        result["preview"] = preview
        result["total_lines"] = total_lines

    return result


async def list_cached_filings(
    cache_dir: str = "/tmp/sec-filings",
    ticker: Optional[str] = None,
    form_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    List cached SEC filings (async).

    Pure function - no global state.

    Args:
        cache_dir: Cache directory path
        ticker: Optional ticker filter
        form_type: Optional form type filter

    Returns:
        Dict with list of cached filings
    """
    cache = FilingCache(cache_dir)

    # Run file I/O in thread pool
    filings = await asyncio.to_thread(cache.list_cached, ticker, form_type)
    disk_usage = await asyncio.to_thread(cache.get_disk_usage)

    return {
        "success": True,
        "filings": filings,
        "count": len(filings),
        "disk_usage_mb": round(disk_usage / 1024 / 1024, 2)
    }


async def list_filings(
    ticker: str,
    form_type: str,
    cache_dir: str = "/tmp/sec-filings",
    user_agent: str = "breed research breed@idio.sh"
) -> Dict[str, Any]:
    """
    List all filings for ticker/form (both cached + available from SEC) - async.

    Shows which filings are cached locally vs. available for download.

    Args:
        ticker: Stock ticker
        form_type: Form type (e.g., "10-K", "10-Q")
        cache_dir: Cache directory path
        user_agent: SEC User-Agent identity

    Returns:
        Dict with combined list of filings (cached + available)
    """
    cache = FilingCache(cache_dir)
    fetcher = EdgarFetcher(user_agent)

    # Get cached filings (async file I/O)
    cached_filings = await asyncio.to_thread(cache.list_cached, ticker, form_type)

    # Build map of cached dates by format
    cached_by_date = {}
    for filing in cached_filings:
        date = filing["filing_date"]
        fmt = filing["format"]
        if date not in cached_by_date:
            cached_by_date[date] = {}
        cached_by_date[date][fmt] = filing

    # Get available filings from SEC (async network I/O)
    try:
        available_filings = await asyncio.to_thread(fetcher.list_available, ticker, form_type)
    except Exception as e:
        # If SEC query fails, just show cached
        return {
            "success": True,
            "filings": cached_filings,
            "count": len(cached_filings),
            "cached_count": len(cached_filings),
            "available_count": 0,
            "error": f"Could not query SEC: {str(e)}"
        }

    # Merge: add cached flag and paths to available filings
    merged = []
    for available in available_filings:
        date = available["filing_date"]

        # Check if cached in any format
        cached_formats = cached_by_date.get(date, {})

        merged.append({
            **available,
            "cached": len(cached_formats) > 0,
            "cached_formats": list(cached_formats.keys()),
            "paths": {fmt: filing["path"] for fmt, filing in cached_formats.items()},
            "size_bytes": cached_formats.get("text", cached_formats.get("markdown", {})).get("size_bytes") if cached_formats else None
        })

    return {
        "success": True,
        "filings": merged,
        "count": len(merged),
        "cached_count": len([f for f in merged if f["cached"]]),
        "available_count": len(merged),
        "ticker": ticker.upper(),
        "form_type": form_type
    }


async def search_filing(
    ticker: str,
    form_type: str,
    pattern: str,
    cache_dir: str = "/tmp/sec-filings",
    date: Optional[str] = None,
    context_lines: int = 2,
    max_results: int = 20,
    case_sensitive: bool = False
) -> Dict[str, Any]:
    """
    Search for pattern in filing (like grep with line numbers) - async.

    Auto-fetches filing if not cached. Returns matches with context.

    Args:
        ticker: Stock ticker
        form_type: Form type
        pattern: Search pattern (regex supported)
        cache_dir: Cache directory path
        date: Optional date filter (YYYY-MM-DD)
        context_lines: Lines of context before/after match
        max_results: Maximum number of matches to return
        case_sensitive: Case-sensitive search (default: False)

    Returns:
        Dict with matches, line numbers, and metadata
    """
    import subprocess
    import re

    # Fetch filing if needed (will use cache if available) - async
    filing_result = await fetch_filing(ticker, form_type, cache_dir, date, format="text")

    if not filing_result["success"]:
        return {
            "success": False,
            "error": filing_result.get("error", "Failed to fetch filing")
        }

    file_path = filing_result["path"]

    # Use grep to search with line numbers and context
    # -n: line numbers
    # -C: context lines (before and after)
    # -i: case insensitive (default)
    grep_args = ["grep", "-n", f"-C{context_lines}"]
    if not case_sensitive:
        grep_args.append("-i")

    grep_args.extend([pattern, file_path])

    try:
        # Run grep in thread pool (blocking subprocess)
        result = await asyncio.to_thread(
            subprocess.run,
            grep_args,
            capture_output=True,
            text=True,
            timeout=30
        )

        # grep returns 1 if no matches (not an error)
        if result.returncode == 1:
            return {
                "success": True,
                "matches": [],
                "match_count": 0,
                "file_path": file_path,
                "pattern": pattern,
                "ticker": ticker,
                "form_type": form_type,
                "filing_date": filing_result["filing_date"],
                "message": "No matches found"
            }

        if result.returncode != 0:
            return {
                "success": False,
                "error": f"grep failed: {result.stderr}"
            }

        # Parse grep output
        lines = result.stdout.strip().split('\n')

        # Group matches (grep separates groups with --)
        matches = []
        current_match = []

        for line in lines:
            if line == '--':
                if current_match:
                    matches.append(current_match)
                    current_match = []
            else:
                current_match.append(line)

        if current_match:
            matches.append(current_match)

        # Limit results
        if len(matches) > max_results:
            matches = matches[:max_results]
            truncated = True
        else:
            truncated = False

        # Count total line count for context - run file I/O in thread pool
        def count_lines(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return sum(1 for _ in f)
            except Exception:
                return None

        total_lines = await asyncio.to_thread(count_lines, file_path)

        return {
            "success": True,
            "matches": matches,
            "match_count": len(result.stdout.strip().split('\n--\n')),
            "returned_matches": len(matches),
            "truncated": truncated,
            "file_path": file_path,
            "total_lines": total_lines,
            "pattern": pattern,
            "ticker": ticker.upper(),
            "form_type": form_type,
            "filing_date": filing_result["filing_date"],
            "context_lines": context_lines
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Search timed out (filing too large or pattern too complex)"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Search failed: {str(e)}"
        }
