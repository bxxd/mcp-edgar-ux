"""
MCP Tool Handlers

Shared handlers for MCP tools that use the hexagonal core.
"""
import asyncio
from typing import Any, Optional

from ...container import Container


class MCPHandlers:
    """Handlers for MCP tools using dependency injection"""

    def __init__(self, container: Container):
        self.container = container

    async def fetch_filing(
        self,
        ticker: str,
        form_type: str,
        date: Optional[str] = None,
        format: str = "text",
        preview_lines: int = 50
    ) -> dict[str, Any]:
        """Fetch filing and return path + preview + metadata"""
        try:
            # Get list of cached filings to check if this one exists
            cached_filings = await asyncio.to_thread(
                self.container.cache.list_all,
                ticker=ticker,
                form_type=form_type
            )
            # Normalize format names: cache uses extensions (txt, md, html), API uses full names
            format_map = {"text": "txt", "markdown": "md", "html": "html"}
            normalized_format = format_map.get(format, format)
            cached_dates = {(c.filing_date, c.format) for c in cached_filings}

            # Fetch the filing (may use cache or download)
            filing_content = await asyncio.to_thread(
                self.container.fetch_filing.execute,
                ticker=ticker,
                form_type=form_type,
                date=date,
                format=format,
                include_exhibits=True,
                preview_lines=preview_lines
            )

            # Check if this filing was already cached before we called the service
            was_cached = (filing_content.filing.filing_date, normalized_format) in cached_dates

            # Generate preview if requested
            if preview_lines > 0:
                preview, total_lines = await asyncio.to_thread(
                    self.container.searcher.read_preview,
                    filing_content.path,
                    preview_lines
                )
            else:
                preview = []
                total_lines = filing_content.total_lines

            return {
                "success": True,
                "path": str(filing_content.path),
                "cached": was_cached,
                "preview": preview,
                "metadata": {
                    "company": filing_content.filing.company_name,
                    "ticker": filing_content.filing.ticker,
                    "form_type": filing_content.filing.form_type,
                    "filing_date": filing_content.filing.filing_date,
                    "accession_number": filing_content.filing.accession_number,
                    "sec_url": filing_content.filing.sec_url,
                    "format": filing_content.format,
                    "size_bytes": filing_content.size_bytes,
                    "total_lines": total_lines,
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to fetch filing: {str(e)}"
            }

    async def search_filing(
        self,
        ticker: str,
        form_type: str,
        pattern: str,
        date: Optional[str] = None,
        format: str = "text",
        context_lines: int = 2,
        max_results: int = 20,
        offset: int = 0
    ) -> dict[str, Any]:
        """Search for pattern in filing"""
        try:
            # Use service from container
            result = await asyncio.to_thread(
                self.container.search_filing.execute,
                ticker=ticker,
                form_type=form_type,
                pattern=pattern,
                date=date,
                format=format,
                context_lines=context_lines,
                max_results=max_results,
                offset=offset
            )

            # Format matches for output
            formatted_matches = []
            for match in result.matches:
                formatted_matches.append({
                    "line_number": match.line_number,
                    "line": match.line_content,
                    "context_before": match.context_before,
                    "context_after": match.context_after
                })

            return {
                "success": True,
                "pattern": result.pattern,
                "matches": formatted_matches,
                "match_count": result.total_matches,
                "file_path": str(result.file_path),
                "metadata": {
                    "ticker": result.filing.ticker,
                    "form_type": result.filing.form_type,
                    "filing_date": result.filing.filing_date,
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to search filing: {str(e)}"
            }

    async def list_filings(
        self,
        ticker: str,
        form_type: str,
        start: int = 0,
        max: int = 15
    ) -> dict[str, Any]:
        """List available filings (both cached and from SEC)"""
        try:
            # Use service from container
            available, cached = await asyncio.to_thread(
                self.container.list_filings.execute,
                ticker=ticker,
                form_type=form_type
            )

            # Build map of cached dates by format
            cached_map = {}
            for c in cached:
                if c.filing_date not in cached_map:
                    cached_map[c.filing_date] = {}
                cached_map[c.filing_date][c.format] = {
                    "path": str(c.path),
                    "size_bytes": c.size_bytes
                }

            # Merge available with cached info
            filings = []
            for filing in available:
                cached_info = cached_map.get(filing.filing_date, {})
                filings.append({
                    "ticker": filing.ticker,
                    "form_type": filing.form_type,
                    "filing_date": filing.filing_date,
                    "accession_number": filing.accession_number,
                    "sec_url": filing.sec_url,
                    "cached": cached_info
                })

            return {
                "success": True,
                "filings": filings,
                "count": len(filings),
                "cached_count": len(cached),
                "available_count": len(available),
                "start": start,
                "max": max
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to list filings: {str(e)}"
            }

    async def list_cached(
        self,
        ticker: Optional[str] = None,
        form_type: Optional[str] = None
    ) -> dict[str, Any]:
        """List cached filings"""
        try:
            # Use service from container
            cached, disk_usage = await asyncio.to_thread(
                self.container.list_cached.execute,
                ticker=ticker,
                form_type=form_type
            )

            # Format cached filings
            formatted_filings = []
            for c in cached:
                formatted_filings.append({
                    "ticker": c.ticker,
                    "form_type": c.form_type,
                    "filing_date": c.filing_date,
                    "path": str(c.path),
                    "size_bytes": c.size_bytes,
                    "format": c.format
                })

            return {
                "success": True,
                "filings": formatted_filings,
                "count": len(formatted_filings),
                "disk_usage_mb": round(disk_usage / 1024 / 1024, 2),
                "cache_dir": str(self.container.cache.cache_dir)
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to list cached filings: {str(e)}"
            }
