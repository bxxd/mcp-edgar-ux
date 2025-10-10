"""
bitter-edgar MCP Server

Scale beats cleverness. Returns file paths, not content.
"""
import argparse
import logging
import os
from pathlib import Path
from typing import Optional
from mcp.server.fastmcp import FastMCP
from edgar import Company, set_identity

# Suppress INFO logs
logging.getLogger("edgar").setLevel(logging.WARNING)

# Set SEC User-Agent (required by SEC EDGAR API)
set_identity("breed research breed@idio.sh")

# Default cache directory (can be overridden via env var)
CACHE_DIR = Path(os.getenv("BITTER_EDGAR_CACHE_DIR", "/tmp/sec-filings"))

# Initialize MCP server
mcp = FastMCP("bitter-edgar")


def get_company(identifier: str) -> Company:
    """Get company by ticker or CIK."""
    return Company(identifier)


def ensure_cache_dir(ticker: str, form_type: str) -> Path:
    """Ensure cache directory exists for ticker/form."""
    path = CACHE_DIR / ticker.upper() / form_type.upper()
    path.mkdir(parents=True, exist_ok=True)
    return path


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
        # Get company and filings
        company = get_company(ticker)
        filings = company.get_filings(form=form_type)

        if not filings:
            return {
                "success": False,
                "error": f"No {form_type} filings found for {ticker}"
            }

        # Get the first (most recent) filing
        filing = list(filings)[0]

        # Ensure cache directory exists
        cache_dir = ensure_cache_dir(ticker, form_type)

        # Generate filename from filing date
        filing_date = filing.filing_date
        if hasattr(filing_date, 'strftime'):
            date_str = filing_date.strftime('%Y-%m-%d')
        else:
            date_str = str(filing_date)

        # Choose file extension based on format
        ext = {"markdown": ".md", "text": ".txt", "html": ".html"}[format]
        file_path = cache_dir / f"{date_str}{ext}"

        # Check if already cached
        if file_path.exists():
            return {
                "success": True,
                "cached": True,
                "path": str(file_path),
                "company": company.name,
                "ticker": ticker.upper(),
                "cik": filing.cik,
                "form_type": filing.form,
                "filing_date": date_str,
                "accession_number": filing.accession_number,
                "size_bytes": file_path.stat().st_size,
                "format": format,
                "sec_url": filing.url,
                "message": "Already cached. Use Read tool to view."
            }

        # Download and convert content
        if format == "html":
            content = filing.html()
        elif format == "markdown":
            # Convert HTML to markdown
            try:
                from markdownify import markdownify as md
                html_content = filing.html()
                content = md(html_content, heading_style="ATX")
            except ImportError:
                # Fallback to text if markdown lib not available
                content = filing.text()
                format = "text"
                ext = ".txt"
                file_path = cache_dir / f"{date_str}{ext}"
        else:
            content = filing.text()

        # Save to disk
        file_path.write_text(content, encoding='utf-8')

        return {
            "success": True,
            "cached": False,
            "path": str(file_path),
            "company": company.name,
            "ticker": ticker.upper(),
            "cik": filing.cik,
            "form_type": filing.form,
            "filing_date": date_str,
            "accession_number": filing.accession_number,
            "size_bytes": file_path.stat().st_size,
            "format": format,
            "sec_url": filing.url,
            "message": f"Downloaded {filing.form} filing. Use Read tool to view: Read('{file_path}')"
        }

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
        if not CACHE_DIR.exists():
            return {
                "success": True,
                "filings": [],
                "count": 0,
                "disk_usage_mb": 0
            }

        filings = []
        total_size = 0

        # Walk cache directory
        for ticker_dir in CACHE_DIR.iterdir():
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
                        total_size += stat.st_size

                        filings.append({
                            "ticker": ticker_dir.name,
                            "form_type": form_dir.name,
                            "filing_date": file_path.stem,
                            "path": str(file_path),
                            "size_bytes": stat.st_size,
                            "format": file_path.suffix[1:]  # Remove leading dot
                        })

        # Sort by date descending
        filings.sort(key=lambda x: x["filing_date"], reverse=True)

        return {
            "success": True,
            "filings": filings,
            "count": len(filings),
            "disk_usage_mb": round(total_size / 1024 / 1024, 2)
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to list cached filings: {str(e)}"
        }


def main():
    """Main entry point for the MCP server."""
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
        global CACHE_DIR
        CACHE_DIR = Path(args.cache_dir)

    # Run the server
    if args.transport == "streamable-http":
        print(f"Starting bitter-edgar on http://{args.host}:{args.port}")
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
