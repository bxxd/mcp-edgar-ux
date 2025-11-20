"""
Ports - Interfaces for external dependencies

These define HOW the core interacts with the outside world,
but NOT the implementation details.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from .domain import Filing, CachedFiling, FilingContent, SearchMatch


class FilingRepository(ABC):
    """Port for filing cache storage"""

    @abstractmethod
    def get(self, ticker: str, form_type: str, filing_date: str, format: str) -> Optional[Path]:
        """Get path to cached filing if it exists"""
        pass

    @abstractmethod
    def save(self, content: FilingContent) -> Path:
        """Save filing content to cache, return path"""
        pass

    @abstractmethod
    def list_all(self, ticker: Optional[str] = None, form_type: Optional[str] = None) -> list[CachedFiling]:
        """List all cached filings, optionally filtered"""
        pass

    @abstractmethod
    def get_disk_usage(self) -> int:
        """Get total disk usage in bytes"""
        pass

    @abstractmethod
    def exists(self, ticker: str, form_type: str, filing_date: str, format: str) -> bool:
        """Check if filing is cached"""
        pass


class FilingFetcher(ABC):
    """Port for fetching filings from SEC"""

    @abstractmethod
    def list_available(self, ticker: str, form_type: str) -> list[Filing]:
        """List all available filings from SEC (historical + current)"""
        pass

    @abstractmethod
    def fetch(self, filing: Filing, format: str = "text", include_exhibits: bool = True) -> str:
        """Download filing content from SEC"""
        pass

    @abstractmethod
    def get_latest(self, ticker: str, form_type: str, date: Optional[str] = None) -> Filing:
        """Get metadata for latest filing (or first filing >= date)"""
        pass


class FilingSearcher(ABC):
    """Port for searching within filings"""

    @abstractmethod
    def search(
        self,
        file_path: Path,
        pattern: str,
        context_lines: int = 2,
        max_results: int = 20,
        offset: int = 0
    ) -> list[SearchMatch]:
        """Search for pattern in filing, return matches with context"""
        pass

    @abstractmethod
    def count_lines(self, file_path: Path) -> int:
        """Count total lines in file"""
        pass

    @abstractmethod
    def read_preview(self, file_path: Path, num_lines: int) -> tuple[list[str], int]:
        """Read first N lines with line numbers, return (lines, total_count)"""
        pass
