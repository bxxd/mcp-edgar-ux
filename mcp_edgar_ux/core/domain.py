"""
Domain Models - Pure business entities

No external dependencies. These represent the core business concepts.
"""
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class Filing:
    """A SEC filing document"""
    ticker: str
    form_type: str
    filing_date: str  # YYYY-MM-DD format
    accession_number: str
    sec_url: str
    company_name: Optional[str] = None
    cik: Optional[str] = None


@dataclass
class CachedFiling:
    """A filing cached on disk"""
    ticker: str
    form_type: str
    filing_date: str
    path: Path
    size_bytes: int
    format: str  # "text", "markdown", or "html"


@dataclass
class FilingContent:
    """Content of a downloaded filing"""
    filing: Filing
    content: str
    format: str  # "text", "markdown", or "html"
    path: Path
    size_bytes: int
    total_lines: int


@dataclass
class SearchMatch:
    """A search result match within a filing"""
    line_number: int
    line_content: str
    context_before: list[str]
    context_after: list[str]


@dataclass
class SearchResult:
    """Results from searching within a filing"""
    filing: Filing
    pattern: str
    matches: list[SearchMatch]
    total_matches: int
    file_path: Path
