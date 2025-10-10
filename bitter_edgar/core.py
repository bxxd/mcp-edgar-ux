"""
bitter-edgar core logic

Pure functions for fetching, caching, and converting SEC filings.
No MCP delivery concerns - just the business logic.
"""
import os
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

    def fetch_latest(self, ticker: str, form_type: str) -> Dict[str, Any]:
        """Fetch latest filing metadata (no content download)."""
        company = self.get_company(ticker)
        filings = company.get_filings(form=form_type)

        if not filings:
            raise ValueError(f"No {form_type} filings found for {ticker}")

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

    def download_content(self, filing, format: str = "markdown") -> str:
        """Download filing content in specified format."""
        if format == "html":
            return filing.html()
        elif format == "markdown":
            try:
                from markdownify import markdownify as md
                html_content = filing.html()
                return md(html_content, heading_style="ATX")
            except ImportError:
                # Fallback to text if markdown lib not available
                return filing.text()
        else:  # text
            return filing.text()


def fetch_filing(
    ticker: str,
    form_type: str,
    cache_dir: str = "/tmp/sec-filings",
    format: str = "markdown",
    user_agent: str = "breed research breed@idio.sh"
) -> Dict[str, Any]:
    """
    Fetch SEC filing and save to cache.

    Pure function - no global state.

    Args:
        ticker: Stock ticker (e.g., "TSLA", "AAPL")
        form_type: Form type ("10-K", "10-Q", "8-K", etc.)
        cache_dir: Cache directory path
        format: Output format - "markdown", "text", or "html"
        user_agent: SEC User-Agent identity

    Returns:
        Dict with file path and metadata
    """
    cache = FilingCache(cache_dir)
    fetcher = EdgarFetcher(user_agent)

    # Fetch metadata
    metadata = fetcher.fetch_latest(ticker, form_type)
    filing_date = metadata["filing_date"]

    # Check if cached
    if cache.is_cached(ticker, form_type, filing_date, format):
        path = cache.get_path(ticker, form_type, filing_date, format)
        return {
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

    # Download content
    content = fetcher.download_content(metadata["filing"], format)

    # Save to cache
    path = cache.save(ticker, form_type, filing_date, content, format)

    return {
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
        "format": format,
        "sec_url": metadata["sec_url"],
        "message": f"Downloaded {metadata['form_type']} filing. Use Read tool to view: Read('{path}')"
    }


def list_cached_filings(
    cache_dir: str = "/tmp/sec-filings",
    ticker: Optional[str] = None,
    form_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    List cached SEC filings.

    Pure function - no global state.

    Args:
        cache_dir: Cache directory path
        ticker: Optional ticker filter
        form_type: Optional form type filter

    Returns:
        Dict with list of cached filings
    """
    cache = FilingCache(cache_dir)
    filings = cache.list_cached(ticker, form_type)
    disk_usage = cache.get_disk_usage()

    return {
        "success": True,
        "filings": filings,
        "count": len(filings),
        "disk_usage_mb": round(disk_usage / 1024 / 1024, 2)
    }
