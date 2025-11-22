"""
Core - Domain logic and ports

This package contains:
- domain.py: Pure domain models
- ports.py: Port interfaces (abstractions for external dependencies)
- services.py: Application services (use cases)
"""
from .domain import Filing, CachedFiling, FilingContent, SearchMatch, SearchResult
from .ports import FilingRepository, FilingFetcher, FilingSearcher
from .services import (
    FetchFilingService,
    ListFilingsService,
    SearchFilingService,
    ListCachedService,
    FinancialStatementsService,
    ThirteenFHoldingsService
)

__all__ = [
    # Domain models
    "Filing",
    "CachedFiling",
    "FilingContent",
    "SearchMatch",
    "SearchResult",
    # Ports
    "FilingRepository",
    "FilingFetcher",
    "FilingSearcher",
    # Services
    "FetchFilingService",
    "ListFilingsService",
    "SearchFilingService",
    "ListCachedService",
    "FinancialStatementsService",
    "ThirteenFHoldingsService",
]
